import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Class Action Ohio", page_icon="⚖️", layout="wide")

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state: st.session_state.xp_points = 0
if 'hall_of_fame' not in st.session_state: st.session_state.hall_of_fame = ["David M. Bothast"]

defaults = {
    'u_name': "David M. Bothast", 'u_role': "K-8 Visual Arts Teacher", 'u_targets': ["📍 Local Rep"],
    'is_parent': False, 'child_count': 0, 'is_homeowner': True, 'is_renter': False,
    'is_taxpayer': True, 'is_voter': True, 'years_ohio': 0, 'years_district': 0,
    'custom_note': ""
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 3. AUDIT-PROTECTED DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str}, quotechar='"', on_bad_lines='warn')
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. BULK PDF ENGINE (One Page Per Representative) ---
def create_bulk_pdf(recipients_list, user_info, data, id_badges, custom_text):
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.set_margins(left=1.0, top=1.0, right=1.0)
    pdf.set_auto_page_break(auto=True, margin=1.0)
    
    # Identity Sentence Logic
    badges = []
    if id_badges['voter']: badges.append("active voter")
    if id_badges['taxpayer']: badges.append("dedicated taxpayer")
    if id_badges['homeowner']: badges.append("homeowner")
    if id_badges['renter']: badges.append("local resident")
    
    id_base = ", ".join(badges[:-1]) + (" and " + badges[-1] if len(badges) > 1 else badges[0] if badges else "resident")
    parent_part = f" and a parent of {id_badges['count']} children," if id_badges['parent'] else ","
    residency_part = f" Having lived in Ohio for {id_badges['y_ohio']} years and within this district for {id_badges['y_dist']} years,"
    
    for rec in recipients_list:
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        
        # Block Format Header
        pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
        pdf.cell(0, 0.2, txt=user_info['role'], ln=True)
        pdf.cell(0, 0.2, txt=f"Zip Code: {user_info['zip']}", ln=True); pdf.ln(0.2)
        pdf.cell(0, 0.2, txt=date.today().strftime("%B %d, %Y"), ln=True); pdf.ln(0.3)
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 0.2, txt=f"{rec['role']} {rec['name']}", ln=True); pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 0.2, txt=rec['address']); pdf.ln(0.3)
        
        last_name = rec['name'].split()[-1]
        pdf.cell(0, 0.2, txt=f"Dear {rec['role']} {last_name}:")
        pdf.ln(0.3)
        
        # Body Construction with ODEW Data
        opening = f"My name is {user_info['name']}. I live in House District {data['rep_district']}, home of the {data['school_district']}."
        identity_line = f"As an {id_base}{parent_part}{residency_part} I am writing to you today regarding the future of our public schools."
        
        custom_section = ""
        if custom_text.strip():
            custom_section = f"To provide a personal perspective from my experience: {custom_text.strip()}"
            if not custom_section.endswith(('.', '!', '?')): custom_section += "."

        fiscal_detail = (
            f"Currently, {data['school_district']} serves {data['enrollment']} students with a poverty rate of {data['poverty_rate']}. "
            f"Our instructional quality is driven by a veteran workforce averaging {data['avg_teacher_ex']} years of experience, "
            f"with {data['percent_masters']} of our faculty holding Master's degrees. "
            "Predictable local funding is vital; voucher expansion threatens this professional stability."
        )

        action = f"I urge you, as a {rec['role']}, to prioritize public education funding. Thank you for your consideration."
        
        full_body = [opening, identity_line]
        if custom_section: full_body.append(custom_section)
        full_body.extend([fiscal_detail, action])
        
        for p in full_body:
            pdf.multi_cell(0, 0.2, txt=p.replace('’', "'").replace('“', '"').replace('”', '"'), align='L')
            pdf.ln(0.2)
        
        pdf.ln(0.2); pdf.cell(0, 0.2, txt="Sincerely,", ln=True); pdf.ln(0.8) 
        pdf.set_font("Times", 'B', 12); pdf.cell(0, 0.2, txt=user_info['name'], ln=True)
        
    return pdf.output(dest="S").encode('latin-1', 'replace')

# --- 5. INTERFACE ---
logo_url = "https://github.com/deyvidbo/ohio-school-advocate/blob/main/Class_action_Logo.jpg?raw=true"
st.markdown("<center>", unsafe_allow_html=True)
try: st.image(logo_url, width=320)
except: st.title("⚖️ CLASS ACTION: OHIO")
st.markdown("</center>", unsafe_allow_html=True)

zip_input = st.text_input("Enter Ohio Zip Code:", max_chars=5)

