import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse

# --- 1. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        # We force the zip_code to be read as a string so "04532" doesn't become "4532"
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
    if rep.get('rep_stance') == "Hostile":
        subject = f"URGENT: Financial Distress in {user_district}"
        body = (
            f"Dear {rep['rep_role']} {rep['rep_name']},\n\n"
            f"I am a voter in {user_district} (Zip: {rep['zip_code']}). "
            f"The decision to freeze public school funding at 2022 levels while expanding "
            f"EdChoice vouchers is draining our classrooms.\n\n"
        )
        if rep.get('rep_career') == "Re-election":
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
    
    # Header
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    pdf.ln(5)
    
    # Recipient Block
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
    pdf.set_font("Arial", size=12)
    
    # --- CRASH PREVENTION FIX ---
    # This .get() method asks for the address, but uses a default if missing.
    # This prevents the KeyError crash you saw.
    safe_address = str(rep.get('rep_address', 'Ohio Statehouse, Columbus, OH'))
    pdf.cell(0, 5, txt=safe_address, ln=1) 
    
    pdf.ln(10)
    pdf.multi_cell(0, 7, txt=content)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MOBILE-FIRST INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

st.title("📢 Ohio Legislator Communicator")
st.markdown("### 1. Enter Your Details")

if df.empty:
    st.error("⚠️ System Error: 'ohio_districts.csv' file not found. Please check GitHub.")
    st.stop()

# --- INPUTS (Optimized for Mobile & Autofill) ---
col1, col2 = st.columns(2)

with col1:
    zip_code = st.text_input("Zip Code", max_chars=5, placeholder="45011")

with col2:
    user_name = st.text_input("Full Name", "Concerned Citizen")

# --- SEARCH LOGIC ---
rep_match = get_rep_from_zip(zip_code)

st.markdown("---") 

# --- RESULTS DISPLAY ---
if rep_match:
    st.success(f"📍 District Found: **{rep_match['school_district']}**")
    
    with st.container():
        st.markdown(f"### Your Representative: {rep_match['rep_name']}")
        
        # Stance Check
        if rep_match.get('rep_stance') == "Hostile":
            st.error(f"❌ **Voted for Cuts / Vouchers**")
        else:
            st.success(f"✅ **Public School Supporter**")
            
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
            
        with st.expander("👀 Preview the Letter Text"):
            st.text_area("Message Preview", body, height=250)

elif zip_code and len(zip_code) == 5:
    st.warning(f"⚠️ Zip Code {zip_code} is not in our database yet.")
    st.info("We are currently adding more districts.")
    
else:
    st.info("👆 Enter your Zip Code above to find your representative.")

st.markdown("---")
st.caption("Advocacy Tool | Data: Ohio 136th General Assembly")
