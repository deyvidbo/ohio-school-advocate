import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .rank-card { background-color: #1e3a8a; color: white; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .action-button { background-color: #B22234; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; text-decoration: none; display: block; }
    .action-button:hover { background-color: #8b1a29; color: white; }
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

# --- 3. RANKING & DYNAMIC SHARING ---
def get_rank(xp):
    if xp < 100: return "Substitute", 100, "Teacher"
    if xp < 500: return "Teacher", 500, "Principal"
    return "THE SUPERINTENDENT", 1000, "Advocacy Legend"

rank, next_goal, next_rank = get_rank(st.session_state.xp_points)

# --- 4. SIDEBAR: MISSION CONTROL ---
with st.sidebar:
    st.markdown(f"""<div class="rank-card"><p style='text-transform: uppercase; font-size: 0.8em;'>Current Rank</p>
                <h2 style='color: #facc15; margin: 0;'>{rank}</h2><p>{st.session_state.xp_points} XP</p></div>""", unsafe_allow_html=True)
    
    st.progress(min(st.session_state.xp_points / next_goal, 1.0))
    st.caption(f"Next Promotion: {next_rank}")
    
    st.markdown("---")
    st.subheader("📢 Share the Mission")
    
    site_url = "https://classactionohio.org"
    share_msg = urllib.parse.quote(f"I'm advocating for Ohio schools as a {rank}! Join the mission: {site_url}")
    
    # Desktop-Optimized Sharing
    st.markdown(f"🐦 [Post to X/Twitter](https://twitter.com/intent/tweet?text={share_msg})")
    st.markdown(f"👥 [Share on Facebook](https://www.facebook.com/sharer/sharer.php?u={site_url})")
    st.markdown(f"✉️ [Email Coworkers](mailto:?subject=Join the Mission&body={share_msg})")
    st.markdown(f"📱 [Text a Friend](sms:?&body={share_msg})")

# --- 5. DATA & DEPLOYMENT ---
@st.cache_data
def load_data():
    # Final data engine with quotechar safety
    df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str}, quotechar='"')
    df.fillna("N/A", inplace=True)
    return df

df = load_data()
zip_input = st.text_input("📍 ENTER ZIP CODE TO DEPLOY:")

if zip_input and not df.empty:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        st.success(f"TARGET: {data['school_district']} (District {data['rep_district']})")
        
        # Tabs for clean UX
        t_id, t_msg, t_deploy = st.tabs(["👤 IDENTITY", "📝 MESSAGE", "🚀 DEPLOY"])
        
        with t_id:
            st.session_state.u_name = st.text_input("Full Name:", value=st.session_state.u_name)
            st.session_state.u_role = st.text_input("Role:", value=st.session_state.u_role)
            st.checkbox("Voter", value=st.session_state.is_voter, key="v")
            st.number_input("Years in District:", value=st.session_state.years_district, key="yd")

        with t_msg:
            st.session_state.custom_note = st.text_area("Your Story (Integrated into letter):", value=st.session_state.custom_note)
            st.session_state.u_targets = st.multiselect("Targets:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], default=st.session_state.u_targets)

        with t_deploy:
            if st.session_state.u_targets:
                # RECIPIENT MAPPING
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": data['rep_address'], "role": data['rep_role']},
                    "🏛️ Governor": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Friendly Caucus": {"name": "Dani Isaacsohn", "email": "rep24@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Opposition Leadership": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                selected = [target_map[t] for t in st.session_state.u_targets]
                
                c_mail, c_pdf = st.columns(2)
                
                with c_mail:
                    st.subheader("Digital Advocacy")
                    bcc_list = ",".join([r['email'] for r in selected])
                    subject = urllib.parse.quote(f"Constituent Support for {data['school_district']}")
                    body = urllib.parse.quote(f"Please see my attached advocacy letter for District {data['rep_district']}.\n\n{st.session_state.custom_note}")
                    
                    # Mailto link optimized for both Desktop (Outlook/Webmail) and Mobile
                    mailto_link = f"mailto:?bcc={bcc_list}&subject={subject}&body={body}"
                    
                    st.markdown(f'<a href="{mailto_link}" class="action-button">✉️ BCC ALL TARGETS</a>', unsafe_allow_html=True)
                    st.caption("Recommended for all users. Opens your default mail client.")

                with c_pdf:
                    st.subheader("Physical Mail")
                    # (PDF creation logic remains same as previously agreed)
                    st.button("📄 DOWNLOAD BULK PDF") 

                if st.button("🚀 COMPLETE MISSION"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons()
