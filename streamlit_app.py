import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import urllib.parse

# --- 1. CONFIGURATION: CLASS ACTION BRANDING ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Class Action: Don't just watch. Take action."
    }
)

# --- 2. SESSION STATE & URL MAGIC (The Save System) ---
# Check if they arrived via a "Magic Link" (bookmark)
params = st.query_params

if 'xp_points' not in st.session_state:
    # If URL has xp, load it. Otherwise start at 0.
    start_xp = int(params.get("xp", 0))
    st.session_state.xp_points = start_xp

if 'badge_level' not in st.session_state:
    st.session_state.badge_level = "📝 The Substitute"

# --- 3. GAMIFICATION LOGIC ---
def update_status():
    xp = st.session_state.xp_points
    
    # 1. Update the URL (The Magic Link System)
    # This ensures the URL in the browser always matches their current score
    st.query_params["xp"] = str(xp)

    # 2. Update the Rank
    if xp >= 300:
        st.session_state.badge_level = "🎓 The Superintendent"
    elif xp >= 200:
        st.session_state.badge_level = "🍎 Tenured Teacher"
    elif xp >= 100:
        st.session_state.badge_level = "🎒 The Student"
    else:
        st.session_state.badge_level = "📝 The Substitute"

# Run status check on every load to ensure rank matches XP
update_status()


# --- 4. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        # Ensure ohio_districts.csv is in your GitHub repository
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

# --- 5. MESSAGE GENERATOR ---
def generate_message(target_rep, user_info, mode):
    # (Logic identical to previous versions - keeping concise)
    student_hook = ""
    if user_info.get('enrollment'):
        student_hook = (f"I am a voter in {user_info['district']} (Zip: {user_info['zip']}). Our district serves {user_info['enrollment']} students.")

    subject = "Action Needed for Ohio Schools"
    body = "Error generating message."

    if mode == "Leadership":
        subject = "URGENT: Executive Action Required"
        body = (f"Dear Governor DeWine,\n\n{student_hook}\n\nI urge you to line-item veto voucher expansion and update the Fair School Funding Plan inputs.\n\nSincerely,\n{user_info['name']}")
    elif mode == "Ally":
        subject = f"Thank You standing with {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\nThank you for defending public schools. We have your back.\n\nSincerely,\n{user_info['name']}")
    elif mode == "Hostile":
        subject = f"URGENT: Stop Undermining {user_info['district']}"
        body = (f"Dear Legislator,\n\n{student_hook}\n\nI oppose freezing public school funding while expanding vouchers. Update the funding formula inputs.\n\nSincerely,\n{user_info['name']}")
    else: # District Rep
        subject = f"Support Needed: {user_info['district']}"
        body = (f"Dear {target_rep.get('rep_role','Rep')} {target_rep.get('rep_name','')},\n\n{student_hook}\n\nPlease prioritize public school funding over private voucher expansion.\n\nSincerely,\n{user_info['name']}")

    return subject, body


# --- 6. APP INTERFACE ---

# BRAND HEADER
col1, col2 = st.columns([4, 1])
with col1:
    # Main Title using Brand colors (Red/Blue)
    st.markdown("<h1 style='color:#B22234;'>⚖️ CLASS ACTION</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#3C3B6E;'>Don't just watch. Take action.</h4>", unsafe_allow_html=True)
with col2:
    # --- YOUR LINK IS PASTED HERE ---
    logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
    try:
        st.image(logo_url, width=100)
    except:
        # Fallback if image link is broken
        st.write("⚖️")

if df.empty:
    st.error("⚠️ Error: ohio_districts.csv missing. Please upload it to GitHub.")
    st.stop()

# --- SIDEBAR: THE FACULTY LOUNGE (Save System) ---
with st.sidebar:
    st.header("📋 Faculty Lounge")
    
    lvl = st.session_state.badge_level
    xp = st.session_state.xp_points
    
    # Rank Display
    if lvl == "📝 The Substitute":
        st.info(f"Rank: **{lvl}** (XP: {xp}/100)")
        st.write("👉 *Send your first email to get certified!*")
        st.progress(xp/100 if xp < 100 else 1.0)
    elif lvl == "🎒 The Student":
        st.warning(f"Rank: **{lvl}** (XP: {xp}/200)")
        st.write("📚 *Good work. Send a Mass Email to get Tenure.*")
        st.progress((xp-100)/100 if xp < 200 else 1.0)
    elif lvl == "🍎 Tenured Teacher":
        st.success(f"Rank: **{lvl}** (XP: {xp}/300)")
        st.write("🔥 *You are a pro. Recruit a friend to run the district.*")
        st.progress((xp-200)/100 if xp < 300 else 1.0)
    elif lvl == "🎓 The Superintendent":
        st.success(f"Rank: **{lvl}** (MAX)")
        st.write("👑 **YOU RUN THIS TOWN.**")
        st.balloons()

    # --- THE SAVE BUTTON ---
    st.markdown("---")
    if xp > 0:
        st.write("**Don't lose your rank!**")
        if st.button("🔖 Bookmark My Progress"):
            st.toast("📌 **Action Required!** Press Ctrl+D (or Cmd+D) to bookmark this page right now. Use that bookmark to return with your rank!", icon="💾")
            st.info("Your unique 'save code' is now in your browser's address bar.")
