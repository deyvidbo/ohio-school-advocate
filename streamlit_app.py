import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import base64

# --- CONFIGURATION & DATA ---

# 1. THE LEGISLATOR DATABASE (Sample - You would expand this via CSV)
# "Stance" logic: 'Hostile' = Voted for EdChoice/Funding Freeze. 'Friendly' = Voted No.
legislators_db = pd.DataFrame([
    {"name": "Matt Huffman", "role": "House Speaker", "district": 78, "email": "rep78@ohiohouse.gov", "party": "R", "stance": "Hostile", "career_stage": "Re-election"},
    {"name": "Andrew Brenner", "role": "Senate Education Chair", "district": 19, "email": "brenner@ohiosenate.gov", "party": "R", "stance": "Hostile", "career_stage": "Re-election"},
    {"name": "Jerry Cirino", "role": "Senator", "district": 18, "email": "cirino@ohiosenate.gov", "party": "R", "stance": "Hostile", "career_stage": "Retiring"}, # Example status
    {"name": "Generic Friendly Rep", "role": "Rep", "district": 1, "email": "rep1@ohiohouse.gov", "party": "D", "stance": "Friendly", "career_stage": "Re-election"},
])

# 2. THE DISTRICT MAP (Sample - Links Districts to Rep District IDs)
# In production, this would be a full CSV of all 600+ Ohio districts
district_map = {
    "Hamilton City Schools": {"House": 47, "Senate": 4},
    "Linden Local Schools": {"House": 78, "Senate": 19}, # Targeted example
    "Columbus City Schools": {"House": 1, "Senate": 15},
}

# --- LOGIC FUNCTIONS ---

def get_reps(district_name):
    """Finds the reps for a selected school district."""
    if district_name not in district_map:
        return []
    
    mapping = district_map[district_name]
    
    # Filter DB for matching districts
    reps = legislators_db[
        (legislators_db['district'] == mapping['House']) & (legislators_db['role'].str.contains("House")) |
        (legislators_db['district'] == mapping['Senate']) & (legislators_db['role'].str.contains("Sen"))
    ]
    
    # ALWAYS add Leadership (Huffman/Brenner) if not present, as they control the budget
    leadership = legislators_db[legislators_db['name'].isin(["Matt Huffman", "Andrew Brenner"])]
    
    combined = pd.concat([reps, leadership]).drop_duplicates(subset=['email'])
    return combined.to_dict('records')

def generate_message(rep, user_name, user_district):
    """The Persuasion Engine: Generates text based on Rep attributes."""
    today = date.today().strftime("%B %d, %Y")
    
    # --- TEMPLATE LOGIC ---
    
    if rep['stance'] == "Hostile":
        subject = f"URGENT: The Financial Stability of {user_district}"
        
        opening = f"Dear {rep['role']} {rep['name']},"
        
        core_issue = (
            f"\n\nI am writing as a concerned educator and voter in {user_district}. "
            f"The decision to freeze public school 'base cost' inputs at 2022 levels, effectively cutting "
            f"our real-dollar funding while fully funding universal EdChoice vouchers, is devastating our classrooms."
        )
        
        # PSYCHOLOGICAL TRIGGER: Re-election vs Legacy
        if rep['career_stage'] == "Re-election":
            closer = (
                "\n\nWe are organizing. Teachers, parents, and community members are paying close attention "
                "to who supports our public schools and who undermines them. "
                "I urge you to reverse course on the EdChoice expansion and update the Fair School Funding Plan inputs immediately."
            )
        else: # Retiring
            closer = (
                "\n\nAs you look toward your legacy in Ohio, ask yourself: Do you want to be remembered as a leader "
                "who upheld our constitutional promise to public education, or one who oversaw its dismantling? "
                "Please, do the right thing before your term ends."
            )
            
    else: # Friendly
        subject = f"Support Needed: Protect {user_district} Funding"
        opening = f"Dear {rep['role']} {rep['name']},"
        core_issue = (
            f"\n\nThank you for your continued support of public education. However, the current budget's "
            f"refusal to update 'base cost' inputs is hurting {user_district}."
        )
        closer = (
            "\n\nPlease be our voice. We need you to aggressively push specifically for the update of "
            "funding inputs to current economic data and to call for a cap on voucher spending."
        )

    full_body = f"{opening}\n{core_issue}\n{closer}\n\nSincerely,\n{user_name}\n{user_district} Educator & Voter"
    
    return subject, full_body

def create_pdf(rep, user_name, user_address, content):
    """Generates a professional PDF letter."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Header
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=user_name, ln=1, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=user_address, ln=1, align='C')
    pdf.cell(200, 5, txt=date.today().strftime("%B %d, %Y"), ln=1, align='C')
    pdf.ln(10)
    
    # Recipient
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 5, txt=f"The Honorable {rep['name']}", ln=1)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 5, txt="Ohio Statehouse", ln=1) # Simplified address
    pdf.cell(0, 5, txt="Columbus, OH 43215", ln=1)
    pdf.ln(10)
    
    # Body
    pdf.multi_cell(0, 6, txt=content)
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP INTERFACE ---

st.set_page_config(page_title="Ohio School Advocate", page_icon="🏫")

st.title("📢 Ohio Legislator Communicator")
st.markdown("""
**Empowering Ohio Educators to Demand Fair Funding.**
Select your district to identify your representatives. The app automatically drafts targeted messages based on their voting record.
""")

with st.sidebar:
    st.header("Your Information")
    user_name = st.text_input("Name", "David M. Bothast")
    user_addr = st.text_input("City/State (For Letters)", "Hamilton, OH")
    user_district = st.selectbox("Select School District", list(district_map.keys()))
    
    st.info("ℹ️ **Privacy Note:** Your data is not stored. It is only used to generate the draft.")

# Main Execution
if user_district:
    targets = get_reps(user_district)
    
    st.subheader(f"Representatives for {user_district}")
    
    for rep in targets:
        # Determine Color Coding
        color = "red" if rep['stance'] == "Hostile" else "green"
        emoji = "🚫" if rep['stance'] == "Hostile" else "✅"
        
        with st.expander(f"{emoji} {rep['role']} {rep['name']} ({rep['party']})"):
            # Generate the content
            subject, body = generate_message(rep, user_name, user_district)
            
            # Display Context
            if rep['stance'] == "Hostile":
                st.error(f"**Voting Record:** Voted YES on EdChoice Expansion & Funding Freeze.\n\n**Strategy:** Pressure them on {rep['career_stage']}.")
            else:
                st.success("**Voting Record:** Supporter of Public Schools.\n\n**Strategy:** Encourage them to fight harder.")
            
            # --- ACTION BUTTONS ---
            col1, col2 = st.columns(2)
            
            # 1. EMAIL BUTTON
            with col1:
                # Mailto links must be URL encoded
                import urllib.parse
                safe_subject = urllib.parse.quote(subject)
                safe_body = urllib.parse.quote(body)
                mailto_link = f"mailto:{rep['email']}?subject={safe_subject}&body={safe_body}"
                
                st.markdown(f"""
                <a href="{mailto_link}" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; background-color:#FF4B4B; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">
                        ✉️ Open Email Draft
                    </button>
                </a>
                """, unsafe_allow_html=True)

            # 2. PRINT LETTER BUTTON
            with col2:
                pdf_bytes = create_pdf(rep, user_name, user_addr, body)
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="Letter_to_{rep["name"].replace(" ", "_")}.pdf">📄 Download PDF Letter</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            # Preview
            st.text_area("Preview Message:", value=body, height=200, key=rep['email'])
