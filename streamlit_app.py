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

def generate_message(target_rep, user_info, mode):
    """
    Generates text. 
    target_rep: The specific politician (or {} if mass email)
    user_info: Dictionary containing user's name, district name, and STATS
    mode: 'District', 'Ally', or 'Hostile'
    """
    
    # 1. CONSTRUCT THE "DATA HOOK"
    # This paragraph is now used in ALL email types.
    data_hook = ""
    if user_info.get('enrollment'):
        data_hook = (
            f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}). "
            f"Our district serves {user_info['enrollment']} students, "
            f"{user_info['poverty']}% of whom are economically disadvantaged. "
            f"These students rely on stable public funding, not privatization schemes.\n\n"
        )
    else:
        # Fallback if CSV is missing stats
        data_hook = f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}).\n\n"

    # --- MODE 1: EMAIL DEFENDERS (ALLIES) ---
    if mode == "Ally":
        subject = f"Thank You for Standing with {user_info['district']}"
        body = (
            f"Dear Legislator,\n\n"
            f"{data_hook}" # <--- INSERTING STATS HERE
            f"I am writing to thank you for your continued defense of Ohio's public schools. "
            f"In a time when our districts are facing budget freezes and voucher expansion pressures, "
            f"your vote matters deeply to our specific community.\n\n"
            f"Please continue to fight for us. We are organizing locally to ensure that representatives "
            f"who support public education return to Columbus. We have your back.\n\n"
            f"Sincerely,\n{user_info['name']}\nPublic Education Advocate"
        )
        return subject, body

    # --- MODE 2: EMAIL OPPONENTS (HOSTILE) ---
    if mode == "Hostile":
        subject = f"URGENT: Stop Undermining {user_info['district']}"
        body = (
            f"Dear Legislator,\n\n"
            f"{data_hook}" # <--- INSERTING STATS HERE
            f"I am writing to express my strong opposition to budget decisions that harm our specific students. "
            f"By freezing 'base cost' inputs at 2022 levels while expanding universal EdChoice vouchers, "
            f"you are actively dismantling the resources our students need.\n\n"
            f"We are watching the voting records closely. I urge you to freeze new voucher appropriations "
            f"and vote to update the Fair School Funding Plan inputs immediately.\n\n"
            f"Sincerely,\n{user_info['name']}\nConcerned Voter"
        )
        return subject, body

    # --- MODE 3: SINGLE DISTRICT REP ---
    # Standard logic, but now using the passed user_info stats
    if target_rep.get('rep_stance') == "Hostile":
        subject = f"URGENT: Financial Distress in {user_info['district']}"
        body = (
            f"Dear {target_rep['rep_role']} {target_rep['rep_name']},\n\n"
            f"{data_hook}"
            f"The decision to freeze public school funding at 2022 levels while expanding "
            f"EdChoice vouchers is draining our classrooms.\n\n"
        )
        if target_rep.get('rep_career') == "Re-election":
            body += "We are organizing locally. We need you to support public schools now."
        else:
            body += "Please consider your legacy. Do not be the leader who dismantled Ohio's public education."
    else:
        subject = f"Support Needed: {user_info['district']}"
        body = (
            f"Dear {target_rep['rep_role']} {target_rep['rep_name']},\n\n"
            f"{data_hook}"
            f"Thank you for your support. Please keep fighting to update the Fair School Funding Plan inputs."
        )

    full_text = f"{body}\n\nSincerely,\n{user_info['name']}\n{user_info['district']} Resident"
    return subject, full_text

