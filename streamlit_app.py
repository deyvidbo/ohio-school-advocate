import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import base64
import urllib.parse

# --- 1. THE DATA BRAIN (Database) ---

# A. Legislator Database (The Politicians)
# NOTE: You would eventually replace this with a full CSV file.
legislators_db = pd.DataFrame([
    # HAMILTON / BUTLER COUNTY REPS
    {"name": "Thomas Hall", "role": "State Rep", "district": "46", "email": "rep46@ohiohouse.gov", "party": "R", "stance": "Hostile", "career_stage": "Re-election"},
    {"name": "George Lang", "role": "State Senator", "district": "4", "email": "lang@ohiohouse.gov", "party": "R", "stance": "Hostile", "career_stage": "Re-election"},
    
    # LEADERSHIP (Always included)
    {"name": "Matt Huffman", "role": "House Speaker", "district": "78", "email": "rep78@ohiohouse.gov", "party": "R", "stance": "Hostile", "career_stage": "Legacy"},
    {"name": "Andrew Brenner", "role": "Senate Education Chair", "district": "19", "email": "brenner@ohiosenate.gov", "party": "R", "stance": "Hostile", "career_stage": "Legacy"},
])

# B. Zip Code to District Map (The "Auto-Connect" Feature)
# This maps a Zip Code -> School District Name
zip_code_map = {
    # Hamilton / Fairfield Area
    "45011": "Hamilton City Schools",
    "45013": "Hamilton City Schools",
    "45015": "Hamilton City Schools",
    "45014": "Fairfield City Schools",
    # Columbus Area (Samples)
    "43215": "Columbus City Schools",
    "43081": "Westerville City Schools",
}

# C. District to Legislative District Map
# This maps School District Name -> The House/Senate District Numbers
district_to_politics_map = {
    "Hamilton City Schools": {"House": "46", "Senate": "4"}, 
    "Fairfield City Schools": {"House": "51", "Senate": "4"},
    "Columbus City Schools": {"House": "1", "Senate": "15"},
    "Westerville City Schools": {"House": "19", "Senate": "19"},
}

# --- 2. LOGIC FUNCTIONS ---

def get_reps_by_district(school_district_name):
    """Finds the politicians for a specific school district."""
    if school_district_name not in district_to_politics_map:
        return []
    
    mapping = district_to_politics_map[school_district_name]
    
    # 1. Find Local Reps
    local_reps = legislators_db[
        (legislators_db['district'] == mapping['House']) | 
        (legislators_db['district'] == mapping['Senate'])
    ]
    
    # 2. Find Leadership (They affect everyone)
    leadership = legislators_db[legislators_db['role'].isin(["House Speaker", "Senate Education Chair"])]
    
    # Combine and remove duplicates
    combined = pd.concat([local_reps, leadership]).drop_duplicates(subset=['name'])
    return combined.to_dict('records')

def generate_message(rep, user_name, user_district):
    """Generates the persuasive text."""
    today = date.today().strftime("%B %d, %Y")
    
    if rep['stance'] == "Hostile":
        subject = f"URGENT: Financial Distress in {user_district}"
        body = (
            f"Dear {rep['role']} {rep['name']},\n\n"
            f"I am a voter in {user_district}. The decision to freeze public school funding "
            f"at 2022 levels while expanding EdChoice vouchers is draining our classrooms.\n\n"
        )
        if rep['career_stage'] == "Re-election":
            body += "We are organizing locally for the upcoming election. We need you to support public schools now."
        else:
            body += "Please consider your legacy. Do not be the leader who dismantled Ohio's public education."
    else:
        subject = f"Support Needed: {user_district}"
        body = f"Dear {rep['role']} {rep['name']},\n\nThank you for supporting {user_district}. Please keep fighting to update the Fair School Funding Plan inputs."

    full_text = f"{body}\n\nSincerely,\n{user_name}\n{user_district} Resident"
    return subject, full_text

def create_pdf(rep, user_name, user_addr, content):
    """Generates a PDF letter."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"From: {user_name}", ln=1)
    pdf.cell(200, 10, txt=f"To: {rep['role']} {rep['name']}", ln=1)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=content)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. THE APP INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

st.title("📢 Ohio Legislator Communicator")
st.markdown("Enter your **Zip Code** to automatically find your School District and Representatives.")

# SIDEBAR INPUTS
with st.sidebar:
    st.header("1. Your Info")
    user_name = st.text_input("Your Name", "Concerned Citizen")
    user_addr = st.text_input("Your City", "Hamilton, OH")
    
    st.header("2. Find Your District")
    # THE NEW ZIP CODE SEARCH
    zip_code = st.text_input("Enter Zip Code", max_chars=5)
    
    # Logic: Auto-select based on Zip, or fall back to manual
    detected_district = zip_code_map.get(zip_code, None)
    
    if detected_district:
        st.success(f"📍 Found: {detected_district}")
        selected_district = detected_district
    else:
        if zip_code:
            st.warning("Zip not in database yet. Please select manually.")
        selected_district = st.selectbox("Or Select District", list(district_to_politics_map.keys()))

# MAIN AREA
if selected_district:
    reps = get_reps_by_district(selected_district)
    
    st.divider()
    st.subheader(f"Representatives for {selected_district}")
    st.info(f"These officials control the funding for **{selected_district}**.")
    
    for rep in reps:
        with st.expander(f"{rep['role']} {rep['name']} ({rep['party']})"):
            # Color code the stance
            if rep['stance'] == "Hostile":
                st.error("⚠️ Voted for EdChoice / Funding Cuts")
            else:
                st.success("✅ Public School Supporter")
                
            subject, body = generate_message(rep, user_name, selected_district)
            
            # Email Link
            safe_sub = urllib.parse.quote(subject)
            safe_body = urllib.parse.quote(body)
            mailto = f"mailto:{rep['email']}?subject={safe_sub}&body={safe_body}"
            
            st.markdown(f"[**✉️ Send Email Now**]({mailto})")
            
            # PDF Button
            pdf_data = create_pdf(rep, user_name, user_addr, body)
            b64 = base64.b64encode(pdf_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Letter_to_{rep["name"]}.pdf">📄 Download PDF Letter</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.text_area("Preview:", body, height=150)

else:
    st.info("👈 Please enter your Zip Code to begin.")
