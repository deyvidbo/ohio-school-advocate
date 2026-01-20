import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .rank-card { background-color: #1e3a8a; color: white; padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #b91c1c; }
    .deploy-btn { display: block; width: 100%; padding: 18px; background-color: #b91c1c; color: white !important; text-align: center; border-radius: 12px; font-weight: bold; text-decoration: none; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE (Memory Engine) ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0

# --- 3. DATA ENGINE: CSV ZIP LOOKUP ---
@st.cache_data
def load_lookup_data():
    try:
        # quotechar='"' handles complex names and multi-line addresses safely
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"⚠️ SYSTEM ERROR: 'ohio_districts.csv' not found or improperly formatted. {e}")
        return pd.DataFrame()

df_lookup = load_lookup_data()

# --- 4. UNICODE SANITIZER (PDF Safety) ---
def safe_encode(text):
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-', '\u2026': '...'}
    for unicode_char, safe_char in replacements.items():
        text = text.replace(unicode_char, safe_char)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 5. PDF GENERATOR ---
def create_bulk_pdf(recipients_list, user_info, data, custom_text):
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
        
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=safe_encode(f"Dear {rec['role']} {last_name}:")); pdf.ln(0.3)
        
        body = (f"My name is {user_info['name']}. I live in House District {data['rep_district']}, home of {data['school_district']}. "
                f"Currently, our schools serve {data['enrollment']} students. I am writing because voucher expansion is a direct, "
                f"perilous threat to our community stability. {custom_text}")
        
        pdf.multi_cell(0, 0.2, txt=safe_encode(body))
        pdf.ln(0.4); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8)
        pdf.set_font("Times", 'B', 12); pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
    return pdf.output(dest="S")

# --- 6. MAIN INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.image(logo_url, width=150)
st.title("⚖️ Class Action: Ohio")

# SIDEBAR: MISSION PROGRESS
with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 500 else "THE SUPERINTENDENT"
    st.markdown(f"<div class='rank-card'><div class='xp-display'>{st.session_state.xp_points} XP</div><div>Rank: {rank}</div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📢 Share the Mission")
    site_url = "https://classactionohio.org"
    msg = urllib.parse.quote(f"Advocating for Ohio schools as a {rank}. Join me: {site_url}")
    st.markdown(f"📱 [Text/SMS](sms:?&body={msg})")
    st.markdown(f"✉️ [Email](mailto:?subject=Urgent%20Action&body={msg})")

# ZIP CODE TRIGGER
zip_input = st.text_input("📍 ENTER ZIP CODE TO AUTO-CONNECT:", max_chars=5)

if zip_input:
    matches = df_lookup[df_lookup['zip_code'] == zip_input]
    
    if matches.empty:
        st.error(f"Zip code {zip_input} not found in Ohio database. Please verify your entry.")
    else:
        # Collision Handling
        if len(matches) > 1:
            st.warning(f"Zip code {zip_input} covers multiple districts. Please select yours:")
            district_choice = st.selectbox("Select School District:", matches['school_district'].tolist())
            selected_data = matches[matches['school_district'] == district_choice].iloc[0].to_dict()
        else:
            selected_data = matches.iloc[0].to_dict()
            st.success(f"✅ TARGET ACQUIRED: {selected_data['school_district']} (District {selected_data['rep_district']})")

        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])
        
        with t_id:
            st.text_input("Full Name:", key="u_name") 
            st.text_input("Professional Title:", key="u_role")
            st.checkbox("Voter", key="is_voter")
            st.checkbox("Taxpayer", key="is_taxpayer")
            st.number_input("Years in Ohio:", min_value=0, key="years_ohio")

        with t_msg:
            st.text_area("Your Story (integrated into letters):", key="custom_note")
            all_opts = ["📍 Local Rep", "🏛️ Governor DeWine", "🛡️ Minority Leader Russo", "🚫 Speaker Huffman"]
            if st.button("Select All Targets"): 
                st.session_state.u_targets = all_opts
                st.rerun()
            st.multiselect("Recipients:", all_opts, key="u_targets")

        with t_deploy:
            if st.session_state.u_targets and st.session_state.u_name:
                # 2026 Leadership Mappings
                target_map = {
                    "📍 Local Rep": {"name": selected_data['rep_name'], "email": selected_data['rep_email'], "address": selected_data['rep_address'], "role": "Representative"},
                    "🏛️ Governor DeWine": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Friendly Caucus": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Speaker Huffman": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                selected = [target_map[t] for t in st.session_state.u_targets if t in target_map]
                
                # Digital & Physical Deployment
                bcc_list = ",".join([r['email'] for r in selected])
                subj = urllib.parse.quote(f"CRISIS: Public Schools in {selected_data['school_district']}")
                email_body = urllib.parse.quote(f"Please read my testimony regarding Dist. {selected_data['rep_district']}:\n\n{st.session_state.custom_note}")
                st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subj}&body={email_body}" class="deploy-btn">✉️ SEND URGENT EMAIL BLAST</a>', unsafe_allow_html=True)

                pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, selected_data, st.session_state.custom_note)
                st.download_button(label=f"📄 DOWNLOAD PRINT PACK (PDF)", data=pdf_bytes, file_name="Urgent_Advocacy.pdf")

                if st.button("✅ FINALIZE & EARN XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons(); st.rerun()
            else:
                st.warning("Complete the YOU and MSG tabs to deploy.")
