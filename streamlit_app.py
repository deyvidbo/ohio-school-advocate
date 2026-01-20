import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'district_stats' not in st.session_state: st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state: st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("N/A", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
# This function now takes the 'recipient_data' to dynamically address the letterhead
def create_block_letter(recipient_data, user_info, content):
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
    
    # Recipient Block (Now Dynamic)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{recipient_data['role']} {recipient_data['name']}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=recipient_data['address'])
    pdf.ln(0.3)
    
    # Salutation
    last_name = recipient_data['name'].split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {recipient_data['role']} {last_name}:")
    pdf.ln(0.3)
    
    # Body
    for p in content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # Signature Area
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # 4-line signature gap
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. APP INTERFACE ---
st.markdown("<h1 style='text-align: center; color:#B22234;'>⚖️ CLASS ACTION: OHIO</h1>", unsafe_allow_html=True)

zip_input = st.text_input("Enter Zip Code:", max_chars=5)

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        st.header("1. Personalize Your Identity")
        c_name, c_role = st.columns(2)
        with c_name: u_name = st.text_input("Full Name:", value="David M. Bothast")
        with c_role: u_role = st.text_input("Title:", value="K-8 Visual Arts Teacher")

        st.header("2. Select Your Recipient")
        target_mode = st.radio("Who are you addressing?", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], horizontal=True)

        # Recipient Logic
        if target_mode == "📍 Local Rep":
            recipient = {"name": data['rep_name'], "role": data['rep_role'], "email": data['rep_email'], "address": data['rep_address']}
        elif target_mode == "🏛️ Governor":
            recipient = {"name": "Mike DeWine", "role": "Governor", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215"}
        elif target_mode == "🛡️ Friendly Caucus":
            recipient = {"name": "Allison Russo", "role": "Minority Leader", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}
        else: # Opposition
            recipient = {"name": "Matt Huffman", "role": "Speaker of the House", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}

        if u_name:
            # Shared Content Hook
            opening = f"My name is {u_name}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
            detail = (f"Our schools serve {data['enrollment']} students with a workforce averaging {data['avg_teacher_ex']} years of experience. "
                      f"Voucher expansion threatens our ability to meet state academic standards, such as 5.1PE.")
            action = f"I urge you, as a {recipient['role']}, to prioritize local public school funding. Thank you for your time."
            full_content = f"{opening}\n\n{detail}\n\n{action}"

            st.header("3. Send or Print")
            btn1, btn2 = st.columns(2)
            
            with btn1:
                # Digital Action
                safe_body = urllib.parse.quote(full_content)
                subject = f"Constituent Message: District {data['rep_district']} ({data['school_district']})"
                st.markdown(f'''<a href="mailto:{recipient['email']}?subject={urllib.parse.quote(subject)}&body={safe_body}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND EMAIL TO {recipient['name'].upper()}</div></a>''', unsafe_allow_html=True)
            
            with btn2:
                # Physical Action (Now fully dynamic based on target_mode)
                pdf_bytes = create_block_letter(recipient, {"name": u_name, "title": u_role, "zip": zip_input}, full_content)
                st.download_button(f"📄 DOWNLOAD PRINT LETTER FOR {recipient['name'].upper()}", pdf_bytes, f"Letter_{recipient['name']}.pdf", "application/pdf")
            
            if st.button("✅ Log This Action (+100 XP)"):
                st.session_state.xp_points += 100
                st.rerun()
