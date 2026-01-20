import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. MOBILE-FIRST CONFIGURATION ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* High-Visibility Mobile Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { font-size: 14px; padding: 12px; }
    .deploy-btn { 
        display: block; width: 100%; padding: 20px; 
        background-color: #b91c1c; color: white !important; 
        text-align: center; border-radius: 12px; 
        font-weight: bold; text-decoration: none; font-size: 1.2em;
    }
    .status-banner { padding: 15px; border-radius: 10px; background-color: #fef2f2; border: 1px solid #b91c1c; color: #b91c1c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'u_targets' not in st.session_state: st.session_state.u_targets = []

# --- 3. AUDIT-PROTECTED DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. UNICODE SANITIZER ---
def safe_encode(text):
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-', '\u2026': '...'}
    for unicode_char, safe_char in replacements.items():
        text = text.replace(unicode_char, safe_char)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 5. DYNAMIC PDF GENERATOR ---
def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(1.0, 1.0, 1.0)
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['role']), ln=True); pdf.ln(0.2)
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(f"{rec['role']} {rec['name']}"), ln=True); pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=safe_encode(rec['address'])); pdf.ln(0.3)
        
        # Urgent Body with ODEW Data Hooks
        body = (f"My name is {user_info['name']}. I live in District {data['rep_district']}, home of {data['school_district']}. "
                f"Our schools serve {data['enrollment']} students. Voucher expansion is an existential threat. {custom_text}")
        pdf.multi_cell(0, 0.2, txt=safe_encode(body))
        pdf.ln(0.4); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
    return pdf.output(dest="S")

# --- 6. MOBILE INTERFACE ---
st.title("⚖️ Class Action: Ohio")
zip_input = st.text_input("📍 ENTER ZIP CODE TO UNLOCK MISSION:", max_chars=5)

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        # MOBILE STATUS BANNER
        st.markdown(f"""<div class="status-banner">✅ TARGET ACQUIRED: {data['school_district']} (District {data['rep_district']})</div>""", unsafe_allow_html=True)
        
        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])
        
        with t_id:
            st.text_input("Full Name:", key="u_name") 
            st.text_input("Professional Title:", key="u_role")
            st.checkbox("Voter", key="is_voter")
            st.checkbox("Taxpayer", key="is_taxpayer")
            st.number_input("Years in Ohio:", min_value=0, key="years_ohio")
            st.number_input(f"Years in Dist. {data['rep_district']}:", min_value=0, key="years_district")

        with t_msg:
            st.text_area("Your Urgent Testimony:", key="custom_note", placeholder="How does this impact your students?")
            all_opts = ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"]
            if st.button("Select All Targets"): 
                st.session_state.u_targets = all_opts
                st.rerun()
            st.multiselect("Recipients:", all_opts, key="u_targets")

        with t_deploy:
            if st.session_state.u_targets:
                # 2026 Leadership Mappings
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": data['rep_address'], "role": data['rep_role']},
                    "🏛️ Governor": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Friendly Caucus": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Opposition Leadership": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                selected = [target_map[t] for t in st.session_state.u_targets]
                
                # BCC EMAIL (Mobile Native)
                bcc_list = ",".join([r['email'] for r in selected])
                subj = urllib.parse.quote(f"CRISIS: Public Schools in {data['school_district']}")
                email_body = urllib.parse.quote(f"Please read my testimony regarding Dist. {data['rep_district']}:\n\n{st.session_state.custom_note}")
                st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subj}&body={email_body}" class="deploy-btn">✉️ SEND EMAIL BLAST</a>', unsafe_allow_html=True)

                # PDF DOWNLOAD
                id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 'homeowner': st.session_state.is_homeowner, 'renter': st.session_state.is_renter, 'parent': st.session_state.is_parent, 'count': st.session_state.child_count, 'y_ohio': st.session_state.years_ohio, 'y_dist': st.session_state.years_district}
                pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                st.download_button(label=f"📄 DOWNLOAD PRINT PACK", data=pdf_bytes, file_name="Urgent_Advocacy_Pack.pdf")

                if st.button("✅ FINALIZE & EARN XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons(); st.rerun()
            else:
                st.warning("Please select targets in the MSG tab.")
    else:
        st.error("Zip code not found. Check entry.")
