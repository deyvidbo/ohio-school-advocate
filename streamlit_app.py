import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF

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

# --- 4. ENHANCED PDF GENERATOR (With Mailing Address) ---
def create_pdf(target_rep, district, content, user_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CLASS ACTION: OHIO ADVOCACY", ln=True, align='C')
    pdf.ln(5)
    
    # Rep Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 7, txt=f"To: {target_rep.get('rep_role', 'Honorable')} {target_rep.get('rep_name', 'Legislator')}", ln=True)
    pdf.set_font("Arial", '', 10)
    # Restore Physical Address support
    address = target_rep.get('rep_address', '77 S. High St, Columbus, OH 43215')
    pdf.multi_cell(0, 5, txt=address)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Regarding: Emergency Funding Support for {district}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, txt=content)
    
    pdf.ln(15)
    pdf.cell(200, 10, txt=f"Sincerely,", ln=True)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=user_name, ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- 5. MESSAGE GENERATION LOGIC (RESTORED) ---
def generate_advocacy_content(target_rep, user_info, mode):
    student_hook = f"I am a voter in {user_info['district']} (Zip: {user_info['zip']})."
    if user_info.get('enrollment'):
        student_hook += f" Our district serves {user_info['enrollment']} students who depend on fair state funding."

    if mode == "🏛️ Governor":
        subject = "URGENT: Executive Action on School Funding"
        body = f"Dear Governor DeWine,\n\n{student_hook}\n\nI urge you to line-item veto voucher expansion and prioritize the Fair School Funding Plan. Public dollars belong in public schools.\n\nSincerely,\n{user_info['name']}"
    elif mode == "🛡️ Defenders":
        subject = f"Thank you for supporting {user_info['district']}"
        body = f"Dear Legislator,\n\n{student_hook}\n\nThank you for standing as a defender of public education. We appreciate your support for the students of {user_info['district']}.\n\nSincerely,\n{user_info['name']}"
    elif mode == "🚫 Opponents":
        subject = "Opposition to Voucher Expansion"
        body = f"Dear Legislator,\n\n{student_hook}\n\nI am writing to express my strong opposition to current voucher expansion efforts that drain resources from our local classrooms.\n\nSincerely,\n{user_info['name']}"
    else: # Local Rep
        subject = f"Constituent Concern: {user_info['district']}"
        body = f"Dear {target_rep.get('rep_role', 'Rep')} {target_rep.get('rep_name', '')},\n\n{student_hook}\n\nAs your constituent, I ask you to prioritize local public school funding over private interests.\n\nSincerely,\n{user_info['name']}"
    
    return subject, body

# --- 6. APP INTERFACE ---
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

# RESTORED ACTION LOGIC
if zip_code:
    res = df[df['zip_code'] == zip_code]
    if not res.empty:
        user_data = res.iloc[0].to_dict()
        dist_name = user_data['school_district']
        user_info = {
            "name": user_name, "zip": zip_code, 
            "district": dist_name, "enrollment": user_data.get('enrollment', '')
        }
        
        st.success(f"📍 District: **{dist_name}** ({user_data.get('enrollment', 'Unknown')} Students)")
        
        st.header("2. Take Action")
        mode = st.radio("Task:", ["📍 Local Rep", "🛡️ Defenders", "🚫 Opponents", "🏛️ Governor"], horizontal=True)
        
        # Generate restored personalized content
        subject, content = generate_advocacy_content(user_data, user_info, mode)
        
        # Routing Emails
        if mode == "🛡️ Defenders":
            emails = df[df['rep_stance'] == "Friendly"]['rep_email'].unique().tolist()
        elif mode == "🚫 Opponents":
            emails = df[df['rep_stance'] == "Hostile"]['rep_email'].unique().tolist()
        elif mode == "🏛️ Governor":
            emails = ["governor@ohio.gov"]
        else:
            emails = [user_data['rep_email']]

        # STEP 1: RESTORED BCC EMAIL
        email_list = ",".join([str(e) for e in emails if str(e) != "nan"])
        safe_sub = urllib.parse.quote(subject)
        safe_body = urllib.parse.quote(content)
        mailto_link = f"mailto:?bcc={email_list}&subject={safe_sub}&body={safe_body}"
        
        st.markdown(f'<a href="{mailto_link}" target="_blank" style="text-decoration:none;"><div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ SEND EMAIL (BCC ALL)</div></a>', unsafe_allow_html=True)
        
        # STEP 2: PRINTABLE PDF (With Restored Address Data)
        pdf_data = create_pdf(user_data, dist_name, content, user_name)
        st.download_button(label="📄 GENERATE PRINTABLE LETTER", data=pdf_data, file_name="Class_Action_Letter.pdf", mime="application/pdf")
        
        if st.button("✅ TASK COMPLETE (+100 XP)"):
            st.session_state.xp_points += 100
            st.session_state.district_stats[dist_name] = st.session_state.district_stats.get(dist_name, 0) + 1
            st.rerun()

# --- 7. LEADERBOARD & SOCIAL (Same as before) ---
st.markdown("---")
st.header("🏆 District Leaderboard")
if st.session_state.district_stats:
    leader_df = pd.DataFrame(list(st.session_state.district_stats.items()), columns=['District', 'Actions'])
    st.table(leader_df.sort_values(by='Actions', ascending=False).head(5))

# Social Buttons
encoded_msg = urllib.parse.quote(f"I reached {rank_title} on Class Action! Join me: https://ohio-advocate.streamlit.app")
st.write("📲 **Recruit Peers**")
s1, s2, s3 = st.columns(3)
with s1: st.markdown(f'<a href="sms:?&body={encoded_msg}" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">SMS</div></a>', unsafe_allow_html=True)
with s2: st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u=https://ohio-advocate.streamlit.app" target="_blank" style="text-decoration:none;"><div style="background-color:#1877F2;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">FB</div></a>', unsafe_allow_html=True)
with s3: st.markdown(f'<a href="https://twitter.com/intent/tweet?text={encoded_msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">X</div></a>', unsafe_allow_html=True)
