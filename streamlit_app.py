import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse

# --- 1. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 5, txt=str(rep['rep_address']), ln=1) 
    pdf.ln(10)
    pdf.multi_cell(0, 7, txt=content)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MOBILE-FIRST INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

# Title Section
st.title("📢 Ohio Legislator Communicator")
st.markdown("### 1. Enter Your Details")

# ERROR CHECK: If CSV is missing
if df.empty:
    st.error("⚠️ System Error: 'ohio_districts.csv' file not found. Please contact administrator.")
    st.stop()

# --- MOBILE FIX: INPUTS ON MAIN SCREEN ---
# We use columns to make it look good on desktop, but they stack vertically on mobile automatically.
col1, col2 = st.columns(2)

with col1:
    # Key change: This is now front-and-center, not hidden in a sidebar
    zip_code = st.text_input("Enter Zip Code (Required)", max_chars=5, placeholder="e.g. 45011")

with col2:
    user_name = st.text_input("Your Name (For Signature)", "Concerned Citizen")

# --- SEARCH LOGIC ---
rep_match = get_rep_from_zip(zip_code)

st.markdown("---") # Divider line

# --- RESULTS DISPLAY ---
if rep_match:
    st.success(f"📍 District Found: **{rep_match['school_district']}**")
    
    # We use a container to group the result nicely
    with st.container():
        st.markdown(f"### Your Representative: {rep_match['rep_name']}")
        
        # Stance Badge
        if rep_match['rep_stance'] == "Hostile":
            st.error(f"❌ **Voted for Cuts / Vouchers**")
        else:
            st.success(f"✅ **Public School Supporter**")
            
        # Generate Content
        subject, body = generate_message(rep_match, user_name, rep_match['school_district'])
        
        # Action Buttons (Full width on mobile)
        safe_sub = urllib.parse.quote(subject)
        safe_body = urllib.parse.quote(body)
        mailto = f"mailto:{rep_match['rep_email']}?subject={safe_sub}&body={safe_body}"
        
        # Use columns for buttons, but on mobile they will be easy to tap
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
            
        # Preview Box
        with st.expander("👀 Preview the Letter Text"):
            st.text_area("Message Preview", body, height=250)

elif zip_code and len(zip_code) == 5:
    st.warning(f"⚠️ Zip Code {zip_code} is not in our database yet.")
    st.info("We are currently adding more districts. Please check back soon.")
    
else:
    # "Empty State" - Instructions for the user
    st.info("👆 Please enter your 5-digit Zip Code above to find your representative.")

# Footer
st.markdown("---")
st.caption("This tool is for educational and advocacy purposes. Data is based on Ohio 136th General Assembly records.")
