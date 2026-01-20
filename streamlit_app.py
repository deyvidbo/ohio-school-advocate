import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

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

# --- 3. DATA LOADER: ODEW Employment & District Data ---
@st.cache_data
def load_data():
    try:
        # Expected columns: zip_code, school_district, enrollment, voucher_loss, 
        # teacher_count, avg_teacher_salary, rep_name, rep_email, rep_address, rep_stance
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
def create_professional_letter(target_rep, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_font("Times", '', 12)
    pdf.set_left_margin(1.0)
    pdf.set_right_margin(1.0)
    
    # 1. Sender Info (Block Format)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    
    # 2. Date
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.2)
    
    # 3. Recipient Info
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S. High St, Columbus, OH 43215'))
    pdf.ln(0.2)
    
    # 4. Salutation (Professional Colon)
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:")
    pdf.ln(0.4)
    
    # 5. Body Paragraphs (Left Justified)
    paragraphs = content.split('\n\n')
    for p in paragraphs:
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # 6. Closing & Signature Space
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # 4 spaces for signature
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=320) 
except:
    st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.header("📋 Educator Profile")
    user_name = st.text_input("Your Full Name", value="David M. Bothast")
    user_title = st.text_input("Your Title", value="K-8 Visual Arts Teacher")
    zip_code = st.text_input("Mailing Zip Code", max_chars=5, value="45056")
    st.markdown("---")
    st.metric("Total Advocacy XP", f"{st.session_state.xp_points}")

# MAIN PAGE
st.header("1. Select District & Analyze ODEW Data")
if not df.empty:
    districts = sorted(df['school_district'].unique())
    selected_dist = st.selectbox("Search School District:", ["Select..."] + districts)

    if selected_dist != "Select...":
        data = df[df['school_district'] == selected_dist].iloc[0]
        
        # ODEW EMPLOYMENT & ENROLLMENT DATA DASHBOARD
        st.markdown(f"### 📊 ODEW Statistics for {selected_dist}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Students Enrolled", data['enrollment'])
        with col2:
            st.metric("Total Licensed Teachers", data.get('teacher_count', 'N/A'))
        with col3:
            st.metric("Voucher Funding Loss", f"${data.get('voucher_loss', '0')}", delta="- Budget Impact", delta_color="inverse")

        st.markdown("---")
        st.header("2. Professional Correspondence")
        mode = st.radio("Recipient:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Defenders", "🚫 Opponents"], horizontal=True)

        # Content with Teacher Demographic/Employment Data
        intro = f"I am writing as a {user_title} and voter in the {selected_dist} (Zip: {zip_code})."
        detail = (f"According to the latest ODEW data, our district serves {data['enrollment']} students and employs "
                  f"{data.get('teacher_count', 'our professional faculty')}. Diversion of ${data.get('voucher_loss', '0')} "
                  f"to vouchers threatens the stability of our workforce and our ability to meet state academic standards.")
        action = "I ask you to prioritize public funding for our schools. Thank you for your consideration."
        full_content = f"{intro}\n\n{detail}\n\n{action}"

        # ACTION BUTTONS
        c_mail, c_pdf = st.columns(2)
        with c_mail:
            safe_body = urllib.parse.quote(full_content)
            target = data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
            st.markdown(f'''
                <a href="mailto:{target}?subject=Advocacy for {selected_dist}&body={safe_body}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">
                        ✉️ OPEN EMAIL (Mobile Ready)
                    </div>
                </a>''', unsafe_allow_html=True)
        
        with c_pdf:
            pdf_bytes = create_professional_letter(data, {"name": user_name, "title": user_title, "zip": zip_code}, full_content)
            st.download_button("📄 DOWNLOAD BLOCK FORMAT LETTER", pdf_bytes, f"Advocacy_{selected_dist}.pdf", "application/pdf")

        if st.button("✅ Log Mission Success (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[selected_dist] = st.session_state.district_stats.get(selected_dist, 0) + 1
            st.rerun()
