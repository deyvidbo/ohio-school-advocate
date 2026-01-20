import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse
import time

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Ohio Ed Shield",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.legislature.ohio.gov/',
        'About': "Built by an Ohio educator to defend public schools."
    }
)

# --- SESSION STATE (The Game Engine) ---
# This remembers the user's progress ONLY while the tab is open.
if 'actions_taken' not in st.session_state:
    st.session_state.actions_taken = 0
if 'badge_level' not in st.session_state:
    st.session_state.badge_level = "🛡️ The Observer"
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0

# --- GAMIFICATION LOGIC ---
def update_status():
    # Simple logic: Every action is worth 100 XP
    xp = st.session_state.xp_points
    
    if xp >= 300:
        st.session_state.badge_level = "🏆 Ohio Champion"
    elif xp >= 200:
        st.session_state.badge_level = "📣 The Amplifier"
    elif xp >= 100:
        st.session_state.badge_level = "📨 The Messenger"
    else:
        st.session_state.badge_level = "🛡️ The Observer"

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

# --- 2. MESSAGE GENERATOR ---
def generate_message(target_rep, user_info, mode):
    # Student Data Hook
    student_hook = ""
    if user_info.get('enrollment'):
        student_hook = (
            f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}). "
            f"Our district serves {user_info['enrollment']} students, "
            f"{user_info['poverty']}% of whom are economically disadvantaged. "
        )
    else:
        student_hook = f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}). "

    # Teacher Data Hook
    teacher_hook = ""
    if user_info.get('teacher_exp') and str(user_info['teacher_exp']) != "":
        teacher_hook = (
            f"Our teaching staff averages {user_info['teacher_exp']} years of experience. "
            f"Despite this expertise, our average teacher salary is only {user_info['teacher_salary']}. "
            f"The state's refusal to update funding inputs disrespects their service.\n\n"
        )
    
    # Message Body Construction
    if mode == "Leadership":
        subject = "URGENT: Executive Action Required for Public Schools"
        body = (f"Dear Governor DeWine and Leadership,\n\n{student_hook}\n\n{teacher_hook}"
                f"I urge you to line-item veto any further voucher expansion and advocate "
                f"for updating the Fair School Funding Plan inputs immediately.\n\n"
                f"Sincerely,\n{user_info['name']}")
                
    elif mode == "Ally":
        subject = f"Thank You for Standing with {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\n{teacher_hook}"
                f"Thank you for defending our public schools. We are organizing locally to support "
                f"representatives who fight for us.\n\nSincerely,\n{user_info['name']}")
                
    elif mode == "Hostile":
        subject = f"URGENT: Stop Undermining {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\n{teacher_hook}"
                f"I strongly oppose freezing public school funding while expanding vouchers. "
                f"I urge you to vote to update the Fair School Funding Plan inputs immediately.\n\n"
                f"Sincerely,\n{user_info['name']}")
                
    else: # District Rep
        subject = f"Support Needed: {user_info['district']}"
        body = (f"Dear {target_rep.get('rep_role','Rep')} {target_rep.get('rep_name','')},\n\n{student_hook}\n\n"
                f"Please prioritize public school funding over private voucher expansion.\n\n"
                f"Sincerely,\n{user_info['name']}")

    return subject, body

def create_pdf(rep, user_name, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, txt=f"From: {user_name}\n\n{content}")
    return pdf.output(dest='S').encode('latin-1')

# --- 3. THE APP INTERFACE ---

# Header Section
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🛡️ The Ohio Ed Shield")
    st.caption("Defend Your District. In Seconds.")
with col2:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Seal_of_Ohio.svg/100px-Seal_of_Ohio.svg.png", width=70)

if df.empty:
    st.error("⚠️ Error: ohio_districts.csv not found.")
    st.stop()

# --- SIDEBAR: THE TROPHY ROOM ---
with st.sidebar:
    st.header("📊 Your Mission Status")
    
    lvl = st.session_state.badge_level
    xp = st.session_state.xp_points
    
    # Visual Badge Logic
    if lvl == "🛡️ The Observer":
        st.info(f"Rank: **{lvl}** (XP: {xp})")
        st.write("👉 *Take your first action to level up!*")
        st.progress(0)
    elif lvl == "📨 The Messenger":
        st.warning(f"Rank: **{lvl}** (XP: {xp})")
        st.write("🚀 *Great start! Try a Mass Email next.*")
        st.progress(33)
    elif lvl == "📣 The Amplifier":
        st.success(f"Rank: **{lvl}** (XP: {xp})")
        st.write("🔥 *You are on fire! Share the tool to reach Top Tier.*")
        st.progress(66)
    elif lvl == "🏆 Ohio Champion":
        st.success(f"Rank: **{lvl}** (XP: {xp})")
        st.write("👑 **LEGENDARY STATUS.**")
        st.progress(100)
        st.balloons()
    
    st.markdown("---")
    
    # Global Inputs
    st.header("1. Your Context")
    zip_code = st.text_input("Your Zip Code", max_chars=5, placeholder="45011")
    user_name = st.text_input("Your Name", "Concerned Citizen")
    
    user_data = get_rep_from_zip(zip_code)
    
    user_context = {
        "name": user_name, "zip": zip_code,
        "district": user_data['school_district'] if user_data else "Ohio Public Schools",
        "enrollment": str(user_data.get('enrollment','')) if user_data else "",
        "poverty": str(user_data.get('poverty_rate','')).replace("%","") if user_data else "",
        "teacher_salary": str(user_data.get('avg_teacher_salary', '')) if user_data else "",
        "teacher_exp": str(user_data.get('avg_teacher_exp', '')) if user_data else "",
        "teacher_masters": str(user_data.get('percent_masters', '')) if user_data else ""
    }

    st.markdown("---")
    st.header("2. Select Action")
    mode = st.radio("Choose Mode:", [
        "📍 Find My Rep", 
        "🛡️ Email Defenders", 
        "🚫 Email Opponents",
        "🏛️ Email Governor"
    ])

