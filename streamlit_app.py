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

# Custom CSS for Mobile Optimization
st.markdown("""
    <style>
    /* Tab Styling for Touch Targets */
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; padding: 12px; flex-grow: 1; text-align: center; }
    
    /* High-Impact Action Buttons */
    .deploy-btn { 
        display: block; width: 100%; padding: 18px; 
        background-color: #B22234; color: white !important; 
        text-align: center; border-radius: 12px; 
        font-weight: bold; text-decoration: none; font-size: 1.1em;
        margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
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

# --- 3. ROBUST DATA ENGINE ---
# Backup data ensures the app works immediately, even if CSV is missing.
BACKUP_DATA = {
    "45011": [
        {"display_label": "Rep. Diane Mullins (District 47)", "rep_name": "Diane Mullins", "rep_district": "47", "school_district": "Hamilton City Schools", "enrollment": "9,800", "rep_email": "rep47@ohiohouse.gov"},
        {"display_label": "Rep. Thomas Hall (District 46)", "rep_name": "Thomas Hall", "rep_district": "46", "school_district": "Lakota Local Schools", "enrollment": "17,500", "rep_email": "rep46@ohiohouse.gov"}
    ],
    "45013": [
         {"display_label": "Rep. Diane Mullins (District 47)", "rep_name": "Diane Mullins", "rep_district": "47", "school_district": "Hamilton City Schools", "enrollment": "9,800", "rep_email": "rep47@ohiohouse.gov"},
         {"display_label": "Rep. Thomas Hall (District 46)", "rep_name": "Thomas Hall", "rep_district": "46", "school_district": "Ross Local Schools", "enrollment": "2,800", "rep_email": "rep46@ohiohouse.gov"}
    ],
    "45044": [
        {"display_label": "Rep. Thomas Hall (District 46)", "rep_name": "Thomas Hall", "rep_district": "46", "school_district": "Middletown City Schools", "enrollment": "6,200", "rep_email": "rep46@ohiohouse.gov"}
    ],
    "43215": [
        {"display_label": "Rep. Allison Russo (District 7)", "rep_name": "Allison Russo", "rep_district": "7", "school_district": "Columbus City Schools", "enrollment": "46,000", "rep_email": "rep07@ohiohouse.gov"}
    ]
}

@st.cache_data
def get_reps_for_zip(zip_code):
    """Finds all Representatives linked to a specific Zip Code."""
    # 1. Try CSV
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str}, quotechar='"')
        matches = df[df['zip_code'] == zip_code]
        if not matches.empty:
            records = matches.to_dict('records')
            for r in records:
                r['display_label'] = f"Rep. {r['rep_name']} (District {r['rep_district']})"
            return records
    except:
        pass # Fallback to backup logic if CSV fails
    
    # 2. Backup Dict
    return BACKUP_DATA.get(zip_code, [])

# --- 4. UTILITIES (CRASH PROTECTION) ---
def safe_encode(text):
    """Cleans text to prevent PDF generation crashes."""
    if not isinstance(text, str): text = str(text)
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-', '\u2026': '...'}
    for u, s in replacements.items(): text = text.replace(u, s)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(1.0, 1.0, 1.0)
    
    # Re-Integrated Identity Bridge
    badges = [b for b, active in [("active voter", id_badges['voter']), ("taxpayer", id_badges['taxpayer']), ("homeowner", id_badges['homeowner'])] if active]
    id_base = ", ".join(badges[:-1]) + (" and " + badges[-1] if len(badges) > 1 else badges[0] if badges else "resident")
    residency_part = f" Having lived in Ohio for {id_badges['y_ohio']} years,"
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # Header
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['role']), ln=True)
        pdf.cell(0, 0.2, txt=safe_encode(f"Zip Code: {user_info['zip']}"), ln=True); pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True); pdf.ln(0.3)
        
        # Recipient Block
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(f"{rec['role']} {rec['name']}"), ln=True)
        pdf.set_font("Times", '', 12)
        # Safe Address Handling
        addr = rec.get('address', '77 S. High St, Columbus, OH 43215')
        pdf.multi_cell(0, 0.2, txt=safe_encode(addr)); pdf.ln(0.3)
        
        # Salutation
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=safe_encode(f"Dear {rec['role']} {last_name}:")); pdf.ln(0.3)
        
        # Body Copy
        body = (f"My name is {user_info['name']}. I live in {data['school_district']} (District {data['rep_district']}). "
                f"As an {id_base}{residency_part} I am writing because our public schools serve {data['enrollment']} students "
                f"and face an existential crisis. {custom_text} "
                "I urge you to prioritize public education funding immediately.")
        
        pdf.multi_cell(0, 0.2, txt=safe_encode(body))
        pdf.ln(0.4); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8)
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=safe_encode(user_info['name']), ln=True)
    
    # CRITICAL FIX: Return as binary bytes, not string
    return pdf.output(dest="S").encode('latin-1')

# --- 5. MOBILE INTERFACE ---
c1, c2 = st.columns([1, 5])
with c1: st.title("⚖️")
with c2: st.markdown("### Class Action: Ohio\n**Mobile Command Center**")

with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher"
    st.markdown(f"<div class='rank-card'><h2 style='margin:0; color:#facc15;'>{st.session_state.xp_points} XP</h2><p style='margin:0;'>Rank: {rank}</p></div>", unsafe_allow_html=True)

# --- CORE LOGIC: ZIP -> REP -> SCHOOL ---
st.markdown("#### Step 1: Locate Your Representative")
zip_input = st.text_input("Enter Zip Code:", max_chars=5, help="Try 45011")

if zip_input:
    options = get_reps_for_zip(zip_input)
    
    if not options:
        st.error("No representatives found. Try 45011, 45044, or 43215.")
    else:
        # PIVOT: Select Rep First to lock in School District
        rep_labels = [o['display_label'] for o in options]
        selected_label = st.selectbox("Select Your Representative:", rep_labels)
        
        # Auto-Assign Data
        data = next(o for o in options if o['display_label'] == selected_label)
        
        st.markdown(f"""
        <div class="status-banner">
            ✅ ASSIGNED SCHOOL DISTRICT:<br>
            <span style="font-size: 1.2em;">{data['school_district']}</span>
        </div>
        """, unsafe_allow_html=True)

        # Tabs unlock only after selection
        t_id, t_msg, t_deploy = st.tabs(["👤 YOU", "📝 MSG", "🚀 GO"])

        with t_id:
            st.text_input("Full Name:", key="u_name") 
            st.text_input("Title:", key="u_role")
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.checkbox("Voter", key="is_voter")
                st.checkbox("Taxpayer", key="is_taxpayer")
            with c_b:
                st.checkbox("Homeowner", key="is_homeowner")
                st.number_input("Years in Ohio:", min_value=0, key="years_ohio")

        with t_msg:
            st.text_area("Your Story:", key="custom_note", height=120)
            target_opts = ["📍 Local Rep", "🏛️ Governor DeWine", "🛡️ Minority Leader Russo", "🚫 Speaker Huffman"]
            if st.button("Select All Targets"): 
                st.session_state.u_targets = target_opts
                st.rerun()
            st.multiselect("Recipients:", target_opts, key="u_targets")

        with t_deploy:
            if st.session_state.u_targets and st.session_state.u_name:
                # 2026 Leadership Integration
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": "77 S. High St, Columbus, OH 43215", "role": "Representative"},
                    "🏛️ Governor DeWine": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Minority Leader Russo": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Speaker Huffman": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, Columbus, OH 43215", "role": "Speaker"}
                }
                selected = [target_map[t] for t in st.session_state.u_targets if t in target_map]
                
                # A. Email Blast
                bcc = ",".join([r['email'] for r in selected])
                subj = urllib.parse.quote(f"Public Schools in {data['school_district']}")
                # Custom note is integrated here
                body = urllib.parse.quote(f"Regarding District {data['rep_district']}:\n\n{st.session_state.custom_note}\n\n{st.session_state.u_name}")
                st.markdown(f'<a href="mailto:?bcc={bcc}&subject={subj}&body={body}" class="deploy-btn">✉️ LAUNCH EMAIL APP</a>', unsafe_allow_html=True)
                
                # B. PDF Download
                id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 'homeowner': st.session_state.is_homeowner, 'y_ohio': st.session_state.years_ohio, 'parent': False, 'count': 0}
                
                pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                
                st.download_button("📄 DOWNLOAD PDF PACK", pdf_bytes, "Advocacy.pdf", mime="application/pdf")
                
                if st.button("✅ EARN XP"):
                    st.session_state.xp_points += 100
                    st.rerun()
            else:
                st.info("Complete steps above to deploy.")
