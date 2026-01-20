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
    initial_sidebar_state="collapsed"
)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state:
    st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Loading the Master CSV containing all 4 chunks
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("N/A", inplace=True)
        # Clean numeric columns for calculations
        for col in ['enrollment', 'avg_teacher_salary', 'avg_teacher_ex']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading district data: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
# Standard: Left-justified, Single-spaced, 12pt Times, 1" Margins
def create_professional_letter(target_rep, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.add_page()
    pdf.set_font("Times", '', 12)
    
    # Header: Sender Information
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
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S High St, Columbus, OH 43215'))
    pdf.ln(0.2)
    
    # Salutation (Colon for formal/professional)
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:")
    pdf.ln(0.4)
    
    # Body Paragraphs
    for p in content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Closing & Signature Block (4 blank lines for physical signature)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) 
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
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>OHIO ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# XP & RANK SIDEBAR
with st.sidebar:
    st.header("📋 Advocacy Mission")
    st.metric("Total XP Earned", f"{st.session_state.xp_points}")
    # Automatic Rank Progression
    if st.session_state.xp_points < 100:
        st.info("Current Rank: Substitute")
    elif st.session_state.xp_points < 200:
        st.success("Current Rank: Tenured Teacher")
    elif st.session_state.xp_points < 300:
        st.success("Current Rank: Principal")
    else:
        st.success("🏆 Rank: THE SUPERINTENDENT")
        if "David M. Bothast" not in st.session_state.hall_of_fame:
            st.session_state.hall_of_fame.append("Educator Pioneer")

# MAIN PAGE: ZIP CODE ENGINE
st.header("1. Enter Zip Code to Load District Data")
zip_input = st.text_input("Enter Zip Code:", max_chars=5, help="This connects you to your local district and statehouse representative.")

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        dist_name = data['school_district']
        
        # --- FEATURE: DISTRICT PROFILE CARD ---
        st.markdown(f"### 🏫 {dist_name} Statistics")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Enrollment", f"{int(data['enrollment']):,}")
            st.write(f"**Poverty Rate:** {data['poverty_rate']}")
        with c2:
            st.metric("Avg Salary", f"${int(data['avg_teacher_salary']):,}")
            st.write(f"**Experience:** {data['avg_teacher_ex']} Yrs")
        with c3:
            st.metric("Masters Degree", data['percent_masters'])
            st.write(f"**Minority Rate:** {data['minority_rate']}")
        with c4:
            st.metric("Target Rep", data['rep_name'])
            st.write(f"**Stance:** {data['rep_stance']}")

        st.markdown("---")
        st.header("2. Professional Action Center")
        mode = st.radio("Choose Recipient Protocol:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Stance"], horizontal=True)

        # Default User Info (Streamlined per your instructions)
        user_info = {
            "name": "David M. Bothast", 
            "title": "K-8 Visual Arts Teacher", 
            "zip": zip_input
        }
        
        # Content Generator: Infuses ODEW Teacher Metrics for Authority
        intro = f"I am writing to you today as a {user_info['title']} and a voter in the {dist_name} (Zip: {zip_input})."
        detail = (f"According to latest ODEW metrics, our district serves {int(data['enrollment']):,} students. "
                  f"Our workforce is composed of highly qualified professionals with an average of {data['avg_teacher_ex']} years of classroom experience, "
                  f"with {data['percent_masters']} of our faculty holding Master's degrees. This level of expertise is threatened by the diversion of funds "
                  f"to private vouchers, which directly impacts our ability to meet state academic standards like 5.1PE.")
        action = "I urge you to prioritize local public school funding to protect our professional workforce and students. Thank you for your consideration."
        full_content = f"{intro}\n\n{detail}\n\n{action}"

        # --- FEATURE: MOBILE & PRINT CONNECTORS ---
        ca, cb = st.columns(2)
        with ca:
            # mailto: Protocol for immediate phone app connection
            safe_body = urllib.parse.quote(full_content)
            target = data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
            st.markdown(f'''<a href="mailto:{target}?subject=Advocacy for {dist_name}&body={safe_body}" style="text-decoration:none;">
                <div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;font-size:1.2em;">✉️ OPEN MOBILE EMAIL APP</div></a>''', unsafe_allow_html=True)
        with cb:
            # Professional Block Format Download
            pdf_bytes = create_professional_letter(data, user_info, full_content)
            st.download_button("📄 DOWNLOAD BLOCK FORMAT LETTER (PDF)", pdf_bytes, f"Letter_{dist_name}.pdf", "application/pdf")
        
        # MISSION SUCCESS BUTTON
        if st.button("✅ Log This Action & Earn +100 XP"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[dist_name] = st.session_state.district_stats.get(dist_name, 0) + 1
            st.success("Mission Accomplished! Progress tracked.")
            st.rerun()
    else:
        st.error("District not found. Please verify the Zip Code is an Ohio-based code.")

# --- FEATURE: HALL OF FAME ---
st.markdown("---")
st.header("🎖️ Superintendent Hall of Fame")
st.write("Celebrating the educators who have reached the highest level of advocacy:")
st.info(" | ".join(st.session_state.hall_of_fame))

# --- FEATURE: LEADERBOARD ---
if st.session_state.district_stats:
    st.header("🏆 District Activity Leaderboard")
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions Taken'])
    st.table(leader_df.sort_values(by='Actions Taken', ascending=False).head(5))