def create_pdf(rep, user_name, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    
    if isinstance(rep, dict) and 'rep_name' in rep: # Single Rep
        pdf.cell(0, 5, txt=f"Constituent of {rep.get('school_district', 'Ohio')}", ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
        pdf.set_font("Arial", size=11)
        safe_address = str(rep.get('rep_address', 'Ohio Statehouse'))
        pdf.cell(0, 5, txt=safe_address, ln=1)
    else: # Statewide
        pdf.cell(0, 5, txt="To: Members of the Ohio General Assembly", ln=1)
        
    pdf.ln(10)
    pdf.multi_cell(0, 6, txt=content)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

col1, col2 = st.columns([3, 1])
with col1:
    st.title("📢 Ohio Legislator Communicator")
with col2:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Seal_of_Ohio.svg/100px-Seal_of_Ohio.svg.png", width=80)

if df.empty:
    st.error("⚠️ System Error: CSV not found.")
    st.stop()

# --- SIDEBAR: GLOBAL INPUTS ---
# We move these to the top so we ALWAYS know the user's district stats
with st.sidebar:
    st.header("1. Your Context")
    zip_code = st.text_input("Your Zip Code", max_chars=5, placeholder="45011")
    user_name = st.text_input("Your Name", "Concerned Citizen")
    
    # Try to find user's district data immediately
    user_data = get_rep_from_zip(zip_code)
    
    # Store this for later use
    user_context = {
        "name": user_name,
        "zip": zip_code,
        "district": user_data['school_district'] if user_data else "Ohio Public Schools",
        "enrollment": str(user_data['enrollment']) if user_data else "",
        "poverty": str(user_data['poverty_rate']).replace("%","") if user_data else ""
    }

    st.markdown("---")
    st.header("2. Select Action")
    mode = st.radio("Choose Mode:", [
        "📍 Find My Rep", 
        "🛡️ Email Defenders", 
        "🚫 Email Opponents"
    ])

# --- MAIN DISPLAY ---

# If we don't have a valid zip yet, show the "Waiting" screen
if not user_data:
    st.info("👈 Please enter your **Zip Code** in the sidebar to load your district's statistics.")
    st.stop()

# Show the User's Context (The "Power Card")
st.success(f"📍 **Context Loaded:** {user_context['district']}")
if user_context['enrollment']:
    c1, c2 = st.columns(2)
    c1.metric("Your Students", user_context['enrollment'])
    c2.metric("Econ. Disadvantaged", user_context['poverty'] + "%")
st.markdown("---")

# --- MODE 1: FIND MY REP ---
if mode == "📍 Find My Rep":
    st.subheader(f"Representative for {user_context['district']}")
    
    # Rep Card
    with st.container():
        st.markdown(f"### Rep. {user_data['rep_name']}")
        if user_data.get('rep_stance') == "Hostile":
            st.error(f"❌ Record: Voted for Cuts")
        else:
            st.success(f"✅ Record: Education Ally")
            
        subject, body = generate_message(user_data, user_context, mode="District")
        
        # Buttons
        safe_sub = urllib.parse.quote(subject)
        safe_body = urllib.parse.quote(body)
        mailto = f"mailto:{user_data['rep_email']}?subject={safe_sub}&body={safe_body}"
        
        c1, c2 = st.columns(2)
        with c1:
                st.markdown(f'<a href="{mailto}" target="_blank"><button style="width:100%; padding:10px; background:#FF4B4B; color:white; border:none; border-radius:5px;">✉️ Email Rep</button></a>', unsafe_allow_html=True)
        with c2:
            pdf_bytes = create_pdf(user_data, user_name, body)
            b64 = base64.b64encode(pdf_bytes).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Letter.pdf"><button style="width:100%; padding:10px; background:#F0F2F6; border:1px solid #ccc; border-radius:5px;">📄 PDF Letter</button></a>', unsafe_allow_html=True)
            
        with st.expander("Preview"):
            st.text_area("msg", body, height=200, label_visibility="collapsed")

# --- MODE 2 & 3: MASS EMAIL ---
else:
    if mode == "🛡️ Email Defenders":
        target_stance = "Friendly"
        header_title = "🛡️ Rally the Defenders"
        msg_mode = "Ally"
    else:
        target_stance = "Hostile"
        header_title = "🚫 Pressure the Opponents"
        msg_mode = "Hostile"

    st.subheader(header_title)
    
    # Filter Emails
    target_emails = df[df['rep_stance'] == target_stance]['rep_email'].unique().tolist()
    target_emails = [x for x in target_emails if str(x) != "nan" and str(x) != ""]
    email_string = ", ".join(target_emails)
    
    st.write(f"**Found {len(target_emails)} Representatives.**")
    
    # Generate Message (NOW INCLUDES USER STATS!)
    subject, body = generate_message({}, user_context, mode=msg_mode)
    
    # Display Tools
    st.markdown("### Step 1: Copy Email List")
    st.caption("Paste into **BCC** line.")
    st.text_area("Recipients", value=email_string, height=100)
    
    st.markdown("### Step 2: Copy Message")
    st.text_input("Subject", value=subject)
    st.text_area("Body", value=body, height=250)
    
    # Mailto
    safe_sub = urllib.parse.quote(subject)
    safe_body = urllib.parse.quote(body)
    mailto_all = f"mailto:?bcc={email_string}&subject={safe_sub}&body={safe_body}"
    
    st.markdown("---")
    st.markdown(f"""
    <a href="{mailto_all}" target="_blank">
        <button style="width:100%; padding:15px; background-color:#FF4B4B; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">
            🚀 Auto-Open Email (BCC)
        </button>
    </a>
    """, unsafe_allow_html=True)
