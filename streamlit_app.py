import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="centered"
)

# --- 2. SESSION STATE ---
params = st.query_params
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = int(params.get("xp", 0))

if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}

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
# Follows guidelines from LiveAbout for formal business correspondence
def create_professional_letter(target_rep, user_info, content):
    # US Letter size (8.5x11), Portrait, units in Inches
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    
    # Font: Times New Roman, 12pt
    pdf.set_font("Times", '', 12)
    pdf.set_left_margin(1.0)
    pdf.set_right_margin(1.0)
    
    # A. Writer's Contact Information
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2) # Space after contact info
    
    # B. Date
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.2) # Space before recipient info
    
    # C. Recipient's Contact Information
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=target_rep.get('rep_address', '77 S. High St, Columbus, OH 43215'))
    pdf.ln(0.2) # Space before salutation
    
    # D. Salutation (Colon used for formal letters)
    rep_last_name = target_rep.get('rep_name', 'Legislator').split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {target_rep.get('rep_role', 'Representative')} {rep_last_name}:", ln=True)
    pdf.ln(0.2) # Space before body
    
    # E. Body of Letter: Left-justified, single-spaced paragraphs
    paragraphs = content.split('\n\n')
    for p in paragraphs:
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2) # Double space between paragraphs
    
    # F. Closing & Signature Block
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # 4 spaces for handwritten signature
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. ADVOCACY CONTENT GENERATOR ---
def generate_content(target_rep, user_info, mode):
    # Paragraph 1: Introduction and Teacher Identity
    intro = (f"My name is {user_info['name']}, and I am writing to you today as a {user_info['title']} and a voter "
             f"in the {user_info['district']} (Zip: {user_info['zip']}).")
    
    # Paragraph 2: Details and Background
    detail = (f"As a visual arts educator at Linden Elementary, I see firsthand how the Fair School Funding Plan "
              f"supports our {user_info['enrollment']} students. I am deeply concerned that diverting public dollars "
              f"toward private voucher expansion will undermine our ability to provide essential arts education.")
    
    # Paragraph 3: Call to Action and Thank You
    conclusion = ("I urge you to prioritize local public school funding to protect the programs that help our children thrive. "
                  "Thank you for considering my request and for your service to the people of Ohio.")
    
    return f"{intro}\n\n{detail}\n\n{conclusion}"

# --- 6. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=350) 
except:
    st.title("⚖️ CLASS ACTION")
st.markdown("<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>CLASS ACTION</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# DASHBOARD
st.info(f"🏆 Rank: **{st.session_state.xp_points} XP** | Mission: Advocate for {df['school_district'].nunique() if not df.empty else 'Ohio'} Districts")

# INPUTS
st.header("1. Your Information")
c1, c2 = st.columns(2)
with c1:
    user_name = st.text_input("Full Name", value="David M. Bothast")
    zip_code = st.text_input("Zip Code", max_chars=5, value="45056")
with c2:
    # Explicit teacher demographic inclusion
    user_title = st.text_input("Professional Title", value="K-8 Visual Arts Teacher")

if zip_code:
    res = df[df['zip_code'] == zip_code]
    if not res.empty:
        user_data = res.iloc[0].to_dict()
        dist_name = user_data['school_district']
        user_info = {
            "name": user_name, "zip": zip_code, "title": user_title,
            "district": dist_name, "enrollment": user_data.get('enrollment', '')
        }
        
        st.success(f"📍 Loaded District: **{dist_name}**")
        
        st.header("2. Take Action")
        mode = st.radio("Choose Recipient:", ["📍 Local Rep", "🛡️ Defenders", "🚫 Opponents", "🏛️ Governor"], horizontal=True)
        
        subject, content = generate_content(user_data, user_info, mode)
        
        # --- EMAIL ACTION (Mobile-Friendly mailto:) ---
        # The mailto: protocol automatically opens the default email app on mobile devices
        safe_body = urllib.parse.quote(content)
        target_email = user_data['rep_email'] if mode == "📍 Local Rep" else "governor@ohio.gov"
        mailto_link = f"mailto:{target_email}?subject=Advocacy from {dist_name}&body={safe_body}"
        
        st.markdown(f'''
            <a href="{mailto_link}" style="text-decoration:none;">
                <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:1.1em;">
                    ✉️ OPEN EMAIL APP (Mobile-Ready)
                </div>
            </a>
        ''', unsafe_allow_html=True)
        
        st.write("")
        
        # --- PDF ACTION (Block Format Letter) ---
        pdf_data = create_professional_letter(user_data, user_info, content)
        st.download_button(
            label="📄 GENERATE PRINTABLE LETTER (Professional Block Format)",
            data=pdf_data,
            file_name=f"Class_Action_Letter_{dist_name}.pdf",
            mime="application/pdf"
        )
        
        if st.button("✅ I Sent My Message! (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[dist_name] = st.session_state.district_stats.get(dist_name, 0) + 1
            st.rerun()

# --- 7. LEADERBOARD ---
st.markdown("---")
if st.session_state.district_stats:
    st.header("🏆 Most Active Districts")
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
    st.table(leader_df.sort_values(by='Actions', ascending=False).head(5))
