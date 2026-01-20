import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse

# --- 1. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        # Reads the CSV from GitHub
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

# --- 2. LOGIC FUNCTIONS ---

def get_rep_from_zip(zip_input):
    """Finds the Rep based on Zip Code."""
    if df.empty:
        return None
    match = df[df['zip_code'] == zip_input]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None

def generate_message(rep, user_name, user_district):
    """Generates the persuasive text."""
    if rep['rep_stance'] == "Hostile":
        subject = f"URGENT: Financial Distress in {user_district}"
        body = (
            f"Dear {rep['rep_role']} {rep['rep_name']},\n\n"
            f"I am a voter in {user_district} (Zip: {rep['zip_code']}). "
            f"The decision to freeze public school funding at 2022 levels while expanding "
            f"EdChoice vouchers is draining our classrooms.\n\n"
        )
        if rep['rep_career'] == "Re-election":
            body += "We are organizing locally for the upcoming election. We need you to support public schools now."
        else:
            body += "Please consider your legacy. Do not be the leader who dismantled Ohio's public education."
    else:
        subject = f"Support Needed: {user_district}"
        body = f"Dear {rep['rep_role']} {rep['rep_name']},\n\nThank you for supporting {user_district}. Please keep fighting to update the Fair School Funding Plan inputs."

    full_text = f"{body}\n\nSincerely,\n{user_name}\n{user_district} Resident"
    return subject, full_text

def create_pdf(rep, user_name, content):
    """Generates the PDF with the Official Address."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # User Info
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    pdf.ln(5)
    
    # Official Recipient Address Block
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
    pdf.set_font("Arial", size=12)
    # THIS IS THE NEW PART THAT PRINTS THE ADDRESS
    pdf.cell(0, 5, txt=str(rep['rep_address']), ln=1) 
    
    pdf.ln(10)
    
    # Body
    pdf.multi_cell(0, 7, txt=content)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

st.title("📢 Ohio Legislator Communicator")
st.markdown("Enter your **Zip Code** to automatically find your School District and Representative.")

if df.empty:
    st.error("⚠️ Error: Could not find 'ohio_districts.csv'. Please create this file in GitHub.")
    st.stop()

with st.sidebar:
    st.header("1. Your Info")
    user_name = st.text_input("Your Name", "Concerned Citizen")
    
    st.header("2. Find Your District")
    zip_code = st.text_input("Enter Zip Code", max_chars=5)
    
    rep_match = get_rep_from_zip(zip_code)

# MAIN DISPLAY
if rep_match:
    st.divider()
    st.subheader(f"📍 District Found: {rep_match['school_district']}")
    
    with st.expander(f"{rep_match['rep_role']} {rep_match['rep_name']} ({rep_match['rep_party']})", expanded=True):
        
        # Stance Check
        if rep_match['rep_stance'] == "Hostile":
            st.error(f"⚠️ **Voting Record:** Voted for EdChoice / Funding Cuts")
        else:
            st.success(f"✅ **Voting Record:** Public School Supporter")
            
        subject, body = generate_message(rep_match, user_name, rep_match['school_district'])
        
        col1, col2 = st.columns([1,1])
        
        # EMAIL BUTTON
        safe_sub = urllib.parse.quote(subject)
        safe_body = urllib.parse.quote(body)
        mailto = f"mailto:{rep_match['rep_email']}?subject={safe_sub}&body={safe_body}"
        with col1:
             st.markdown(f"""<a href="{mailto}" target="_blank"><button style="width:100%; padding:10px; background-color:#FF4B4B; color:white; border:none; border-radius:5px; cursor:pointer;">✉️ Email Draft</button></a>""", unsafe_allow_html=True)
        
        # PDF BUTTON
        pdf_data = create_pdf(rep_match, user_name, body)
        b64 = base64.b64encode(pdf_data).decode()
        # Clean the filename
        filename = f"Letter_to_{rep_match['rep_name'].replace(' ', '_')}.pdf"
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}"><button style="width:100%; padding:10px; background-color:#F0F2F6; border:1px solid #ccc; border-radius:5px; cursor:pointer;">📄 Download PDF</button></a>'
        with col2:
            st.markdown(href, unsafe_allow_html=True)
            
        st.text_area("Preview Message", body, height=200)

elif zip_code and len(zip_code) == 5:
    st.warning(f"Zip Code {zip_code} is not in our database yet.")
else:
    st.info("👈 Enter a Zip Code (e.g., 45011) to begin.")
