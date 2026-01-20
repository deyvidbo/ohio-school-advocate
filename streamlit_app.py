import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

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
    st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Loading all 4 chunks from your CSV
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str})
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Connection Error: Ensure 'ohio_districts.csv' is in the root folder. Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. ROBUST PROFESSIONAL BLOCK FORMAT PDF GENERATOR ---
def create_block_letter(recipient_data, user_info, content):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=1.0)
    
    # Use standard Times font for professional government correspondence
    pdf.set_font("Times", '', 12)
    
    # 1. Sender Block (Left Justified)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    pdf.cell(0, 0.2, txt=user_info['title'], ln=True)
    pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True)
    pdf.ln(0.2)
    
    # 2. Date
    pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.3)
    
    # 3. Recipient Block
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=f"{recipient_data['role']} {recipient_data['name']}", ln=True)
    pdf.set_font("Times", '', 12)
    # multi_cell handles long addresses automatically
    pdf.multi_cell(0, 0.2, txt=recipient_data['address'])
    pdf.ln(0.3)
    
    # 4. Salutation (Colon for formal)
    last_name = recipient_data['name'].split()[-1]
    pdf.cell(0, 0.2, txt=f"Dear {recipient_data['role']} {last_name}:")
    pdf.ln(0.3)
    
    # 5. Body
    # Replace smart quotes/special chars to prevent PDF encoding errors
    safe_content = content.replace('’', "'").replace('“', '"').replace('”', '"')
    for p in safe_content.split('\n\n'):
        pdf.multi_cell(0, 0.2, txt=p.strip(), align='L')
        pdf.ln(0.2)
    
    # 6. Signature Area
    pdf.ln(0.2)
    pdf.cell(0, 0.2, txt="Sincerely,", ln=True)
    pdf.ln(0.8) # Standard 4-line signature gap
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
    
    # Clean output
    return pdf.output(dest="S").encode('latin-1', 'replace')

# --- 5. APP INTERFACE ---
# Logo Branding
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=320)
except:
    st.title("⚖️ CLASS ACTION: OHIO")
st.markdown("<h3 style='text-align: center; color:#B22234; margin-top:-20px;'>Advocacy Engine for Public Excellence</h3>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# SIDEBAR: STATS & HALL OF FAME
with st.sidebar:
    st.header("📋 Advocacy Mission")
    st.metric("Total Action XP", f"{st.session_state.xp_points}")
    
    # Rank Logic
    if st.session_state.xp_points < 100: rank = "Substitute"
    elif st.session_state.xp_points < 200: rank = "Tenured Teacher"
    elif st.session_state.xp_points < 300: rank = "Principal"
    else: rank = "THE SUPERINTENDENT"
    
    st.subheader(f"Current Rank: {rank}")
    
    st.markdown("---")
    st.header("🎖️ Hall of Fame")
    for name in st.session_state.hall_of_fame:
        st.write(f"⭐ {name}")

# MAIN CONTENT
st.header("1. Identify Your District")
zip_input = st.text_input("Enter Zip Code:", max_chars=5, help="Connects you to local ODEW data and your Representative.")

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        # --- FEATURE: DISTRICT DASHBOARD ---
        st.markdown(f"### 🏫 {data['school_district']} Snapshot")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Enrollment", data['enrollment'])
        with col2: st.metric("Avg Salary", data['avg_teacher_salary'])
        with col3: st.metric("Masters Degree", data['percent_masters'])
        with col4: st.metric("House District", f"No. {data['rep_district']}")

        st.markdown("---")
        st.header("2. Personalize Your Identity")
        
        c_name, c_role = st.columns(2)
        with c_name: 
            u_name = st.text_input("Full Name:", value="David M. Bothast")
        with c_role: 
            u_role = st.text_input("Title/Professional Role:", value="K-8 Visual Arts Teacher")
        
        st.header("3. Select Your Recipient")
        target_mode = st.radio("Address your advocacy to:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], horizontal=True)

        # Recipient Selection Logic
        if target_mode == "📍 Local Rep":
            recipient = {"name": data['rep_name'], "role": data['rep_role'], "email": data['rep_email'], "address": data['rep_address']}
        elif target_mode == "🏛️ Governor":
            recipient = {"name": "Mike DeWine", "role": "Governor", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215"}
        elif target_mode == "🛡️ Friendly Caucus":
            recipient = {"name": "Allison Russo", "role": "Minority Leader", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}
        else:
            recipient = {"name": "Matt Huffman", "role": "Speaker of the House", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"}

        if u_name:
            # AGREED CONSTITUENT CONTENT
            opening = f"My name is {u_name}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
            detail = (f"Our schools serve {data['enrollment']} students with a workforce averaging {data['avg_teacher_ex']} years of experience. "
                      f"With {data['percent_masters']} of our faculty holding Master's degrees, we provide professional stability. "
                      f"Voucher expansion threatens our ability to meet state academic standards, such as 5.1PE.")
            action = f"As a constituent, I urge you, as a {recipient['role']}, to prioritize local public school funding. Thank you for your consideration."
            
            full_content = f"{opening}\n\n{detail}\n\n{action}"

            st.header("4. Send & Print")
            btn1, btn2 = st.columns(2)
            
            with btn1:
                # Digital Action
                safe_body = urllib.parse.quote(full_content)
                subject = f"Constituent Message: District {data['rep_district']} ({data['school_district']})"
                st.markdown(f'''<a href="mailto:{recipient['email']}?subject={urllib.parse.quote(subject)}&body={safe_body}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:1.1em;">✉️ SEND EMAIL TO {recipient['name'].upper()}</div></a>''', unsafe_allow_html=True)
            
            with btn2:
                # Physical Action
                pdf_bytes = create_block_letter(recipient, {"name": u_name, "title": u_role, "zip": zip_input}, full_content)
                st.download_button(f"📄 DOWNLOAD PRINT LETTER FOR {recipient['name'].upper()}", pdf_bytes, f"Letter_{recipient['name'].replace(' ', '_')}.pdf", "application/pdf")
            
            # MISSION SUCCESS & XP
            st.markdown("---")
            if st.button("✅ I Completed This Mission (+100 XP)"):
                st.session_state.xp_points += 100
                if st.session_state.xp_points >= 300 and u_name not in st.session_state.hall_of_fame:
                    st.session_state.hall_of_fame.append(u_name)
                st.session_state.district_stats[data['school_district']] = st.session_state.district_stats.get(data['school_district'], 0) + 1
                st.balloons()
                st.rerun()
    else:
        st.error("District not found. Please verify your Zip Code.")

# LEADERBOARD (Bottom)
if st.session_state.district_stats:
    st.markdown("---")
    st.header("🏆 District Leaderboard")
    ldf = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Total Actions'])
    st.table(ldf.sort_values(by='Total Actions', ascending=False).head(5))
