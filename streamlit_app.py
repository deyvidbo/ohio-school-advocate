import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION & WAR ROOM THEME ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* War Room Styling */
    .rank-card { 
        background-color: #1e3a8a; 
        color: white; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center; 
        border: 2px solid #facc15;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .rank-title { font-size: 1.2em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .xp-display { font-size: 2em; font-weight: bold; color: #facc15; margin: 0; }
    
    /* Action Buttons */
    .deploy-btn { 
        display: block; width: 100%; padding: 15px; 
        background-color: #B22234; color: white !important; 
        text-align: center; border-radius: 8px; 
        font-weight: bold; text-decoration: none; 
        margin-bottom: 10px; transition: all 0.3s;
    }
    .deploy-btn:hover { background-color: #8b1a29; transform: translateY(-2px); }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 5px; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE INITIALIZATION ---
# Initialize all keys if they don't exist to prevent "KeyError"
initial_state = {
    'xp_points': 0,
    'u_name': "", 
    'u_role': "", 
    'is_voter': False,
    'is_taxpayer': False,
    'is_homeowner': False,
    'is_renter': False,
    'is_parent': False,
    'child_count': 0,
    'years_ohio': 0,
    'years_district': 0,
    'custom_note': "",
    'u_targets': []
}

for key, val in initial_state.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        # Robust parsing for names with suffixes and multi-line addresses
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"', on_bad_lines='warn')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"System Error: Could not load district data. Ensure 'ohio_districts.csv' is present. {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. BULK PDF GENERATOR (Professional Block Format) ---
def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.set_auto_page_break(auto=True, margin=1.0)
    
    # Build Identity Sentence
    badges = [b for b, active in [("active voter", id_badges['voter']), ("dedicated taxpayer", id_badges['taxpayer']), ("homeowner", id_badges['homeowner']), ("local resident", id_badges['renter'])] if active]
    
    id_base = ", ".join(badges[:-1]) + (" and " + badges[-1] if len(badges) > 1 else badges[0] if badges else "resident")
    parent_part = f" and a parent of {id_badges['count']} children," if id_badges['parent'] else ","
    residency_part = f" Having lived in Ohio for {id_badges['y_ohio']} years and within this district for {id_badges['y_dist']} years,"
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # SENDER BLOCK
        pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
        pdf.cell(0, 0.2, txt=user_info['role'], ln=True)
        pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True); pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True); pdf.ln(0.3)
        
        # RECIPIENT BLOCK
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=f"{rec['role']} {rec['name']}", ln=True); pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=rec['address']); pdf.ln(0.3)
        
        # SALUTATION
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=f"Dear {rec['role']} {last_name}:"); pdf.ln(0.3)
        
        # BODY CONSTRUCTION
        opening = f"My name is {user_info['name']}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
        identity_line = f"As an {id_base}{parent_part}{residency_part} I am writing to you today regarding the future of our public schools."
        
        # Custom Bridge (Seamless)
        custom_section = f"To provide a personal perspective: {custom_text.strip()}" if custom_text.strip() else ""
        if custom_section and not custom_section.endswith(('.', '!', '?')): custom_section += "."

        # ODEW Data Integration
        fiscal_detail = (f"Currently, {data['school_district']} serves {data['enrollment']} students with a poverty rate of {data['poverty_rate']}. "
                         f"Our instructional quality is driven by a workforce averaging {data['avg_teacher_ex']} years of experience, "
                         f"with {data['percent_masters']} of our faculty holding Master's degrees and an average salary of {data['avg_teacher_salary']}. "
                         "Voucher expansion threatens this stability.")
        
        full_body = [opening, identity_line]
        if custom_section: full_body.append(custom_section)
        full_body.extend([fiscal_detail, "I urge you to prioritize public education funding. Thank you."])
        
        for p in full_body:
            # Clean smart quotes for PDF safety
            safe_p = p.replace('’', "'").replace('“', '"').replace('”', '"')
            pdf.multi_cell(0, 0.2, txt=safe_p, align='L')
            pdf.ln(0.2)
        
        # SIGN OFF
        pdf.ln(0.2); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8) 
        pdf.set_font("Times", 'B', 12); pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
        
    return pdf.output(dest="S").encode('latin-1', 'replace')

