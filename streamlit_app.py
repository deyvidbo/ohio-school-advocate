import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'district_stats' not in st.session_state: st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state: st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. ROBUST DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Load CSV while specifically handling "bad lines" caused by comma-suffixes
        df = pd.read_csv("ohio_districts.csv", 
                         dtype={'zip_code': str, 'rep_district': str}, 
                         on_bad_lines='warn', 
                         quotechar='"')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
def create_block_letter(recipient_data, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.add_page()
    pdf.set_font("Times", '', 12)
    
    # 1. Sender Info (Block Format)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.3)
    
    # 2. Recipient Info
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{recipient_data['role']} {recipient_data['name']}", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 0.2, txt=recipient_data['address'])
    pdf.ln(0.3)
    
    # 3. Salutation
    last_name = recipient_data['name'].split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {recipient_data['role']} {last_name}:")
    pdf.ln(0.3)
    
    # 4. Body Content
    safe_content = content.replace('’', "'").replace('“', '"').replace('”', '"')
    for p in safe_content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # 5. Closing & Signature Line
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # 4-line signature gap
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    return pdf.output(dest="S").encode('latin-1', 'replace')

# --- 5. INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try: st.image(logo_url, width=320)
except: st.title("⚖️ CLASS ACTION: OHIO")
st.markdown("<h3 style='text-align: center; color:#B22234; margin-top:-20px;'>2026 Public Education Advocacy Engine</h3>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR: GAMIFICATION
with st.sidebar:
    st.header("📋 Mission Status")
    st.metric("Action XP", f"{st.session_state.xp_points}")
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 300 else "THE SUPERINTENDENT"
    st.subheader(f"Rank: {rank}")
    st.markdown("---")
    st.header("🎖️ Hall of Fame")
    for name in st.session_state.hall_of_fame: st.write(f"⭐ {name}")

# CORE DASHBOARD
zip_input = st.text_input("Enter District Zip Code:", max_chars=5)

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        # Identity Inputs
        c1, c2 = st.columns(2)
        with c1: u_name = st.text_input("Full Name:", value="David M. Bothast")
        with c2: u_role = st.text_input("Title:", value="K-8 Visual Arts Teacher")

        st.header("Address Your Advocacy")
        target_mode = st.radio("Recipient:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], horizontal=True)

        # 2026 Recipient Mapping
        if target_mode == "📍 Local Rep":
            recipient = {"name": data['rep_name'], "role": data['rep_role'], "email": data['rep_email'], "address": data['rep_address']}
        elif target_mode == "🏛️ Governor":
            recipient = {"name": "Mike DeWine", "role": "Governor", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215"}
        elif target_mode == "🛡️ Friendly Caucus":
            recipient = {"name": "C. Allison Russo", "role": "Minority Leader", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}
        else:
            recipient = {"name": "Matt Huffman", "role": "Speaker (Designate)", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}

        if u_name:
            # CONSTITUENT STATEMENT
            opening = f"My name is {u_name}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
            detail = (f"Our schools serve {data['enrollment']} students with an average of {data['avg_teacher_ex']} years of experience. "
                      f"State standards like 5.1PE require professional stability that voucher expansion undermines.")
            action = f"I urge you, as a {recipient['role']}, to prioritize public education funding. Thank you."
            full_content = f"{opening}\n\n{detail}\n\n{action}"

            st.header("Actions")
            b1, b2 = st.columns(2)
            with b1:
                safe_body = urllib.parse.quote(full_content)
                subject = f"Constituent Message: District {data['rep_district']} ({data['school_district']})"
                st.markdown(f'''<a href="mailto:{recipient['email']}?subject={urllib.parse.quote(subject)}&body={safe_body}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND EMAIL</div></a>''', unsafe_allow_html=True)
            with b2:
                pdf_bytes = create_block_letter(recipient, {"name": u_name, "title": u_role, "zip": zip_input}, full_content)
                st.download_button(f"📄 PRINT LETTER FOR {recipient['name'].upper()}", pdf_bytes, f"Letter_{recipient['name']}.pdf", "application/pdf")

            if st.button("✅ Log Mission (+100 XP)"):
                st.session_state.xp_points += 100
                if st.session_state.xp_points >= 300 and u_name not in st.session_state.hall_of_fame:
                    st.session_state.hall_of_fame.append(u_name)
                st.session_state.district_stats[data['school_district']] = st.session_state.district_stats.get(data['school_district'], 0) + 1
                st.balloons()
                st.rerun()
