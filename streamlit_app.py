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
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state:
    # Adding Mr. B as the first permanent member
    st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
# 
def create_professional_letter(target_rep, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_font("Times", '', 12)
    pdf.set_left_margin(1.0)
    pdf.set_right_margin(1.0)
    
    # Block Format Header
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.2)
    
    # Recipient
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S. High St, Columbus, OH 43215'))
    pdf.ln(0.2)
    
    # Salutation (Colon)
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:")
    pdf.ln(0.4)
    
    # Body
    for p in content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Signature Space
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # Signature area
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    return pdf.output(dest="S").encode("latin-1")

# --- 5. SUPERINTENDENT CERTIFICATE GENERATOR ---
def create_superintendent_certificate(user_name, district_name):
    pdf = FPDF(orientation='L', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_draw_color(178, 34, 52)
    pdf.set_line_width(0.1)
    pdf.rect(0.5, 0.5, 10, 7.5)
    
    pdf.set_font("Times", 'B', 36)
    pdf.set_y(1.5)
    pdf.cell(0, 0.6, txt="CERTIFICATE OF ADVOCACY", ln=True, align='C')
    pdf.set_font("Times", 'BI', 30)
    pdf.ln(0.9)
    pdf.cell(0, 0.5, txt=user_name, ln=True, align='C')
    pdf.set_font("Times", 'B', 24)
    pdf.set_text_color(178, 34, 52)
    pdf.ln(1.5)
    pdf.cell(0, 0.4, txt="RANK: THE SUPERINTENDENT", ln=True, align='C')
    return pdf.output(dest="S").encode("latin-1")

# --- 6. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try: st.image(logo_url, width=320)
except: st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.header("📋 Educator Profile")
    u_name = st.text_input("Full Name", value="David M. Bothast")
    u_title = st.text_input("Title", value="K-8 Visual Arts Teacher")
    z_code = st.text_input("Zip Code", value="45056", max_chars=5)
    st.markdown("---")
    st.metric("Your Total XP", f"{st.session_state.xp_points}")

# GRADUATION & HALL OF FAME LOGIC
if st.session_state.xp_points >= 300:
    if u_name not in st.session_state.hall_of_fame:
        st.session_state.hall_of_fame.append(u_name)
    
    st.success(f"🎓 **CONGRATULATIONS {u_name.upper()}!** You have achieved Superintendent Rank.")
    cert_bytes = create_superintendent_certificate(u_name, "Ohio Public Schools")
    st.download_button("🏆 DOWNLOAD YOUR DIPLOMA", cert_bytes, "Superintendent_Certificate.pdf", "application/pdf")
    st.balloons()

# MAIN CONTENT
if not df.empty:
    districts = sorted(df['school_district'].unique())
    selected_dist = st.selectbox("Search Your District:", ["Select a District..."] + districts)

    if selected_dist != "Select a District...":
        data = df[df['school_district'] == selected_dist].iloc[0]
        st.subheader(f"📊 ODEW Data: {selected_dist}")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Enrollment", data['enrollment'])
        with col2: st.metric("Licensed Faculty", data.get('teacher_count', 'N/A'))
        with col3: st.metric("Voucher Impact", f"${data.get('voucher_loss', '0')}", delta="- Budget Gap", delta_color="inverse")

        st.markdown("---")
        mode = st.radio("Target Recipient:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Defenders", "🚫 Opponents"], horizontal=True)
        content = (f"I am writing as a {u_title} in the {selected_dist}. According to ODEW data, our district serves {data['enrollment']} students and employs {data.get('teacher_count', 'professional educators')}. "
                   f"The diversion of ${data.get('voucher_loss', '0')} to vouchers undermines our ability to meet state academic standards like 5.1PE.")
        full_content = f"My name is {u_name}.\n\n{content}\n\nPlease prioritize public funding. Thank you."

        c1, c2 = st.columns(2)
        with c1:
            target = data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
            st.markdown(f'''<a href="mailto:{target}?subject=Advocacy for {selected_dist}&body={urllib.parse.quote(full_content)}" style="text-decoration:none;">
                <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND EMAIL</div></a>''', unsafe_allow_html=True)
        with c2:
            st.download_button("📄 DOWNLOAD BLOCK LETTER", create_professional_letter(data, {"name": u_name, "title": u_title, "zip": z_code}, full_content), f"Letter_{selected_dist}.pdf", "application/pdf")
        
        if st.button("✅ Log Mission Success (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[selected_dist] = st.session_state.district_stats.get(selected_dist, 0) + 1
            st.rerun()

# HALL OF FAME SECTION
st.markdown("---")
st.header("🎖️ Superintendent Hall of Fame")
st.write("Recognizing the top advocates for Ohio's classrooms:")
st.info(", ".join(st.session_state.hall_of_fame))
