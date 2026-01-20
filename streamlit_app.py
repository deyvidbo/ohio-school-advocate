import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS for Mobile Optimization & "War Room" Aesthetics
st.markdown("""
    <style>
    /* Tab Styling for Mobile Touch Targets */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; padding: 12px; flex-grow: 1; text-align: center; }
    
    /* High-Impact Action Buttons */
    .deploy-btn { 
        display: block; width: 100%; padding: 18px; 
        background-color: #B22234; color: white !important; 
        text-align: center; border-radius: 12px; 
        font-weight: bold; text-decoration: none; font-size: 1.1em;
        margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    .deploy-btn:hover { background-color: #991b1b; transform: translateY(-2px); }
    
    /* Status Banners */
    .status-banner {
        padding: 12px; background-color: #ecfdf5; 
        border: 1px solid #10b981; color: #065f46; 
        border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;
    }
    
    /* Rank Card */
    .rank-card {
        background-color: #1e3a8a; color: white; 
        padding: 15px; border-radius: 10px; 
        text-align: center; border: 2px solid #facc15;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'u_targets' not in st.session_state: st.session_state.u_targets = []

# --- 3. FAIL-SAFE DATA ENGINE ---
# Built-in backup ensures app NEVER fails on demo/test zips
BACKUP_DATA = {
    "45011": {"school_district": "Hamilton City Schools", "enrollment": "9,800", "rep_name": "Diane Mullins", "rep_district": "47", "rep_email": "rep47@ohiohouse.gov", "rep_address": "77 S. High St, Columbus, OH 43215"},
    "45013": {"school_district": "Hamilton City Schools", "enrollment": "9,800", "rep_name": "Diane Mullins", "rep_district": "47", "rep_email": "rep47@ohiohouse.gov", "rep_address": "77 S. High St, Columbus, OH 43215"},
    "45044": {"school_district": "Middletown City Schools", "enrollment": "6,200", "rep_name": "Thomas Hall", "rep_district": "46", "rep_email": "rep46@ohiohouse.gov", "rep_address": "77 S. High St, Columbus, OH 43215"},
    "45056": {"school_district": "Talawanda City Schools", "enrollment": "2,900", "rep_name": "Diane Mullins", "rep_district": "47", "rep_email": "rep47@ohiohouse.gov", "rep_address": "77 S. High St, Columbus, OH 43215"},
    "43215": {"school_district": "Columbus City Schools", "enrollment": "46,000", "rep_name": "Allison Russo", "rep_district": "7", "rep_email": "rep07@ohiohouse.gov", "rep_address": "77 S. High St, Columbus, OH 43215"}
}

@st.cache_data
def get_district_data(zip_code):
    """Hybrid lookup: Checks CSV first, falls back to Backup Dict."""
    # 1. CSV Attempt
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str}, quotechar='"')
        matches = df[df['zip_code'] == zip_code]
        if not matches.empty:
            return matches.to_dict('records')
    except:
        pass # Silently fail to backup
    
    # 2. Backup Attempt
    if zip_code in BACKUP_DATA:
        return [BACKUP_DATA[zip_code]]
    
    return []

# --- 4. CRASH PROTECTION (Unicode Sanitizer) ---
def safe_encode(text):
    """Cleans emojis & smart quotes to prevent PDF generation crashes."""
    if not isinstance(text, str): text = str(text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u00a0': ' '
    }
    for unicode_char, safe_char in replacements.items():
        text = text.replace(unicode_char, safe_char)
    # Final fallback: encode to latin-1, replacing unknowns with '?'
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 5. PROFESSIONAL PDF GENERATOR ---
def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(1.0, 1.0, 1.0)
    
    # Construct Identity Bridge
    badges = [b for b, active in [("active voter", id_badges['voter']), ("taxpayer", id_badges['taxpayer']), ("homeowner", id_badges['homeowner']), ("resident", id_badges['renter'])] if active]
    id_base = ", ".join(badges[:-1]) + (" and " + badges[-1] if len(badges) > 1 else badges[0] if badges else "resident")
    parent_part = f" and parent of {id_badges['count']} children," if id_badges['parent'] else ","
    residency_part = f" Having lived in Ohio for {id_badges['y_ohio']} years,"
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # SENDER BLOCK
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['role']), ln=True)
        pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
        pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
        pdf.ln(0.3)
        
        # RECIPIENT BLOCK
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(f"{rec['role']} {rec['name']}"), ln=True)
        pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=safe_encode(rec['address']))
        pdf.ln(0.3)
        
        # SALUTATION
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=safe_encode(f"Dear {rec['role']} {last_name}:"))
        pdf.ln(0.3)
        
        # BODY COPY (Customized)
        body = (f"My name is {user_info['name']}. I live in {data['school_district']} (District {data['rep_district']}). "
                f"As an {id_base}{parent_part}{residency_part} I am writing because our public schools serve {data['enrollment']} students "
                f"and face an existential crisis. {custom_text} "
                "I urge you to prioritize public education funding immediately.")
        
        pdf.multi_cell(0, 0.2, txt=safe_encode(body))
        pdf.ln(0.4); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8)
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        
    return pdf.output(dest="S")

# --- 6. MOBILE INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
c1, c2 = st.columns([1, 5])
with c1: 
    try: st.image(logo_url, width=65) 
    except: st.title("⚖️")
with c2: st.markdown("### Class Action: Ohio\n**Mobile Command Center**")

# SIDEBAR: GAMIFICATION & SHARING
with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 500 else "THE SUPERINTENDENT"
    st.markdown(f"""
        <div class="rank-card">
            <h2 style="margin:0; color:#facc15;">{st.session_state.xp_points} XP</h2>
            <p style="margin:0; font-weight:bold;">Rank: {rank}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📢 Recruit Allies")
    site_url = "https://classactionohio.org"
    msg = urllib.parse.quote(f"I'm advocating for Ohio schools as a {rank}. Join the mission: {site_url}")
    st.markdown(f"📱 [Text a Friend](sms:?&body={msg})")
    st.markdown(f"🐦 [Post to X/Twitter](https://twitter.com/intent/tweet?text={msg})")

# MAIN WORKFLOW
zip_input = st.text_input("📍 ENTER ZIP CODE:", max_chars=5, help="Try 45011 for a demo.")

if zip_input:
    # 1. Fetch Data (Fail-Safe)
    results = get_district_data(zip_input)
    
    if not results:
        st.error("Zip code not found. Please try 45011, 45044, or 43215.")
    else:
        # 2. Collision Handling (Multi-District Zips)
        if len(results) > 1:
            opts = [r['school_district'] for r in results]
            choice = st.selectbox("Select Your School District:", opts)
            data = next(r for r in results if r['school_district'] == choice)
        else:
            data = results[0]
            
        st.markdown(f'<div class="status-banner">✅ CONNECTED: {data["school_district"]}</div>', unsafe_allow_html=True)

        # 3. Mobile Tabs
        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])

        with t_id:
            st.text_input("Full Name:", key="u_name") 
            st.text_input("Title (e.g. Parent, Teacher):", key="u_role")
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.checkbox("Voter", key="is_voter")
                st.checkbox("Taxpayer", key="is_taxpayer")
            with c_b:
                st.checkbox("Homeowner", key="is_homeowner")
                st.checkbox("Parent", key="is_parent")
                
            if st.session_state.is_parent: st.number_input("Children:", min_value=1, key="child_count")
            st.number_input("Years in Ohio:", min_value=0, key="years_ohio")

        with t_msg:
            st.text_area("Your Story:", key="custom_note", height=150, placeholder="How does voucher expansion impact your specific classroom or students?")
            
            target_options = ["📍 Local Rep", "🏛️ Governor DeWine", "🛡️ Minority Leader Russo", "🚫 Speaker Huffman"]
            if st.button("Select All Targets"): 
                st.session_state.u_targets = target_options
                st.rerun()
            st.multiselect("Recipients:", target_options, key="u_targets")

        with t_deploy:
            if st.session_state.u_targets and st.session_state.u_name:
                # 2026 Leadership Mappings
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": data.get('rep_address', '77 S. High St, Columbus, OH 43215'), "role": "Representative"},
                    "🏛️ Governor DeWine": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Minority Leader Russo": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Speaker Huffman": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                
                selected = [target_map[t] for t in st.session_state.u_targets if t in target_map]
                
                # A. Email Blast
                bcc_list = ",".join([r['email'] for r in selected])
                subj = urllib.parse.quote(f"CRISIS: Public Schools in {data['school_district']}")
                body = urllib.parse.quote(f"Testimony regarding District {data['rep_district']}:\n\n{st.session_state.custom_note}\n\nSincerely,\n{st.session_state.u_name}")
                
                st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subj}&body={body}" class="deploy-btn">✉️ LAUNCH EMAIL APP</a>', unsafe_allow_html=True)
                
                # B. PDF Download
                id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 'homeowner': st.session_state.is_homeowner, 'renter': False, 'parent': st.session_state.is_parent, 'count': st.session_state.get('child_count', 0), 'y_ohio': st.session_state.years_ohio}
                
                pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                
                st.download_button("📄 DOWNLOAD PDF PACK", pdf_bytes, "Advocacy_Pack.pdf", mime="application/pdf")

                if st.button("✅ FINALIZE & EARN XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons(); st.rerun()
            else:
                st.warning("⚠️ Action Required: Enter your Name (Tab 1) and select Targets (Tab 2).")