# --- MAIN DASHBOARD ---

if not user_data:
    st.info("👈 **Start here:** Enter your Zip Code in the sidebar.")
    st.stop()

st.success(f"📍 **Context Loaded:** {user_context['district']}")

# --- ACTION LOGIC ---

if mode == "📍 Find My Rep":
    st.subheader(f"Contact Rep. {user_data['rep_name']}")
    subject, body = generate_message(user_data, user_context, mode="District")
    
    # Mailto Link
    safe_sub = urllib.parse.quote(subject)
    safe_body = urllib.parse.quote(body)
    mailto = f"mailto:{user_data['rep_email']}?subject={safe_sub}&body={safe_body}"
    
    st.markdown(f"""
    <a href="{mailto}" target="_blank" style="text-decoration:none;">
        <div style="width:100%; padding:15px; background-color:#FF4B4B; color:white; text-align:center; border-radius:8px; font-weight:bold; cursor:pointer;">
        Step 1: Open Email App ✉️
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    if st.button("Step 2: ✅ I sent it! (+100 XP)", key="btn_rep"):
        st.session_state.xp_points += 100
        update_status()
        st.rerun()

else:
    # Mass Email Logic
    header = "Advocacy Action"
    msg_mode = "Leadership"
    
    if mode == "🛡️ Email Defenders":
        msg_mode = "Ally"
        header = "🛡️ Rally the Defenders"
        target_emails = df[(df['rep_stance'] == "Friendly") & (df['rep_district'] != "Statewide")]['rep_email'].unique().tolist()
    elif mode == "🚫 Email Opponents":
        msg_mode = "Hostile"
        header = "🚫 Pressure the Opponents"
        target_emails = df[(df['rep_stance'] == "Hostile") & (df['rep_district'] != "Statewide")]['rep_email'].unique().tolist()
    else: # Governor
        msg_mode = "Leadership"
        header = "🏛️ Email Executive Leadership"
        target_emails = df[df['rep_district'] == "Statewide"]['rep_email'].unique().tolist()

    st.subheader(header)
    
    # Filter valid emails
    target_emails = [x for x in target_emails if str(x) != "nan" and str(x) != ""]
    email_string = ", ".join(target_emails)
    
    st.write(f"**Found {len(target_emails)} Recipients.**")
    
    subject, body = generate_message({}, user_context, mode=msg_mode)
    
    # Copy/Paste Tools
    with st.expander("Show Copy/Paste Tools"):
        st.text_area("BCC List", email_string)
        st.text_input("Subject", subject)
        st.text_area("Body", body, height=200)

    # Mailto
    safe_sub = urllib.parse.quote(subject)
    safe_body = urllib.parse.quote(body)
    mailto_all = f"mailto:?bcc={email_string}&subject={safe_sub}&body={safe_body}"
    
    st.markdown(f"""
    <a href="{mailto_all}" target="_blank" style="text-decoration:none;">
        <div style="width:100%; padding:15px; background-color:#FF4B4B; color:white; text-align:center; border-radius:8px; font-weight:bold; cursor:pointer;">
        Step 1: Open Mass Email (BCC) 🚀
        </div>
    </a>
    """, unsafe_allow_html=True)

    if st.button("Step 2: ✅ I sent it! (+100 XP)", key="btn_mass"):
        st.session_state.xp_points += 100
        update_status()
        st.rerun()

# --- RECRUITMENT SECTION (Final Level) ---
st.markdown("---")
st.header("🤝 Recruit More Defenders")

share_text = urllib.parse.quote("I just defended Ohio's public schools using the Ohio Ed Shield. Join me: https://ohio-schools-now.streamlit.app")
twitter_link = f"https://twitter.com/intent/tweet?text={share_text}"

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""<a href="{twitter_link}" target="_blank"><button style="width:100%; padding:10px; background:#1DA1F2; color:white; border:none; border-radius:5px;">🐦 Share on Twitter</button></a>""", unsafe_allow_html=True)
with col2:
    if st.button("✅ I Shared This Tool (+100 XP)"):
        st.session_state.xp_points += 100
        update_status()
        st.rerun()
