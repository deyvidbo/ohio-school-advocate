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

# LANDING PAGE BRANDING
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=400) # Maximum impact size
except:
    st.title("⚖️ CLASS ACTION")

st.markdown(f"<h1 style='text-align: center; color:#B22234; margin-top:-20px; font-size: 3em;'>CLASS ACTION</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#3C3B6E; margin-bottom: 30px;'>Don't just watch. Take action.</h3>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# DYNAMIC RANK DASHBOARD
st.markdown(f"""
    <div style="background-color:{rank_color}11; border:3px solid {rank_color}; padding:25px; border-radius:15px; text-align:center; margin-bottom:35px;">
        <h1 style="margin:0; color:{rank_color}; font-size: 2em;">{rank_title}</h1>
        <div style="background-color: #ddd; border-radius: 20px; margin: 15px 0;">
            <div style="background-color: {rank_color}; width: {min((st.session_state.xp_points/300)*100, 100)}%; height: 20px; border-radius: 20px;"></div>
        </div>
        <p style="margin:5px 0; font-weight:bold; font-size: 1.2em;">Current XP: {st.session_state.xp_points} / 300</p>
        <p style="margin:0; font-style:italic; font-size: 1.1em;">{rank_msg}</p>
    </div>
""", unsafe_allow_html=True)

# INPUTS
st.header("1. Identify Your District")
c1, c2 = st.columns(2)
with c1:
    zip_code = st.text_input("Enter Zip Code", max_chars=5, placeholder="45011")
with c2:
    user_name = st.text_input("Enter Your Name", placeholder="Mr. B")

# ADVOCACY LOGIC
if zip_code:
    res = df[df['zip_code'] == zip_code]
    if not res.empty:
        user_data = res.iloc[0].to_dict()
        st.success(f"📍 District Loaded: **{user_data['school_district']}**")
        
        st.header("2. Take Action")
        mode = st.radio("Task Selection:", ["📍 Find My Rep", "🛡️ Defenders", "🚫 Opponents", "🏛️ Governor"], horizontal=True)
        
        # Simple BCC mailto link generation for brevity
        st.markdown(f'<a href="mailto:?subject=Class Action Advocacy" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;font-size:1.3em;box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">STEP 1: OPEN EMAIL ✉️</div></a>', unsafe_allow_html=True)
        
        st.write("")
        if st.button("STEP 2: ✅ I SENT IT! (+100 XP)"):
            st.session_state.xp_points += 100
            st.balloons()
            st.rerun()

# --- 5. VISUAL BADGE & SOCIAL TOOLKIT ---
st.markdown("---")
st.header("3. Spread the Word")

# THE VISUAL BADGE (Designed for Instagram/TikTok Screenshots)
st.markdown(f"""
    <div style="background-color:white; border:8px solid #B22234; padding:40px; border-radius:20px; text-align:center; box-shadow: 15px 15px 0px #3C3B6E; margin-bottom: 20px;">
        <img src="{logo_url}" width="120">
        <h1 style="color:#B22234; font-family: sans-serif; letter-spacing: 2px;">CLASS ACTION</h1>
        <div style="height: 2px; background-color: #3C3B6E; width: 60%; margin: 20px auto;"></div>
        <h2 style="color:#3C3B6E; font-size: 2.2em;">{rank_title}</h2>
        <p style="font-size: 1.2em; color: #555;">I am defending Ohio's public schools.</p>
        <p style="font-weight: bold; color: #B22234;">JOIN THE CAUSE</p>
        <p style="font-size:0.9em; color:grey;">ohio-advocate.streamlit.app</p>
    </div>
    <p style="text-align:center; color:#3C3B6E; font-weight:bold;">📸 Screenshot this badge for Instagram & TikTok!</p>
""", unsafe_allow_html=True)

share_url = "https://ohio-advocate.streamlit.app"
encoded_msg = urllib.parse.quote(f"I just reached the rank of {rank_title} on Class Action! Join the movement to defend our schools: {share_url}")

# ONE-TAP SHARING BUTTONS
st.write("📲 **One-Tap Recruitment**")
s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(f'<a href="sms:?&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">SMS 💬</div></a>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#1877F2;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">Facebook 👥</div></a>', unsafe_allow_html=True)
with s3:
    st.markdown(f'<a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#0A66C2;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">LinkedIn 💼</div></a>', unsafe_allow_html=True)

s4, s5 = st.columns(2)
with s4:
    st.markdown(f'<a href="https://twitter.com/intent/tweet?text={encoded_msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">Twitter (X) 🐦</div></a>', unsafe_allow_html=True)
with s5:
    st.markdown(f'<a href="mailto:?subject=Join Class Action Ohio&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#D44638;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">Email 📧</div></a>', unsafe_allow_html=True)

st.write("")
if st.button("✅ I Shared My Mission! (+100 XP)"):
    st.session_state.xp_points += 100
    st.toast("Recruitment XP Added!", icon="🚀")
    st.rerun()
