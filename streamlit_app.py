import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import qrcode
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide"
)

# --- 2. SESSION STATE ---
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}

# --- 3. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        # Expected columns: zip_code, school_district, enrollment, voucher_loss, 
        # teacher_count, rep_name, rep_email, rep_address, rep_role, rep_stance
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
# Strictly adheres to Professional Business Letter standards
def create_professional_letter(target_rep, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_font("Times", '', 12) # Professional Serif Font
    pdf.set_left_margin(1.0)
    pdf.set_right_margin(1.0)
    
    # Block Format Header: Sender Info
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    
    # Date
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.2)
    
    # Recipient Block
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S. High St, Columbus, OH 43215'))
    pdf.ln(0.2)
    
    # Salutation (Colon used for formal letters)
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:")
    pdf.ln(0.4)
    
    # Body (Single spaced, double spaced between paragraphs)
    for p in content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Signature Block (4 blank lines for physical signature)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) 
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=320)
except:
    st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR: STATS
with st.sidebar:
    st.header("📋 Advocacy Progress")
    st.metric("Total XP", f"{st.session_state.xp_points}")
    if st.session_state.xp_points >= 300:
        st.success("🏆 Rank: Superintendent")

# MAIN PAGE: ZIP CODE ENTRY
st.header("1. Locate Your Community")
zip_input = st.text_input("Enter Your Zip Code:", max_chars=5, placeholder="e.g. 45011")

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        dist_name = data['school_district']
        
        # Dashboard: Pulling ODEW and Enrollment Data
        st.subheader(f"📊 ODEW Metrics for {dist_name}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Students Served", data['enrollment'])
        with col2:
            st.metric("Licensed Faculty", data.get('teacher_count', 'N/A'))
        with col3:
            st.metric("Voucher Funding Loss", f"${data.get('voucher_loss', '0')}", delta="- Budget Impact", delta_color="inverse")

        st.markdown("---")
        st.header("2. Take Action")
        mode = st.radio("Choose Target:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Defenders", "🚫 Opponents"], horizontal=True)

        # Content Generation: Using default credentials
        user_info = {
            "name": "David M. Bothast", 
            "title": "K-8 Visual Arts Teacher", 
            "zip": zip_input
        }
        
        intro = f"I am writing as a {user_info['title']} and a voter in the {dist_name} (Zip: {zip_input})."
        detail = (f"According to the latest ODEW data, our district serves {data['enrollment']} students and employs {data.get('teacher_count', 'professional educators')}. "
                  f"The diversion of ${data.get('voucher_loss', '0')} to private vouchers undermines our ability to meet state academic standards.")
        action = "I urge you to prioritize local public school funding. Thank you for your time and consideration."
        full_content = f"{intro}\n\n{detail}\n\n{action}"

        # Action Buttons
        c1, c2 = st.columns(2)
        with c1:
            # mailto: protocol for mobile app connection
            safe_body = urllib.parse.quote(full_content)
            target = data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
            st.markdown(f'''<a href="mailto:{target}?subject=Advocacy for {dist_name}&body={safe_body}" style="text-decoration:none;">
                <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ OPEN EMAIL APP</div></a>''', unsafe_allow_html=True)
        
        with c2:
            pdf_bytes = create_professional_letter(data, user_info, full_content)
            st.download_button("📄 GENERATE BLOCK LETTER", pdf_bytes, f"Letter_{dist_name}.pdf", "application/pdf")
        
        if st.button("✅ I Completed This Task (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[dist_name] = st.session_state.district_stats.get(dist_name, 0) + 1
            st.rerun()
    else:
        st.error("Zip Code not found. Please verify and try again.")

# LEADERBOARD
if st.session_state.district_stats:
    st.markdown("---")
    st.header("🏆 District Leaderboard")
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
    st.table(leader_df.sort_values(by='Actions', ascending=False).head(5))
