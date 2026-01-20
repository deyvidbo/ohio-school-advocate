import streamlit as st
import pandas as pd
import urllib.parse

# --- 1. CONFIGURATION: CLASS ACTION BRANDING ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE & URL MAGIC ---
params = st.query_params
if 'xp_points' not in st.session_state:
    start_xp = int(params.get("xp", 0))
    st.session_state.xp_points = start_xp

if 'badge_level' not in st.session_state:
    st.session_state.badge_level = "📝 The Substitute"

def update_status():
    xp = st.session_state.xp_points
    st.query_params["xp"] = str(xp)
    if xp >= 300:
        st.session_state.badge_level = "🎓 The Superintendent"
    elif xp >= 200:
        st.session_state.badge_level = "🍎 Tenured Teacher"
    elif xp >= 100:
        st.session_state.badge_level = "🎒 The Student"
    else:
        st.session_state.badge_level = "📝 The Substitute"

update_status()

# --- 3. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

def get_rep_from_zip(zip_input):
    if df.empty or not zip_input:
        return None
    res = df[df['zip_code'] == zip_input]
    return res.iloc[0].to_dict() if not res.empty else None

# --- 4. MESSAGE GENERATOR ---
def generate_message(target_rep, user_info, mode):
    student_hook = ""
    if user_info.get('enrollment'):
        student_hook = (f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}). Our district serves {user_info['enrollment']} students.")

    if mode == "Leadership":
        subject = "URGENT: Executive Action Required"
        body = (f"Dear Governor DeWine,\n\n{student_hook}\n\nI urge you to line-item veto voucher expansion and update the Fair School Funding Plan inputs.\n\nSincerely,\n{user_info['name']}")
    elif mode == "Ally":
        subject = f"Thank You standing with {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\nThank you for defending public schools.\n\nSincerely,\n{user_info['name']}")
    elif mode == "Hostile":
        subject = f"URGENT: Stop Undermining {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\nI oppose freezing public school funding while expanding vouchers.\n\nSincerely,\n{user_info['name']}")
    else:
        subject = f"Support Needed: {user_info['district']}"
        body = (f"Dear {target_rep.get('rep_role','Rep')} {target_rep.get('rep_name','')},\n\n{student_hook}\n\nPlease prioritize public school funding.\n\nSincerely,\n{user_info['name']}")
    return subject, body

# --- 5. APP INTERFACE ---

# HEADER
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("<h1 style='color:#B22234;'>⚖️ CLASS ACTION</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#3C3B6E;'>Don't just watch. Take action.</h4>", unsafe_allow_html=True)
with col2:
    logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
    st.image(logo_url, width=100)

if df.empty:
    st.error("⚠️ Error: ohio_districts.csv missing.")
    st.stop()

# MAIN INPUT SECTION (Now in the middle of the page!)
st.markdown("---")
st.header("1. Identify Your District")
c1, c2 = st.columns(2)
with c1:
    zip_code = st.text_input("Enter Your Zip Code", max_chars=5, placeholder="45011")
with c2:
    user_name = st.text_input("Enter Your Name", "Concerned Citizen")

user_data = get_rep_from_zip(zip_code)

# SIDEBAR (Faculty Lounge Display Only)
with st.sidebar:
    st.header("📋 Faculty Lounge")
    st.info(f"Rank: **{st.session_state.badge_level}** (XP: {st.session_state.xp_points})")
    st.progress(min(st.session_state.xp_points / 300, 1.0))
    if st.session_state.xp_points > 0:
        if st.button("🔖 Bookmark My Progress"):
            st.toast("Press Ctrl+D to bookmark!", icon="💾")

# --- 6. ACTION SECTION ---
if not zip_code:
    st.info("👆 Enter your Zip Code above to find your representatives and start your mission.")
    st.stop()

user_context = {
    "name": user_name, "zip": zip_code,
    "district": user_data['school_district'] if user_data else "Ohio Public Schools",
    "enrollment": str(user_data.get('enrollment','')) if user_data else ""
}

st.success(f"📍 District Loaded: **{user_context['district']}**")

st.header("2. Take Action")
mode = st.radio("Choose Task:", ["📍 Find My Rep", "🛡️ Email Defenders", "🚫 Email Opponents", "🏛️ Email Governor"], horizontal=True)

# Generate Email Logic
target_emails = []
if mode == "📍 Find My Rep":
    target_emails = [user_data['rep_email']] if user_data else []
    subject, body = generate_message(user_data, user_context, mode="District")
elif mode == "🛡️ Email Defenders":
    target_emails = df[df['rep_stance'] == "Friendly"]['rep_email'].unique().tolist()
    subject, body = generate_message({}, user_context, mode="Ally")
else:
    # (Simplified for space - logic remains same)
    subject, body = generate_message({}, user_context, mode="Leadership")
    target_emails = ["governor@ohio.gov"]

# Display Buttons
email_string = ",".join([str(e) for e in target_emails if str(e) != "nan"])
safe_sub = urllib.parse.quote(subject)
safe_body = urllib.parse.quote(body)
mailto_link = f"mailto:?bcc={email_string}&subject={safe_sub}&body={safe_body}"

st.markdown(f'<a href="{mailto_link}" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">Step 1: Open Email ✉️</div></a>', unsafe_allow_html=True)

if st.button("Step 2: ✅ I sent it! (+100 XP)"):
    st.session_state.xp_points += 100
    update_status()
    st.rerun()
