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

# --- 3. DATA LOADER & UTILS ---
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
        body = (f"Dear Legislator,\n\n{student_hook}\n\nThank you for defending public schools and our students.\n\nSincerely,\n{user_info['name']}")
    elif mode == "Hostile":
        subject = f"URGENT: Stop Undermining {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\nI oppose freezing public school funding while expanding vouchers. Please support our local schools.\n\nSincerely,\n{user_info['name']}")
    else:
        subject = f"Support Needed: {user_info['district']}"
        body = (f"Dear {target_rep.get('rep_role','Rep')} {target_rep.get('rep_name','')},\n\n{student_hook}\n\nPlease prioritize public school funding over private voucher expansion.\n\nSincerely,\n{user_info['name']}")
    return subject, body

# --- 5. APP INTERFACE ---

# HEADER SECTION
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("<h1 style='color:#B22234;'>⚖️ CLASS ACTION</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#3C3B6E;'>Don't just watch. Take action.</h4>", unsafe_allow_html=True)
with col2:
    logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
    st.image(logo_url, width=100)

if df.empty:
    st.error("⚠️ Error: ohio_districts.csv missing from repository.")
    st.stop()

# MAIN INPUTS
st.markdown("---")
st.header("1. Identify Your District")
c1, c2 = st.columns(2)
with c1:
    zip_code = st.text_input("Enter Your Zip Code", max_chars=5, placeholder="45011")
with c2:
    user_name = st.text_input("Enter Your Name", "Concerned Citizen")

user_data = get_rep_from_zip(zip_code)

# SIDEBAR (Faculty Lounge Display)
with st.sidebar:
    st.header("📋 Faculty Lounge")
    st.info(f"Rank: **{st.session_state.badge_level}**")
    st.write(f"XP Gained: **{st.session_state.xp_points}**")
    st.progress(min(st.session_state.xp_points / 300, 1.0))
    
    st.markdown("---")
    if st.session_state.xp_points > 0:
        st.write("💾 **Save Your Rank**")
        if st.button("🔖 Bookmark Progress"):
            st.toast("📌 Press Ctrl+D (or Cmd+D) now to bookmark this page and save your rank!", icon="💾")

# --- 6. ACTION SECTION ---
if not zip_code:
    st.info("👆 Enter your Zip Code above to find your representatives and begin your mission.")
    st.stop()

user_context = {
    "name": user_name, "zip": zip_code,
    "district": user_data['school_district'] if user_data else "Ohio Public Schools",
    "enrollment": str(user_data.get('enrollment','')) if user_data else ""
}

st.success(f"📍 District Loaded: **{user_context['district']}**")

st.header("2. Take Action")
mode = st.radio("Select Your Advocacy Task:", ["📍 Find My Rep", "🛡️ Email Defenders", "🚫 Email Opponents", "🏛️ Email Governor"], horizontal=True)

target_emails = []
if mode == "📍 Find My Rep":
    target_emails = [user_data['rep_email']] if user_data else []
    subject, body = generate_message(user_data, user_context, mode="District")
elif mode == "🛡️ Email Defenders":
    target_emails = df[df['rep_stance'] == "Friendly"]['rep_email'].unique().tolist()
    subject, body = generate_message({}, user_context, mode="Ally")
elif mode == "🚫 Email Opponents":
    target_emails = df[df['rep_stance'] == "Hostile"]['rep_email'].unique().tolist()
    subject, body = generate_message({}, user_context, mode="Hostile")
else:
    target_emails = ["governor@ohio.gov"]
    subject, body = generate_message({}, user_context, mode="Leadership")

# Advocacy Email Launch Button
email_string = ",".join([str(e) for e in target_emails if str(e) != "nan" and str(e) != ""])
safe_sub = urllib.parse.quote(subject)
safe_body = urllib.parse.quote(body)
mailto_link = f"mailto:?bcc={email_string}&subject={safe_sub}&body={safe_body}"

st.markdown(f'<a href="{mailto_link}" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;font-size:1.2em;">STEP 1: OPEN EMAIL CLIENT ✉️</div></a>', unsafe_allow_html=True)

st.write("")
if st.button("STEP 2: ✅ I SENT IT! (+100 XP)"):
    st.session_state.xp_points += 100
    update_status()
    st.balloons()
    st.rerun()

# --- 7. SOCIAL & PERSONAL SHARING ---
st.markdown("---")
st.header("3. Spread the Word")
st.write(f"Current Rank: **{st.session_state.badge_level}**")

share_url = "https://ohio-advocate.streamlit.app"
share_text = f"I just reached the rank of {st.session_state.badge_level} on Class Action! Join me in standing up for Ohio's public schools: {share_url}"
encoded_share = urllib.parse.quote(share_text)

# ROW 1: Social Media
st.write("📢 **Social Media**")
s1, s2, s3 = st.columns(3)
with s1:
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={share_url}"
    st.markdown(f'<a href="{fb_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#1877F2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Facebook</div></a>', unsafe_allow_html=True)
with s2:
    tw_url = f"https://twitter.com/intent/tweet?text={encoded_share}"
    st.markdown(f'<a href="{tw_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Twitter (X)</div></a>', unsafe_allow_html=True)
with s3:
    li_url = f"https://www.linkedin.com/sharing/share-offsite/?url={share_url}"
    st.markdown(f'<a href="{li_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#0A66C2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">LinkedIn</div></a>', unsafe_allow_html=True)

# ROW 2: Personal (SMS & Email)
st.write("📲 **Direct Messages**")
p1, p2 = st.columns(2)
with p1:
    sms_url = f"sms:?&body={encoded_share}"
    st.markdown(f'<a href="{sms_url}" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Text Friend (SMS)</div></a>', unsafe_allow_html=True)
with p2:
    share_email_sub = urllib.parse.quote("Check out Class Action Ohio")
    share_email_body = urllib.parse.quote(f"Hey! I'm using this tool called Class Action to defend Ohio's public schools. I'm currently at the rank of {st.session_state.badge_level}. Try it out: {share_url}")
    email_share_url = f"mailto:?subject={share_email_sub}&body={share_email_body}"
    st.markdown(f'<a href="{email_share_url}" style="text-decoration:none;"><div style="background-color:#D44638;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Email Friend</div></a>', unsafe_allow_html=True)

# ROW 3: Visual Platforms
st.write("📱 **Instagram & TikTok**")
st.code(share_text, language=None)
st.caption("Copy the text above for your Story or Caption!")

if st.button("✅ I Shared This App! (+100 XP)"):
    st.session_state.xp_points += 100
    update_status()
    st.success("Rank XP updated!")
    st.rerun()