# --- 5. SIDEBAR: MISSION CONTROL ---
with st.sidebar:
    # Rank Logic
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher" if st.session_state.xp_points < 500 else "THE SUPERINTENDENT"
    
    st.markdown(f"""
        <div class='rank-card'>
            <div class='rank-title'>{rank}</div>
            <div class='xp-display'>{st.session_state.xp_points} XP</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Dynamic Progress Bar
    next_goal = 100 if rank == "Substitute" else 500 if rank == "Teacher" else 1000
    st.progress(min(st.session_state.xp_points / next_goal, 1.0))
    
    st.markdown("---")
    st.subheader("📢 Share Your Rank")
    
    # Universal Sharing Links
    site_url = "https://classactionohio.org"
    msg = urllib.parse.quote(f"I reached the rank of {rank} on Class Action Ohio! Join the mission: {site_url}")
    
    st.markdown(f"🐦 [Post to X/Twitter](https://twitter.com/intent/tweet?text={msg})")
    st.markdown(f"👥 [Share on Facebook](https://www.facebook.com/sharer/sharer.php?u={site_url})")
    st.markdown(f"✉️ [Email Coworkers](mailto:?subject=Join%20the%20Mission&body={msg})")
    st.markdown(f"📱 [Text a Friend](sms:?&body={msg})")
    
    if st.button("🔄 Reset User Data"):
        for key, val in initial_state.items(): st.session_state[key] = val
        st.rerun()

# --- 6. MAIN DASHBOARD ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
c_logo, c_head = st.columns([1, 4])
with c_logo:
    try: st.image(logo_url, width=160)
    except: st.title("⚖️")
with c_head:
    st.markdown("# CLASS ACTION: OHIO")
    st.markdown("### The Statewide Public Education Advocacy Engine")

# Zip Code Entry
zip_input = st.text_input("📍 DEPLOY BY ZIP CODE:", max_chars=5, help="Enter your 5-digit Ohio zip code to load local data.")

if zip_input and not df.empty:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        st.success(f"TARGET ACQUIRED: {data['school_district']} (House District {data['rep_district']})")
        
        t_id, t_msg, t_deploy = st.tabs(["👤 IDENTITY", "📝 MESSAGE", "🚀 DEPLOY"])
        
        # TAB 1: IDENTITY (Direct Key Binding Fix)
        with t_id:
            c1, c2 = st.columns(2)
            with c1: st.text_input("Full Name:", key="u_name") 
            with c2: st.text_input("Title (e.g. Teacher, Parent):", key="u_role")
            
            st.subheader("Constituent Badges")
            b1, b2, b3 = st.columns(3)
            with b1:
                st.checkbox("Voter", key="is_voter")
                st.checkbox("Taxpayer", key="is_taxpayer")
            with b2:
                st.checkbox("Homeowner", key="is_homeowner")
                st.checkbox("Parent", key="is_parent")
                if st.session_state.is_parent:
                    st.number_input("Children:", min_value=1, key="child_count")
            with b3:
                st.number_input("Years in Ohio:", min_value=0, key="years_ohio")
                st.number_input(f"Years in Dist. {data['rep_district']}:", min_value=0, key="years_district")

        # TAB 2: MESSAGE & TARGETS
        with t_msg:
            st.markdown("#### Add Your Voice")
            st.text_area("Personal Anecdote (Integrated into your letter):", key="custom_note")
            
            st.markdown("#### Select Targets")
            all_options = ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"]
            
            c_all, c_clear = st.columns([1, 4])
            with c_all: 
                if st.button("Select All"): 
                    st.session_state.u_targets = all_options
                    st.rerun()
            with c_clear:
                if st.button("Clear Selection"): 
                    st.session_state.u_targets = []
                    st.rerun()
            
            st.multiselect("Recipients:", all_options, key="u_targets")

        # TAB 3: DEPLOYMENT (Action Center)
        with t_deploy:
            if st.session_state.u_targets:
                # 2026 Leadership Logic
                target_map = {
                    "📍 Local Rep": {"name": data['rep_name'], "email": data['rep_email'], "address": data['rep_address'], "role": data['rep_role']},
                    "🏛️ Governor": {"name": "Mike DeWine", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215", "role": "Governor"},
                    "🛡️ Friendly Caucus": {"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Minority Leader"},
                    "🚫 Opposition Leadership": {"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215", "role": "Speaker"}
                }
                selected = [target_map[t] for t in st.session_state.u_targets]
                
                c_email, c_pdf = st.columns(2)
                
                # OPTION A: DIGITAL BLAST
                with c_email:
                    st.subheader("Digital Advocacy")
                    bcc_list = ",".join([r['email'] for r in selected])
                    email_subj = urllib.parse.quote(f"Constituent Support for {data['school_district']}")
                    email_body = urllib.parse.quote(f"Please see my attached advocacy letter regarding House District {data['rep_district']}.\n\n{st.session_state.custom_note}")
                    
                    # Universal Mailto Link
                    mailto_url = f"mailto:?bcc={bcc_list}&subject={email_subj}&body={email_body}"
                    st.markdown(f'<a href="{mailto_url}" class="deploy-btn">✉️ SEND BCC EMAIL BLAST</a>', unsafe_allow_html=True)
                    st.caption("Opens your default mail app. Recipients are BCC'd for privacy.")

                # OPTION B: PHYSICAL MAIL
                with c_pdf:
                    st.subheader("Physical Mail")
                    id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 
                                 'homeowner': st.session_state.is_homeowner, 'renter': st.session_state.is_renter, 
                                 'parent': st.session_state.is_parent, 'count': st.session_state.child_count, 
                                 'y_ohio': st.session_state.years_ohio, 'y_dist': st.session_state.years_district}
                    
                    pdf_bytes = create_bulk_pdf(selected, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                    
                    st.download_button(
                        label=f"📄 DOWNLOAD {len(selected)} LETTERS (PDF)", 
                        data=pdf_bytes, 
                        file_name="Ohio_Advocacy_Pack.pdf", 
                        mime="application/pdf"
                    )
                    st.caption("Generates a print-ready packet with one letter per recipient.")

                # FINALIZATION
                st.markdown("---")
                if st.button("✅ COMPLETE MISSION & LOG XP"):
                    st.session_state.xp_points += (100 * len(selected))
                    st.balloons()
                    st.rerun()
            else:
                st.warning("Please select at least one target in the 'MESSAGE' tab to deploy.")
    else:
        st.error("District data not found. Please check your zip code.")
