import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide"  # Wider layout for the new Dashboard
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
        # Expected columns: zip_code, school_district, enrollment, voucher_loss, rep_name, rep_email, rep_address, rep_stance
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
    
    # Sender Block
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
    
    # Salutation
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:", ln=True)
    pdf.ln(0.2)
    
    # Body (Single spaced, double spaced between paragraphs)
    paragraphs = content.split('\n\n')
    for p in paragraphs:
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Closing
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # Space for handwritten signature
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=300) 
except:
    st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>CLASS ACTION ADVOCACY DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR: STATS & PROGRESS
with st.sidebar:
    st.header("📋 Mission Status")
    st.metric("Your Total XP", f"{st.session_state.xp_points}")
    st.markdown("---")
    st.write("**Teacher Demographics**")
    user_name = st.text_input("Full Name", value="David M. Bothast")
    user_title = st.text_input("Professional Title", value="K-8 Visual Arts Teacher")
    zip_code = st.text_input("Home Zip Code", max_chars=5, value="45056")

# MAIN PAGE: DISTRICT SEARCH
st.header("1. District Funding Gap Analysis")
if not df.empty:
    all_districts = sorted(df['school_district'].unique())
    selected_district = st.selectbox("Search for your School District:", ["Select a District..."] + all_districts)

    if selected_district != "Select a District...":
        dist_data = df[df['school_district'] == selected_district].iloc[0]
        
        # Dashboard Display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Students Served", dist_data['enrollment'])
        with col2:
            # Highlight funding loss for advocacy
            st.metric("Voucher Funding Loss", f"${dist_data.get('voucher_loss', 'Unknown')}", delta="- Funding Gap", delta_color="inverse")
        with col3:
            st.metric("Academic Standards", "Ohio Visual Arts", help="Focusing on 5.1PE Incorporate constructive feedback")

        st.markdown("---")
        st.header("2. Take Action")
        mode = st.radio("Select Recipient:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Defenders", "🚫 Opponents"], horizontal=True)

        # Generate Content with Data Hooks
        intro = f"My name is {user_name}, and I am a {user_title} writing to you regarding the {selected_district}."
        detail = (f"Our district serves {dist_data['enrollment']} students. Currently, we face a projected funding gap of "
                  f"${dist_data.get('voucher_loss', '0')} due to voucher expansion. This loss directly impacts our ability "
                  f"to meet state standards, such as 5.1PE, which ensures students receive quality arts instruction.")
        action = "I urge you to prioritize public education funding. Thank you for your consideration."
        full_content = f"{intro}\n\n{detail}\n\n{action}"

        # --- MOBILE FRIENDLY EMAIL (mailto:) ---
        safe_body = urllib.parse.quote(full_content)
        target_email = dist_data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
        mailto_link = f"mailto:{target_email}?subject=Advocacy for {selected_district}&body={safe_body}"
        
        st.markdown(f'''
            <a href="{mailto_link}" style="text-decoration:none;">
                <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">
                    ✉️ OPEN EMAIL APP (Mobile-Ready)
                </div>
            </a>
        ''', unsafe_allow_html=True)
        
        st.write("")

        # --- PROFESSIONAL PRINTABLE LETTER ---
        pdf_data = create_professional_letter(dist_data, {"name": user_name, "title": user_title, "zip": zip_code}, full_content)
        st.download_button(
            label="📄 DOWNLOAD PROFESSIONAL BLOCK LETTER",
            data=pdf_data,
            file_name=f"Letter_{selected_district}.pdf",
            mime="application/pdf"
        )

        if st.button("✅ I Completed This Mission! (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[selected_district] = st.session_state.district_stats.get(selected_district, 0) + 1
            st.rerun()

# LEADERBOARD
st.markdown("---")
if st.session_state.district_stats:
    st.header("🏆 Most Active Advocacy Districts")
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
    st.table(leader_df.sort_values(by='Actions', ascending=False).head(5))
