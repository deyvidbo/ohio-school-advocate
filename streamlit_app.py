import streamlit as st
import pandas as pd
import urllib.parse

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE & RANKING ---
params = st.query_params
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = int(params.get("xp", 0))

def get_rank_info(xp):
    if xp >= 300:
        return "🎓 The Superintendent", "👑 YOU RUN THIS TOWN.", "#FFD700"
    elif xp >= 200:
        return "🍎 Tenured Teacher", "🔥 You are a pro. Recruit a friend.", "#4CAF50"
    elif xp >= 100:
        return "🎒 The Student", "📚 Good work. Keep going.", "#2196F3"
    return "📝 The Substitute", "👉 Send your first email to get certified!", "#757575"

rank_title, rank_msg, rank_color = get_rank_info(st.session_state.xp_points)
st.query_params["xp"] = str(st.session_state.xp_points)

# --- 3. DATA LOADER ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        df.fillna("", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. APP INTERFACE ---

# LARGE LOGO AND BRANDING
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=350) # Increased from 100 to 350 for impact
except:
    st.title("⚖️ CLASS ACTION")
st.markdown(f"<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>CLASS ACTION</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#3C3B6E;'>Don't just watch. Take action.</h3>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# MISSION DASHBOARD
st.markdown(f"""
    <div style="background-color:{rank_color}22; border:2px solid {rank_color}; padding:20px; border-radius:15px; text-align:center; margin-bottom:25px;">
        <h2 style="margin:0; color:{rank_color};">{rank_title}</h2>
        <p style="margin:5px 0; font-weight:bold;">Current XP: {st.session_state.xp_points}</p>
        <p style="margin:0; font-style:italic;">{rank_msg}</p>
    </div>
""", unsafe_allow_html=True)

# INPUTS
st.header("1. Identify Your District")
c1, c2 = st.columns(2)
with c1:
    zip_code = st.text_input("Enter Zip Code", max_chars=5)
with c2:
    user_name = st.text_input("Enter Your Name", "Concerned Citizen")

# LOGIC
if zip_code:
    res = df[df['zip_code'] == zip_code]
    if not res.empty:
        user_data = res.iloc[0].to_dict()
        st.success(f"📍 District Loaded: **{user_data['school_district']}**")
        
        st.header("2. Take Action")
        mode = st.radio("Task:", ["📍 Find My Rep", "🛡️ Defenders", "🚫 Opponents", "🏛️ Governor"], horizontal=True)
        
        # (Email logic here - assuming standard mailto generation)
        # For brevity, using a generic mailto for Step 1
        st.markdown(f'<a href="mailto:?subject=Class Action" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;">STEP 1: OPEN EMAIL ✉️</div></a>', unsafe_allow_html=True)
        
        if st.button("STEP 2: ✅ I SENT IT! (+100 XP)"):
            st.session_state.xp_points += 100
            st.rerun()

# --- 5. SOCIAL RECRUITMENT TOOLKIT ---
st.markdown("---")
st.header("3. Share Your Rank")

# THE VISUAL BADGE (For Screenshots)
st.markdown(f"""
    <div style="background-color:white; border:5px solid #B22234; padding:30px; border-radius:15px; text-align:center; box-shadow: 10px 10px 5px #eeeeee;">
        <img src="{logo_url}" width="80">
        <h1 style="color:#B22234;">CLASS ACTION</h1>
        <hr>
        <h2 style="color:#3C3B6E;">{rank_title}</h2>
        <p>I am defending Ohio's public schools!</p>
        <p style="font-size:0.8em; color:grey;">Join the cause: ohio-advocate.streamlit.app</p>
    </div>
    <p style="text-align:center; color:grey; font-size:0.9em;">📸 Screenshot this badge for <b>Instagram & TikTok</b>!</p>
""", unsafe_allow_html=True)

share_url = "https://ohio-advocate.streamlit.app"
encoded_msg = urllib.parse.quote(f"I just reached the rank of {rank_title} on Class Action! Join the movement: {share_url}")

# BUTTONS
st.write("📲 **One-Tap Share**")
s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(f'<a href="sms:?&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">SMS</div></a>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#1877F2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Facebook</div></a>', unsafe_allow_html=True)
with s3:
    st.markdown(f'<a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#0A66C2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">LinkedIn</div></a>', unsafe_allow_html=True)

s4, s5 = st.columns(2)
with s4:
    st.markdown(f'<a href="https://twitter.com/intent/tweet?text={encoded_msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Twitter (X)</div></a>', unsafe_allow_html=True)
with s5:
    st.markdown(f'<a href="mailto:?subject=Join Class Action&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#D44638;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">Email</div></a>', unsafe_allow_html=True)

if st.button("✅ I Shared This! (+100 XP)"):
    st.session_state.xp_points += 100
    st.rerun()
