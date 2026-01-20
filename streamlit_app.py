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

def generate_message(rep, user_name, user_district, mode="District"):
    """Generates text. Mode can be 'District' or 'Statewide'."""
    
    if mode == "Statewide":
        subject = "URGENT: Statewide Call to Fund Public Schools"
        body = (
            f"Dear Ohio Legislators,\n\n"
            f"I am an Ohio voter and education advocate writing to demand immediate action on the "
            f"Fair School Funding Plan. The decision to freeze 'base cost' inputs at outdated 2022 levels "
            f"is a functional budget cut for districts across the state.\n\n"
            f"Simultaneously, the uncapped expansion of EdChoice vouchers is draining the general fund. "
            f"I urge you to freeze voucher expansion and update the public school funding formula to reflect "
            f"current inflation and economic realities.\n\n"
            f"Ohio's students deserve a constitutional system of funding.\n\n"
            f"Sincerely,\n{user_name}\nOhio Resident"
        )
        return subject, body

    # DISTRICT SPECIFIC LOGIC
    if rep.get('rep_stance') == "Hostile":
        subject = f"URGENT: Financial Distress in {user_district}"
        body = (
            f"Dear {rep['rep_role']} {rep['rep_name']},\n\n"
            f"I am a voter in {user_district} (Zip: {rep['zip_code']}). "
        )
        
        # Data Hook
        if str(rep.get('enrollment')) != "":
            body += (
                f"Our district serves {rep['enrollment']} students, "
                f"{rep['poverty_rate']} of whom are economically disadvantaged. "
            )
            
        body += (
            "The decision to freeze public school funding at 2022 levels while expanding "
            "EdChoice vouchers is draining our classrooms.\n\n"
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
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 5, txt=f"From: {user_name}", ln=1)
    if isinstance(rep, dict): # Single Rep
        pdf.cell(0, 5, txt=f"Constituent of {rep['school_district']}", ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 5, txt=f"To: {rep['rep_role']} {rep['rep_name']}", ln=1)
        pdf.set_font("Arial", size=11)
        safe_address = str(rep.get('rep_address', 'Ohio Statehouse'))
        pdf.cell(0, 5, txt=safe_address, ln=1)
    else: # Statewide
        pdf.cell(0, 5, txt="To: The Ohio General Assembly", ln=1)
        
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

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Choose Mode:", ["📍 My District", "📢 Email ALL Reps"])
    st.markdown("---")
    user_name = st.text_input("Your Name", "Concerned Citizen")

# --- MODE 1: MY DISTRICT ---
if mode == "📍 My District":
    st.subheader("Find Your Representative")
    zip_code = st.text_input("Enter Zip Code", max_chars=5, placeholder="45011")
    
    rep_match = get_rep_from_zip(zip_code)
    st.markdown("---")

    if rep_match:
        # District Stats
        st.caption(f"📍 District: {rep_match['school_district']}")
        if str(rep_match.get('enrollment')) != "":
            c1, c2, c3 = st.columns(3)
            c1.metric("Students", rep_match['enrollment'])
            c2.metric("Poverty", rep_match['poverty_rate'])
            c3.metric("Minority", rep_match['minority_rate'])
        
        # Rep Card
        with st.container():
            st.markdown(f"### Rep. {rep_match['rep_name']}")
            if rep_match.get('rep_stance') == "Hostile":
                st.error(f"❌ Record: Voted for Cuts")
            else:
                st.success(f"✅ Record: Education Ally")
                
            subject, body = generate_message(rep_match, user_name, rep_match['school_district'])
            
            # Buttons
            safe_sub = urllib.parse.quote(subject)
            safe_body = urllib.parse.quote(body)
            mailto = f"mailto:{rep_match['rep_email']}?subject={safe_sub}&body={safe_body}"
            
            c1, c2 = st.columns(2)
            with c1:
                 st.markdown(f'<a href="{mailto}" target="_blank"><button style="width:100%; padding:10px; background:#FF4B4B; color:white; border:none; border-radius:5px;">✉️ Email Rep</button></a>', unsafe_allow_html=True)
            with c2:
                pdf_bytes = create_pdf(rep_match, user_name, body)
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Letter.pdf"><button style="width:100%; padding:10px; background:#F0F2F6; border:1px solid #ccc; border-radius:5px;">📄 PDF Letter</button></a>', unsafe_allow_html=True)
                
            with st.expander("Preview"):
                st.text_area("msg", body, height=200, label_visibility="collapsed")
                
    elif zip_code:
        st.warning("Zip not found yet.")

# --- MODE 2: EMAIL ALL ---
else:
    st.subheader("📢 Statewide Advocacy")
    st.info("This tool targets every legislator currently in our database.")
    
    # 1. Gather all emails
    all_emails = df['rep_email'].unique().tolist()
    # Filter out any accidental empty ones
    all_emails = [x for x in all_emails if str(x) != "nan" and str(x) != ""]
    
    email_string = ", ".join(all_emails)
    count = len(all_emails)
    
    st.write(f"**Found {count} Unique Representatives.**")
    
    # 2. Generate Generic Message
    subject, body = generate_message({}, user_name, "Ohio", mode="Statewide")
    
    # 3. DISPLAY COPY/PASTE TOOLS
    st.markdown("### Step 1: Copy Email List")
    st.caption("Copy these addresses and paste them into the **BCC** field of your email.")
    st.text_area("Recipient List (BCC)", value=email_string, height=100)
    
    st.markdown("### Step 2: Copy Message")
    st.text_input("Subject Line", value=subject)
    st.text_area("Email Body", value=body, height=250)
    
    # 4. OPTIONAL: MASS MAILTO LINK (May not work if list is huge)
    # We try to put them in BCC to avoid spamming the 'To' field
    safe_sub = urllib.parse.quote(subject)
    safe_body = urllib.parse.quote(body)
    # Note: Browsers truncate generic mailto links > 2000 chars. 
    # The copy/paste method above is safer, but we provide this for smaller lists.
    mailto_all = f"mailto:?bcc={email_string}&subject={safe_sub}&body={safe_body}"
    
    st.markdown("---")
    st.markdown(f"""
    <a href="{mailto_all}" target="_blank">
        <button style="width:100%; padding:15px; background-color:#FF4B4B; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">
            🚀 Try Auto-Open Email App (BCC All)
        </button>
    </a>
    """, unsafe_allow_html=True)
    st.caption("*Note: If the button doesn't work (due to too many recipients), use the Copy/Paste boxes above.*")
