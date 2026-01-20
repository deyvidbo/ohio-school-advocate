import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
import base64

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

if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}

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

# --- 4. PDF GENERATOR FUNCTION ---
def create_pdf(target_name, district, content, user_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CLASS ACTION: OHIO ADVOCACY", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"To: {target_name}", ln=True)
    pdf.cell(200, 10, txt=f"Regarding: {district} Funding", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=content)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Sincerely,", ln=True)
    pdf.cell(200, 10, txt=user_name, ln=True)
    return pdf.output(dest="S").encode("latin-1")

# --- 5. APP INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try:
    st.image(logo_url, width=380) 
except:
    st.title("⚖️ CLASS ACTION")
st.markdown(f"<h1 style='text-align: center; color:#B22234; margin-top:-20px;'>CLASS ACTION</h1>", unsafe_allow_html=True)
st.markdown("</center>", unsafe_allow_html=True)

# RANK DASHBOARD
st.markdown(f"""
    <div style="background-color:{rank_color}11; border:3px solid {rank_color}; padding:20px; border-radius:15px; text-align:center; margin-bottom:25px;">
        <h2 style="margin:0; color:{rank_color};">{rank_title}</h2>
        <p style="margin:5px 0; font-weight:bold;">XP: {st.session_state.xp_points} / 300</p>
    </div>
""", unsafe_allow_html=True)

# INPUTS
st.header("1. Identify Your District")
c1, c2 = st.columns(2)
with c1:
    zip_code = st.text_input("Enter Zip Code", max_chars=5)
with c2:
    user_name = st.text_input("Enter Your Name", "Concerned Educator")

# ADVOCACY LOGIC
if zip_code:
    res = df[df['zip_code'] == zip_code]
    if not res.empty:
        user_data = res.iloc[0].to_dict()
        dist_name = user_data['school_district']
        st.success(f"📍 District: **{dist_name}**")
        
        st.header("2. Take Action")
        mode = st.radio("Task:", ["📍 Local Rep", "🛡️ Defenders", "🚫 Opponents", "🏛️ Governor"], horizontal=True)
        
        # Content Generation
        target_name = user_data['rep_name'] if mode == "📍 Local Rep" else "Legislator"
        content = f"I am a voter in {dist_name}. I urge you to prioritize public school funding and update the Fair School Funding Plan inputs. Our students deserve a fully funded education."
        
        # STEP 1: Email
        safe_body = urllib.parse.quote(content)
        mailto_link = f"mailto:{user_data['rep_email']}?subject=Action Needed&body={safe_body}"
        st.markdown(f'<a href="{mailto_link}" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND EMAIL</div></a>', unsafe_allow_html=True)
        
        # NEW: STEP 2: Print/PDF
        pdf_data = create_pdf(target_name, dist_name, content, user_name)
        st.download_button(label="📄 GENERATE PRINTABLE LETTER", data=pdf_data, file_name="Class_Action_Letter.pdf", mime="application/pdf")
        
        if st.button("✅ TASK COMPLETE (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[dist_name] = st.session_state.district_stats.get(dist_name, 0) + 1
            st.rerun()

# --- 6. LEADERBOARD ---
st.markdown("---")
st.header("🏆 District Leaderboard")
if st.session_state.district_stats:
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
    st.table(leader_df.sort_values(by='Actions', ascending=False).head(5))

# --- 7. VISUAL BADGE & SOCIAL ---
st.markdown("---")
st.header("3. Spread the Word")
st.markdown(f"""
    <div style="background-color:white; border:5px solid #B22234; padding:30px; border-radius:15px; text-align:center; box-shadow: 10px 10px 0px #3C3B6E;">
        <h2 style="color:#B22234;">CLASS ACTION</h2>
        <h3 style="color:#3C3B6E;">{rank_title}</h3>
        <p>I am defending Ohio's public schools!</p>
    </div>
""", unsafe_allow_html=True)

# Share Buttons
encoded_msg = urllib.parse.quote(f"I reached {rank_title} on Class Action! Join me: https://ohio-advocate.streamlit.app")
st.write("📲 **Recruit Peers**")
s1, s2, s3 = st.columns(3)
with s1: st.markdown(f'<a href="sms:?&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">SMS</div></a>', unsafe_allow_html=True)
with s2: st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u=https://ohio-advocate.streamlit.app" target="_blank" style="text-decoration:none;"><div style="background-color:#1877F2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">FB</div></a>', unsafe_allow_html=True)
with s3: st.markdown(f'<a href="https://twitter.com/intent/tweet?text={encoded_msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">X</div></a>', unsafe_allow_html=True)
