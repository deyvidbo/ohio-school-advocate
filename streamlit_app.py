import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

# --- 2. DATA ENGINE (The Auto-Connect Logic) ---
@st.cache_data
def load_lookup_data():
    try:
        # Load the mapping file
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str})
        return df
    except FileNotFoundError:
        st.error("⚠️ DATA FILE MISSING: Please upload 'ohio_districts.csv' to the app folder.")
        return pd.DataFrame()

df_lookup = load_lookup_data()

# --- 3. THE INTERFACE ---
st.title("⚖️ Class Action: Ohio")
st.markdown("### 🚨 Mission: Defend Public Education")

# Global State for XP
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0

# STEP 1: ZIP CODE ENTRY
zip_input = st.text_input("📍 ENTER ZIP CODE:", max_chars=5, help="This auto-connects you to your local reps and schools.")

if zip_input:
    # Filter for matches
    matches = df_lookup[df_lookup['zip_code'] == zip_input]
    
    if matches.empty:
        st.warning("Zip code not found in Ohio database. Please enter details manually in the tabs below.")
        # Fallback values
        selected_data = {"school_district": "", "enrollment": "Unknown", "rep_name": "", "rep_email": "", "rep_district": ""}
    else:
        # Handle "Collision" (Zip codes spanning multiple districts)
        if len(matches) > 1:
            st.info(f"Multiple districts found for {zip_input}. Please select yours:")
            choice = st.selectbox("Select your School District:", matches['school_district'].tolist())
            selected_data = matches[matches['school_district'] == choice].iloc[0].to_dict()
        else:
            selected_data = matches.iloc[0].to_dict()
            st.success(f"✅ CONNECTED: {selected_data['school_district']} | Rep. {selected_data['rep_name']}")

    # --- THE MISSION TABS ---
    t_id, t_msg, t_deploy = st.tabs(["👤 IDENTITY", "📝 TESTIMONY", "🚀 DEPLOY"])

    with t_id:
        st.text_input("Your Full Name:", key="u_name")
        st.text_input("Your Professional Title:", key="u_role", value="Ohio Educator" if "teacher" in st.session_state.get('u_name','').lower() else "")
        st.markdown(f"**Auto-Connected School District:** {selected_data['school_district']}")
        st.checkbox("I am an active Ohio Voter", key="is_voter")
        st.checkbox("I am a Homeowner/Property Taxpayer", key="is_taxpayer")

    with t_msg:
        st.subheader("Craft Your Message")
        anecdote = st.text_area("Your Story:", placeholder="Briefly describe how voucher expansion impacts your specific classroom or community...")
        
        st.markdown("---")
        st.write("🎯 **Primary Target:**")
        st.info(f"Rep. {selected_data['rep_name']} (District {selected_data['rep_district']})")
        
        include_leadership = st.toggle("Include House Leadership (Speaker & Minority Leader)", value=True)

    with t_deploy:
        if st.session_state.u_name:
            # Recipients List
            recipients = []
            if selected_data['rep_name']:
                recipients.append({"name": selected_data['rep_name'], "email": selected_data['rep_email'], "role": "Representative"})
            
            if include_leadership:
                recipients.append({"name": "Matt Huffman", "email": "rep78@ohiohouse.gov", "role": "Speaker of the House"})
                recipients.append({"name": "Allison Russo", "email": "rep07@ohiohouse.gov", "role": "Minority Leader"})

            # EMAIL ACTION
            bcc_list = ",".join([r['email'] for r in recipients])
            subject = urllib.parse.quote(f"URGENT: Save {selected_data['school_district']} - Prioritize Public Education")
            body_text = f"Dear Representatives,\n\nMy name is {st.session_state.u_name}. I am a resident of District {selected_data['rep_district']} and a stakeholder in {selected_data['school_district']}.\n\n{anecdote}\n\nOur district serves {selected_data['enrollment']} students. Please prioritize public schools over universal vouchers.\n\nSincerely,\n{st.session_state.u_name}"
            body_encoded = urllib.parse.quote(body_text)
            
            st.markdown(f'<a href="mailto:?bcc={bcc_list}&subject={subject}&body={body_encoded}" style="display: block; width: 100%; padding: 20px; background-color: #b91c1c; color: white; text-align: center; border-radius: 10px; font-weight: bold; text-decoration: none;">✉️ LAUNCH EMAIL BLAST</a>', unsafe_allow_html=True)

            # FINALIZE
            if st.button("✅ Log Mission & Earn XP"):
                st.session_state.xp_points += (50 * len(recipients))
                st.balloons()
                st.success(f"Mission logged! You now have {st.session_state.xp_points} XP.")
        else:
            st.error("Please enter your name in the IDENTITY tab to unlock deployment.")