if zip_input:
    res = df[df['zip_code'] == zip_input]
    if not res.empty:
        data = res.iloc[0].to_dict()
        
        st.header("1. Personalize Your Identity")
        c1, c2 = st.columns(2)
        with c1: st.session_state.u_name = st.text_input("Full Name:", value=st.session_state.u_name)
        with c2: st.session_state.u_role = st.text_input("Role:", value=st.session_state.u_role)

        r1, r2 = st.columns(2)
        with r1: st.session_state.years_ohio = st.number_input("Years in Ohio:", min_value=0, value=st.session_state.years_ohio)
        with r2: st.session_state.years_district = st.number_input(f"Years in Dist. {data['rep_district']}:", min_value=0, value=st.session_state.years_district)

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.session_state.is_voter = st.checkbox("Voter", value=st.session_state.is_voter)
            st.session_state.is_taxpayer = st.checkbox("Taxpayer", value=st.session_state.is_taxpayer)
        with b2:
            st.session_state.is_homeowner = st.checkbox("Homeowner", value=st.session_state.is_homeowner)
            st.session_state.is_renter = st.checkbox("Renter", value=st.session_state.is_renter)
        with b3:
            st.session_state.is_parent = st.checkbox("Parent", value=st.session_state.is_parent)
        with b4:
            if st.session_state.is_parent:
                st.session_state.child_count = st.number_input("Children:", min_value=1, value=max(1, st.session_state.child_count))

        st.header("2. Add Personal Perspective")
        st.session_state.custom_note = st.text_area("Custom Message:", value=st.session_state.custom_note)

        st.header("3. Advocacy Action Center")
        st.session_state.u_targets = st.multiselect("Select Targets for Print & Email:", ["📍 Local Rep", "🏛️ Governor", "🛡️ Friendly Caucus", "🚫 Opposition Leadership"], default=st.session_state.u_targets)

        # Map Recipients
        final_recs = []
        if "📍 Local Rep" in st.session_state.u_targets: final_recs.append({"name": data['rep_name'], "role": data['rep_role'], "email": data['rep_email'], "address": data['rep_address']})
        if "🏛️ Governor" in st.session_state.u_targets: final_recs.append({"name": "Mike DeWine", "role": "Governor", "email": "governor@ohio.gov", "address": "77 S. High St, 30th Floor, Columbus, OH 43215"})
        if "🛡️ Friendly Caucus" in st.session_state.u_targets: final_recs.append({"name": "C. Allison Russo", "role": "Minority Leader", "email": "rep07@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"})
        if "🚫 Opposition Leadership" in st.session_state.u_targets: final_recs.append({"name": "Matt Huffman", "role": "Speaker (Designate)", "email": "rep78@ohiohouse.gov", "address": "77 S. High St, 14th Floor, Columbus, OH 43215"})

        if st.session_state.u_name and final_recs:
            id_badges = {'voter': st.session_state.is_voter, 'taxpayer': st.session_state.is_taxpayer, 'homeowner': st.session_state.is_homeowner, 'renter': st.session_state.is_renter, 'parent': st.session_state.is_parent, 'count': st.session_state.child_count, 'y_ohio': st.session_state.years_ohio, 'y_dist': st.session_state.years_district}
            
            c_email, c_pdf = st.columns(2)
            
            with c_pdf:
                # 1. BULK PDF DOWNLOAD
                pdf_data = create_bulk_pdf(final_recs, {"name": st.session_state.u_name, "role": st.session_state.u_role, "zip": zip_input}, data, id_badges, st.session_state.custom_note)
                st.download_button(label=f"📄 DOWNLOAD {len(final_recs)} PRINT-READY LETTERS", data=pdf_data, file_name=f"Ohio_Advocacy_Pack.pdf", mime="application/pdf")

            with c_email:
                # 2. BCC EMAIL GENERATOR
                emails = [r['email'] for r in final_recs]
                bcc_string = ",".join(emails)
                subject = f"Constituent Advocacy: {data['school_district']} (District {data['rep_district']})"
                
                # Use a placeholder body for the mailto link (most browsers have char limits)
                email_body = f"Please find my attached advocacy regarding House District {data['rep_district']}."
                mailto_link = f"mailto:?bcc={bcc_string}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(email_body)}"
                
                st.markdown(f'''<a href="{mailto_link}" style="text-decoration:none;">
                    <div style="background-color:#B22234;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">✉️ BCC ALL REPRESENTATIVES</div></a>''', unsafe_allow_html=True)
                st.caption(f"BCC Targets: {', '.join(emails)}")

            if st.button("✅ Log All Actions (+100 XP per Target)"):
                st.session_state.xp_points += (100 * len(final_recs))
                st.balloons(); st.rerun()
