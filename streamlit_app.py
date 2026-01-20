import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse

# --- 1. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        # Load data and ensure Zip Codes are text (keep leading zeros)
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        # Fill missing text data with empty strings to prevent crashes
        df.fillna("", inplace=True)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

# --- 2. LOGIC FUNCTIONS ---

def get_rep_from_zip(zip_input):
    if df.empty: return None
    match = df[df['zip_code'] == zip_input]
    if not match.empty: return match.iloc[0].to_dict()
    return None

def generate_message(rep, user_name, user_district):
    # 1. BASE OPENING
    body = (
        f"Dear {rep['rep_role']} {rep['rep_name']},\n\n"
        f"I am a voter and advocate for {user_district} (Zip: {rep['zip_code']}). "
    )

    # 2. SMART DATA INJECTION (The New Feature)
    # We check if the 'enrollment' column has data. If so, we add a 'Data Hook'.
    if str(rep.get('enrollment')) != "" and str(rep.get('poverty_rate')) != "":
        body += (
            f"Our district serves approximately {rep['enrollment']} students, "
            f"{rep['poverty_rate']} of whom are economically disadvantaged. "
            f"These students rely on stable public funding, not privatization schemes.\n\n"
        )
    else:
        # Fallback if no data in CSV
        body += "Our students rely on stable public funding, not privatization schemes.\n\n"

    # 3. THE CORE ARGUMENT
    if rep.get('rep_stance') == "Hostile":
        body += (
            f"Your decision to freeze public school funding at outdated 2022 cost levels—while "
            f"simultaneously expanding universal EdChoice vouchers—is a direct attack on our classroom budgets. "
            f"You are forcing us to do more with less while private tuitions are fully subsidized.\n\n"
        )
        if rep.get('rep_career') == "Re-election":
            body += (
                "Teachers and parents in this district are organizing. We are paying close attention to "
                "this budget cycle. We need you to vote to UNFREEZE the Fair School Funding Plan inputs immediately."
            )
        else:
            body += (
                "As you approach the end of your term, consider your legacy. Please do not leave office "
                "as the leader who dismantled the promise of public education in Ohio."
            )
    else:
        body += (
            f"Thank you for your continued defense of the Fair School Funding Plan. However, the current "
            f"'base cost' freeze is hurting us. Please aggressively push leadership to update the funding inputs "
            f"to match current inflation."
        )

    full_text = f"{body}\n\nSincerely,\n{user_name}\n{user_district} Community Member"
    subject = f"Urgent: Funding Crisis in {user_district}"
    
    return subject, full_text

def create_pdf(rep, user_name, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Professional Header
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    pdf.cell(0, 5, txt=f"Constituent of {rep['school_district']}", ln=1)
    pdf.ln(5)
    
    # Recipient Block
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
    pdf.set_font("Arial", size=11)
    
    # Crash-Proof Address
    safe_address = str(rep.get('rep_address'))
    if safe_address == "" or safe_address == "nan": 
        safe_address = "Ohio Statehouse, Columbus, OH 43215"
        
    pdf.cell(0, 5, txt=safe_address, ln=1) 
    pdf.ln(10)
    
    # Body Text
    pdf.multi_cell(0, 6, txt=content)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

col1, col2 = st.columns([3, 1])
with col1:
    st.title("📢 Ohio Legislator Communicator")
with col2:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Seal_of_Ohio.svg/100px-Seal_of_Ohio.svg.png", width=80)

st.markdown("**Data Source:** *Ohio Dept of Education & Workforce (FY2025)*")

if df.empty:
    st.error("⚠️ System Error: 'ohio_districts.csv' file not found.")
    st.stop()

# --- INPUTS ---
col1, col2 = st.columns(2)
with col1:
    zip_code = st.text_input("Zip Code", max_chars=5, placeholder="45011")
with col2:
    user_name = st.text_input("Full Name", "Concerned Citizen")

# --- RESULTS ---
rep_match = get_rep_from_zip(zip_code)

st.markdown("---") 

if rep_match:
    # 1. DISTRICT INFO CARD
    st.subheader(f"📍 {rep_match['school_district']}")
    
    # Show stats if they exist in CSV
    if str(rep_match.get('enrollment')) != "":
        stat1, stat2, stat3 = st.columns(3)
        stat1.metric("Students", rep_match['enrollment'])
        stat2.metric("Poverty Rate", rep_match['poverty_rate'])
        stat3.metric("Minority Rate", rep_match['minority_rate'])
        st.caption("*Demographic data sourced from ODEW Report Cards*")
    
    st.markdown("---")

    # 2. REP CARD
    with st.container():
        st.markdown(f"### Representative: {rep_match['rep_name']}")
        
        if rep_match.get('rep_stance') == "Hostile":
            st.error(f"❌ **Voting Record:** Supported EdChoice Expansion / Funding Freeze")
        else:
            st.success(f"✅ **Voting Record:** Public School Ally")
            
        subject, body = generate_message(rep_match, user_name, rep_match['school_district'])
        
        # Action Buttons
        safe_sub = urllib.parse.quote(subject)
        safe_body = urllib.parse.quote(body)
        mailto = f"mailto:{rep_match['rep_email']}?subject={safe_sub}&body={safe_body}"
        
        b_col1, b_col2 = st.columns(2)
        with b_col1:
             st.markdown(f"""
             <a href="{mailto}" target="_blank" style="text-decoration:none;">
                <button style="width:100%; padding:15px; background-color:#FF4B4B; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; margin-bottom:10px;">
                    ✉️ Open Email App
                </button>
             </a>
             """, unsafe_allow_html=True)
             
        with b_col2:
            try:
                pdf_data = create_pdf(rep_match, user_name, body)
                b64 = base64.b64encode(pdf_data).decode()
                filename = f"Letter_to_{rep_match['rep_name'].replace(' ', '_')}.pdf"
                st.markdown(f"""
                <a href="data:application/octet-stream;base64,{b64}" download="{filename}" style="text-decoration:none;">
                    <button style="width:100%; padding:15px; background-color:#F0F2F6; color:#31333F; border:1px solid #ccc; border-radius:8px; font-weight:bold; cursor:pointer;">
                        📄 Download PDF Letter
                    </button>
                </a>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"PDF Error: {e}")
            
        with st.expander("👀 Preview Letter"):
            st.text_area("Content", body, height=300)

elif zip_code and len(zip_code) == 5:
    st.warning("⚠️ Zip Code not found in database. We are expanding coverage daily.")
else:
    st.info("👆 Enter your Zip Code to see your District Data & Representative.")
