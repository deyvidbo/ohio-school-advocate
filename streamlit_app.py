import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & MOBILE THEME ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="auto" # 'auto' is better for mobile than 'expanded'
)

# Custom CSS for Mobile Touch Targets
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; padding: 12px; flex-grow: 1; text-align: center; }
    .deploy-btn { 
        display: block; width: 100%; padding: 18px; 
        background-color: #B22234; color: white !important; 
        text-align: center; border-radius: 12px; 
        font-weight: bold; text-decoration: none; font-size: 1.2em;
        margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .status-banner {
        padding: 15px; background-color: #ecfdf5; 
        border: 1px solid #10b981; color: #065f46; 
        border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'u_targets' not in st.session_state: st.session_state.u_targets = []

# --- 3. ROBUST DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Handles complex CSVs with quoted strings
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"', on_bad_lines='warn')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. UNICODE SANITIZER (Prevents PDF Crashes) ---
def safe_encode(text):
    """Converts emojis and smart quotes to safe Latin-1 characters."""
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u00a0': ' '
    }
    for unicode_char, safe_char in replacements.items():
        text = text.replace(unicode_char, safe_char)
    # Final fallback: encode to latin-1, replacing unknowns with '?'
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 5. PDF GENERATOR ---
def create_bulk_pdf(recipients_list, user_info, data, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(1.0, 1.0, 1.0)
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # Header
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['role']), ln=True)
        pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
        pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
        pdf.ln(0.3)
        
        # Recipient
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(f"{rec['role']} {rec['name']}"), ln=True)
        pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=safe_encode(rec['address']))
        pdf.ln(0.3)
        
        # Body
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=safe_encode(f"Dear {rec['role']} {last_name}:"))
        pdf.ln(0.3)
        
        body = (f"My name is {user_info['name']}. I live in {data['school_district']} (District {data['rep_district']}). "
                f"Our schools serve {data['enrollment']} students. I am writing because voucher expansion is a direct threat "
                f"to our community stability. {custom_text}")
        
        pdf.multi_cell(0, 0.2, txt=safe_encode(body))
        pdf.ln(0.4); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8)
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        
    return pdf.output(dest="S")

# --- 6. MOBILE INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
c1, c2 = st.columns([1, 4])
with c1: 
    try: st.image(logo_url, width=80) 
    except: st.title("⚖️")
with c2: st.markdown("### Class Action: Ohio\n**Mobile Command Center**")

# SIDEBAR: GAMIFICATION
with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 300 else "THE SUPERINTENDENT"
    st.metric("Action XP", st.session_state.xp_points, delta=None)
    st.write(f"**Current Rank:** {rank}")
    st.markdown("---")
    st.markdown(" **Share:**")
    site_url = "https://classactionohio.org"
    msg = urllib.parse.quote(f"I'm an advocacy {rank} for Ohio schools! Join me: {site_url}")
    st.markdown(f"📱 [Text/SMS](sms:?&body={msg})")
    st.markdown(f"🐦 [X/Twitter](https://twitter.com/intent/tweet?text={msg})")

# CORE WORKFLOW
zip_input = st.text_input("📍 ENTER ZIP CODE:", max_chars=5, help="Auto-connects to your district.")

if zip_input:
    # Filter for matches in CSV
    matches = df[df['zip_code'] == zip_input]
    
    if matches.empty:
        st.warning("Zip code not found. Please check your entry.")
    else:
        # COLLISION HANDLING: If zip has >1 district, ask user.
        if len(matches) > 1:
            district_choice = st.selectbox("Select Your School District:", matches['school_district'].unique())
            data = matches[matches['school_district'] == district_choice].iloc[0].to_dict()
        else:
            data = matches.iloc[0].to_dict()
            
        st.markdown(f'<div class="status-banner">✅ CONNECTED: {data['school_district']}</div>', unsafe_allow_html=True)

        # MOBILE TABS (The Fix for Scrolling)
        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])

        with t_id:
            st.text_input("Full Name:", key="u_name") 
            st.text_input("Title:", key="u_role")
            st.checkbox("Voter", key="is_voter")
            st.checkbox("Taxpayer", key="is_taxpayer")

        with t_msg:
            st.text_area("Your Story:", key="custom_note", height=150, placeholder="How does this impact your students?")
            
            # 2026 Leadership Targets
            target_options = ["📍 Local Rep", "🏛️ Governor DeWine", "🛡️ Minority Leader Russo", "🚫 Speaker Huffman"]
            if st.button("Select All Targets"): 
                st.session_state.u_targets = target_options
                st.rerun()
            st.multiselect("Recipients:", target_options, key="u_targets")

        with t_deploy:
            if st.session_state.u_targets and st.session_state.u_name:
                # Map selections to data
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": data['rep_address'], "role": "Representative"},
                    "🏛️ Governor DeWine": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Minority Leader Russo": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Speaker Huffman": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                
                selected = [target_map[t] for t in st.session_state.u_targets if t in target_map]
                
                # 1. EMAIL BLAST
                bcc_list = ",".join([r['email'] for r in selected])
                subj = urllib.parse.quote(f"CRISIS: Public Schools in {data['school_district']}")
                body = urllib.parse.quote(f"Testimony regarding District {data['rep_district']}:\n\n{st.session_state.custom_note}\n\nSincerely,\n{st.session_state.u_name}")
                
                st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subj}&body={body}" class="deploy-btn">✉️ LAUNCH EMAIL APP</a>', unsafe_allow_html=True)
                
                # 2. PDF GENERATION
                pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, st.session_state.custom_note)
                st.download_button("📄 DOWNLOAD PDF PACK", pdf_bytes, "Advocacy_Pack.pdf", mime="application/pdf")

                if st.button("✅ FINALIZE & EARN XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons(); st.rerun()
            else:
                st.warning("Please enter your Name (Tab 1) and select Targets (Tab 2) to deploy.")
