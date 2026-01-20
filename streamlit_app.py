import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

# Custom CSS for the "War Room" look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .share-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #ddd; }
    .rank-card { background-color: #1e3a8a; color: white; padding: 20px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'u_targets' not in st.session_state: st.session_state.u_targets = []

defaults = {
    'u_name': "David M. Bothast", 'u_role': "K-8 Visual Arts Teacher",
    'is_parent': False, 'child_count': 0, 'is_homeowner': True,
    'is_taxpayer': True, 'is_voter': True, 'years_ohio': 0, 'years_district': 0,
    'custom_note': ""
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str}, quotechar='"')
        df.fillna("N/A", inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. SHARING LOGIC ---
def get_share_links(rank, points):
    site_url = "https://classactionohio.org" # Replace with your actual URL
    text = f"I just reached the rank of {rank} on Class Action Ohio! Join me in defending our public schools: {site_url}"
    encoded_text = urllib.parse.quote(text)
    
    links = {
        "Twitter": f"https://twitter.com/intent/tweet?text={encoded_text}",
        "FB": f"https://www.facebook.com/sharer/sharer.php?u={site_url}",
        "SMS": f"sms:?&body={encoded_text}",
        "Email": f"mailto:?subject=Join the Mission&body={encoded_text}"
    }
    return links

# --- 5. INTERFACE ---
# HEADER SECTION
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
col_logo, col_title = st.columns([1, 3])
with col_logo:
    try: st.image(logo_url, width=200)
    except: st.title("⚖️")
with col_title:
    st.markdown("# CLASS ACTION: OHIO")
    st.markdown("### *Defending Public Education Through Data & Action*")

# SIDEBAR: MISSION STATUS & SHARING
with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 500 else "Principal" if st.session_state.xp_points < 1000 else "THE SUPERINTENDENT"
    
    st.markdown(f"""
        <div class="rank-card">
            <h3>CURRENT RANK</h3>
            <h2 style='color: #facc15;'>{rank}</h2>
            <p>{st.session_state.xp_points} Action XP</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📢 Share Your Rank")
    s = get_share_links(rank, st.session_state.xp_points)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"[🐦 X/Twitter]({s['Twitter']})")
        st.markdown(f"[📱 SMS]({s['SMS']})")
    with c2:
        st.markdown(f"[👥 Facebook]({s['FB']})")
        st.markdown(f"[✉️ Email]({s['Email']})")

# MAIN ACTION AREA
zip_input = st.text_input("📍 ENTER ZIP CODE TO DEPLOY:", max_chars=5, help="Find your district representatives and school data.")

if zip_input and not df.empty:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        # MISSION PREVIEW
        st.success(f"TARGET ACQUIRED: {data['school_district']} | District {data['rep_district']}")
        
        t1, t2, t3 = st.tabs(["👤 IDENTITY", "📋 MISSION", "🚀 DEPLOY"])
        
        with t1:
            st.header("Personalize Your Identity")
            st.session_state.u_name = st.text_input("Full Name:", value=st.session_state.u_name)
            st.session_state.u_role = st.text_input("Role:", value=st.session_state.u_role)
            
            st.subheader("Constituent Badges")
            b1, b2, b3 = st.columns(3)
            with b1:
                st.session_state.is_voter = st.checkbox("Voter", value=True)
                st.session_state.is_taxpayer = st.checkbox("Taxpayer", value=True)
            with b2:
                st.session_state.is_homeowner = st.checkbox("Homeowner", value=st.session_state.is_homeowner)
                st.session_state.is_parent = st.checkbox("Parent", value=st.session_state.is_parent)
            with b3:
                st.session_state.years_ohio = st.number_input("Years in OH:", value=st.session_state.years_ohio)
                st.session_state.years_district = st.number_input("Years in Dist:", value=st.session_state.years_district)

        with t2:
            st.header("The Mission Briefing")
            st.write(f"**District Stats:** Enrollment: {data['enrollment']} | Avg Exp: {data['avg_teacher_ex']} yrs")
            st.session_state.custom_note = st.text_area("Add Your Personal Anecdote:", value=st.session_state.custom_note)
            
            st.subheader("Select Targets")
            if st.button("Select All Targets"): st.session_state.u_targets = ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"]
            st.session_state.u_targets = st.multiselect("Targets:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], default=st.session_state.u_targets)

        with t3:
            st.header("Deployment")
            if not st.session_state.u_targets:
                st.warning("Please select at least one target in the Mission tab.")
            else:
                # PDF & Email Logic (As previously agreed)
                st.info(f"Ready to deploy to {len(st.session_state.u_targets)} recipients.")
                if st.button("🚀 EXECUTE MISSION & EARN XP"):
                    st.session_state.xp_points += (100 * len(st.session_state.u_targets))
                    st.balloons()
                    st.rerun()
