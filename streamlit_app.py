import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state:
    # Starting with you as the founder
    st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Loading Master CSV with all chunks integrated
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading district data: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
# Standards: Left-justified, 12pt Times, 1" Margins, 4-line Signature Gap
def create_block_letter(target_rep, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.add_page()
    pdf.set_font("Times", '', 12)
    
    # Sender Block
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.3)
    
    # Recipient Block
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S High St, Columbus, OH 43215'))
    pdf.ln(0.3)
    
    # Salutation
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:")
    pdf.ln(0.3)
    
    # Body
    for p in content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Signature Area
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # Correct 4-line spacing for handwritten signature
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try: st.image(logo_url, width=320)
except: st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>OHIO ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR: XP & RANK SYSTEM
with st.sidebar:
    st.header("📋 Advocacy Mission")
    st.metric("Total XP", f"{st.session_state.xp_points}")
    
    # Rank Progression Logic
    if st.session_state.xp_points < 100: rank = "Substitute"
    elif st.session_state.xp_points < 200: rank = "Tenured Teacher"
    elif st.session_state.xp_points < 300: rank = "Principal"
    else: rank = "THE SUPERINTENDENT"
    
    st.subheader(f"Rank: {rank}")
    if st.session_state.xp_points >= 300:
        st.success("🏆 Hall of Fame Eligibility Active")

# MAIN PAGE: ZIP CODE ENTRY
st.header("1. Identify Your District")
zip_input = st.text_input("Enter Zip Code:", max_chars=5)

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        # FEATURE: DISTRICT PROFILE CARD (ODEW DATA)
        st.markdown(f"### 🏫 {data['school_district']} Snapshot")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Enrollment", data['enrollment'])
        with col2: st.metric("Avg Salary", data['avg_teacher_salary'])
        with col3: st.metric("Masters Degree", data['percent_masters'])
        with col4: st.metric("House District", f"No. {data['rep_district']}")

        st.markdown("---")
        st.header("2. Personalize Your Message")
        
        # User Identification
        c_name, c_role = st.columns(2)
        with c_name: u_name = st.text_input("Full Name:", placeholder="Enter your name")
        with c_role: u_role = st.text_input("Title/Role:", value="K-8 Visual Arts Teacher")
        
        target_mode = st.radio("Target Recipient:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Stance"], horizontal=True)

        if u_name:
            # FEATURE: AGREED CONSTITUENT OPENING
            opening = f"My name is {u_name}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
            
            detail = (f"Our schools serve {data['enrollment']} students with a workforce averaging {data['avg_teacher_ex']} years of experience. "
                      f"With {data['percent_masters']} of our faculty holding Master's degrees, we provide professional stability. "
                      f"Voucher expansion threatens our ability to meet state academic standards, such as 5.1PE.")
            
            action = "As a constituent, I urge you to prioritize local public school funding. Thank you for your time."
            full_content = f"{opening}\n\n{detail}\n\n{action}"

            st.markdown("### 3. Send & Print")
            btn1, btn2 = st.columns(2)
            with btn1:
                # FEATURE: EMAIL SYNERGY (Subject & Body)
                safe_body = urllib.parse.quote(full_content)
                subject = f"Constituent Message: District {data['rep_district']} ({data['school_district']})"
                target_email = data['rep_email'] if target_mode == "📍 Local Rep" else "governor@ohio.gov"
                st.markdown(f'''<a href="mailto:{target_email}?subject={urllib.parse.quote(subject)}&body={safe_body}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND CONSTITUENT EMAIL</div></a>''', unsafe_allow_html=True)
            
            with btn2:
                # FEATURE: BLOCK FORMAT PDF
                pdf_bytes = create_block_letter(data, {"name": u_name, "title": u_role, "zip": zip_input}, full_content)
                st.download_button("📄 DOWNLOAD PRINTABLE PDF", pdf_bytes, f"Letter_Dist_{data['rep_district']}.pdf", "application/pdf")
            
            # FEATURE: MISSION LOGGING
            if st.button("✅ Log This Action (+100 XP)"):
                st.session_state.xp_points += 100
                if st.session_state.xp_points >= 300 and u_name not in st.session_state.hall_of_fame:
                    st.session_state.hall_of_fame.append(u_name)
                st.session_state.district_stats[data['school_district']] = st.session_state.district_stats.get(data['school_district'], 0) + 1
                st.rerun()

# FEATURE: HALL OF FAME & LEADERBOARD
st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    st.header("🎖️ Superintendent Hall of Fame")
    st.info(" | ".join(st.session_state.hall_of_fame))
with col_b:
    st.header("🏆 District Leaderboard")
    if st.session_state.district_stats:
        ldf = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
        st.table(ldf.sort_values(by='Actions', ascending=False).head(3))
