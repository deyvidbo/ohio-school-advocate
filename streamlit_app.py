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
    .rank-card { 
        background-color: #1e3a8a; color: white; padding: 15px; border-radius: 12px; 
        text-align: center; border: 2px solid #b91c1c; margin-bottom: 10px;
    }
    .xp-display { font-size: 1.8em; font-weight: bold; color: #facc15; }
    .deploy-btn { 
        display: block; width: 100%; padding: 18px; background-color: #b91c1c; 
        color: white !important; text-align: center; border-radius: 10px; 
        font-weight: bold; text-decoration: none; margin-top: 10px; font-size: 1.1em;
    }
    .stTextArea textarea { font-size: 16px !important; } 
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE (The Memory Engine) ---
# This ensures that "Go Back" works and customization is preserved.
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'u_targets' not in st.session_state: st.session_state.u_targets = []

# --- 3. AUDIT-PROTECTED DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # quotechar handles names like "Rogers, Jr." and complex school district names
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. UNICODE SANITIZER ---
def safe_encode(text):
    """Prevents PDF crashes from emojis or smart quotes."""
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u00a0': ' '
    }
    for unicode_char, safe_char in replacements.items():
        text = text.replace(unicode_char, safe_char)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 5. DYNAMIC PDF GENERATOR ---
def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.set_auto_page_break(auto=True, margin=1.0)
    
    # Construct Personalization Strings
    badges = [b for b, active in [("active voter", id_badges['voter']), ("taxpayer", id_badges['taxpayer']), ("homeowner", id_badges['homeowner']), ("resident", id_badges['renter'])] if active]
    id_base = ", ".join(badges[:-1]) + (" and " + badges[-1] if len(badges) > 1 else badges[0] if badges else "resident")
    parent_part = f" and parent of {id_badges['count']} children," if id_badges['parent'] else ","
    residency_part = f" Having lived in Ohio for {id_badges['y_ohio']} years and within this district for {id_badges['y_dist']} years,"
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # SENDER & RECIPIENT HEADERS (Block Format)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['role']), ln=True)
        pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True); pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True); pdf.ln(0.3)
        
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(f"{rec['role']} {rec['name']}"), ln=True); pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=safe_encode(rec['address'])); pdf.ln(0.3)
        
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=safe_encode(f"Dear {rec['role']} {last_name}:")); pdf.ln(0.3)
        
        # THE CUSTOMIZED MESSAGE
        opening = f"My name is {user_info['name']}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
        identity_line = f"As an {id_base}{parent_part}{residency_part} I am writing to you because our public schools are facing an existential crisis."
        
        custom_section = f"From my direct experience: {custom_text.strip()}" if custom_text.strip() else ""
        if custom_section and not custom_section.endswith(('.', '!', '?')): custom_section += "."

        # ODEW Data Hook
        fiscal_detail = (f"Currently, {data['school_district']} serves {data['enrollment']} students. "
                         "The unchecked expansion of universal vouchers is a direct threat to the stability of our community.")
        
        full_body = [opening, identity_line]
        if custom_section: full_body.append(custom_section)
        full_body.extend([fiscal_detail, "I urge you to prioritize public education funding immediately."])
        
        for p in full_body:
            pdf.multi_cell(0, 0.2, txt=safe_encode(p), align='L')
            pdf.ln(0.2)
        
        pdf.ln(0.2); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8) 
        pdf.set_font("Times", 'B', 12); pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        
    return pdf.output(dest="S")

# --- 6. INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.image(logo_url, width=140)
st.markdown("### ⚖️ CLASS ACTION: OHIO")

# Mobile Sidebar
with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 500 else "THE SUPERINTENDENT"
    st.markdown(f"<div class='rank-card'><div class='xp-display'>{st.session_state.xp_points} XP</div><div>Rank: {rank}</div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📢 Share")
    site_url = "https://classactionohio.org"
    msg = urllib.parse.quote(f"Advocating for Ohio schools as a {rank}. Join me: {site_url}")
    st.markdown(f"🐦 [X/Twitter](https://twitter.com/intent/tweet?text={msg})")
    st.markdown(f"📱 [Text/SMS](sms:?&body={msg})")

zip_input = st.text_input("📍 DEPLOY BY ZIP CODE:", max_chars=5)

if zip_input and not df.empty:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        st.error(f"⚠️ TARGET: {data['school_district']} (District {data['rep_district']})")
        
        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])
        
        with t_id:
            # Keys ensure these are mapped to the final communication
            st.text_input("Name:", key="u_name") 
            st.text_input("Title:", key="u_role")
            st.checkbox("Voter", key="is_voter")
            st.checkbox("Taxpayer", key="is_taxpayer")
            st.checkbox("Homeowner", key="is_homeowner")
            st.checkbox("Parent", key="is_parent")
            if st.session_state.is_parent: st.number_input("Children:", min_value=1, key="child_count")
            st.number_input("Years in Ohio:", min_value=0, key="years_ohio")
            st.number_input(f"Years in Dist. {data['rep_district']}:", min_value=0, key="years_district")

        with t_msg:
            # Custom anecdote logic
            st.text_area("Your Story (Seamlessly integrated):", key="custom_note")
            all_opts = ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"]
            if st.button("Select All"): 
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
                
                # Digital & Physical Deployment
                c_email, c_pdf = st.columns(2)
                with c_email:
                    bcc_list = ",".join([r['email'] for r in selected])
                    subj = urllib.parse.quote(f"CRISIS: Public Schools in {data['school_district']}")
                    # Custom note is integrated into the email body
                    email_body = urllib.parse.quote(f"Please read my testimony regarding Dist. {data['rep_district']}:\n\n{st.session_state.custom_note}")
                    st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subj}&body={email_body}" class="deploy-btn">✉️ SEND EMAIL BLAST</a>', unsafe_allow_html=True)

                with c_pdf:
                    # Identity badges and custom note are integrated into PDF
                    id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 'homeowner': st.session_state.is_homeowner, 'renter': st.session_state.is_renter, 'parent': st.session_state.is_parent, 'count': st.session_state.child_count, 'y_ohio': st.session_state.years_ohio, 'y_dist': st.session_state.years_district}
                    pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                    st.download_button(label=f"📄 DOWNLOAD PDF PACK", data=pdf_bytes, file_name="Urgent_Pack.pdf")

                if st.button("✅ FINALIZE & EARN XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.rerun()
