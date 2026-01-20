import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date

# =========================================================
# 1. APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="auto"
)

# =========================================================
# 2. SAFE CSS
# =========================================================
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    padding: 12px;
    flex-grow: 1;
    text-align: center;
    background-color: #f8f9fa;
    border-radius: 8px;
}
.stTabs [aria-selected="true"] {
    background-color: #e2e8f0;
    font-weight: bold;
}
.deploy-btn {
    display: block;
    width: 100%;
    padding: 18px;
    background-color: #B22234;
    color: white !important;
    text-align: center;
    border-radius: 12px;
    font-weight: bold;
    font-size: 1.1em;
    margin-bottom: 12px;
    text-decoration: none;
}
.status-banner {
    padding: 12px;
    background-color: #ecfdf5;
    border: 1px solid #10b981;
    color: #065f46;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
    margin-bottom: 15px;
}
.rank-card {
    background-color: #1e3a8a;
    color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    border: 2px solid #facc15;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
st.session_state.setdefault("xp_points", 0)

# =========================================================
# 4. BACKUP DATA (FAILSAFE)
# =========================================================
BACKUP_DATA = {
    "45011": [{
        "rep_name": "Diane Mullins",
        "rep_district": "47",
        "rep_email": "rep47@ohiohouse.gov",
        "rep_role": "Representative",
        "rep_address": "77 S High St, Columbus, OH 43215",
        "school_district": "Hamilton City Schools",
        "enrollment": "8900"
    }]
}

# =========================================================
# 5. CSV LOADER (CRASH-PROOF)
# =========================================================
@st.cache_data
def get_reps_for_zip(zip_code: str):
    zip_code = "".join(c for c in zip_code if c.isdigit())[:5]
    if len(zip_code) != 5:
        return []

    try:
        df = pd.read_csv(
            "ohio_districts_clean.csv",
            dtype=str,
            engine="python",
            keep_default_na=False,
            on_bad_lines="skip"
        )

        df["rep_name"] = df["rep_name"].str.replace(",", "", regex=False)

        matches = df[df["zip_code"] == zip_code]
        if matches.empty:
            return BACKUP_DATA.get(zip_code, [])

        records = matches.to_dict("records")
        for r in records:
            r["display_label"] = f"Rep. {r['rep_name']} (District {r['rep_district']})"
            r["rep_address"] = r.get("rep_address", "77 S High St, Columbus, OH 43215")
        return records

    except Exception:
        return BACKUP_DATA.get(zip_code, [])

# =========================================================
# 6. CANONICAL LETTER TEXT (SINGLE SOURCE OF TRUTH)
# =========================================================
def build_letter_text(user, rep_data, custom_text, badges):
    identity = []
    if badges["voter"]: identity.append("voter")
    if badges["taxpayer"]: identity.append("taxpayer")
    if badges["homeowner"]: identity.append("homeowner")
    identity_text = ", ".join(identity) if identity else "resident"

    years = f" Having lived in Ohio for {badges['years']} years," if badges["years"] else ""

    letter = (
        f"My name is {user['name']}. I live in {rep_data['school_district']} "
        f"(House District {rep_data['rep_district']}). "
        f"As a {identity_text},{years} I am writing to express serious concern "
        f"about the condition of public education in our community.\n\n"
        f"Our district serves approximately {rep_data['enrollment']} students. "
        f"{custom_text}\n\n"
        "I respectfully urge you to prioritize stable and sufficient funding "
        "for Ohio’s public schools and to protect the educators and students "
        "who depend on them."
    )
    return letter

# =========================================================
# 7. PDF GENERATOR (USES SAME LETTER TEXT)
# =========================================================
def generate_pdf(user, rep, letter_text):
    pdf = FPDF()
    pdf.set_margins(1, 1, 1)
    pdf.add_page()
    pdf.set_font("Times", "", 12)

    pdf.cell(0, 0.2, user["name"], ln=True)
    pdf.cell(0, 0.2, user["role"], ln=True)
    pdf.cell(0, 0.2, f"Zip Code: {user['zip']}", ln=True)
    pdf.ln(0.2)
    pdf.cell(0, 0.2, date.today().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.3)

    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 0.2, f"{rep['rep_role']} {rep['rep_name']}", ln=True)
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(0, 0.2, rep["rep_address"])
    pdf.ln(0.3)

    pdf.cell(0, 0.2, f"Dear {rep['rep_role']} {rep['rep_name'].split()[-1]}:", ln=True)
    pdf.ln(0.3)

    pdf.multi_cell(0, 0.2, letter_text)
    pdf.ln(0.4)
    pdf.cell(0, 0.2, "Sincerely,", ln=True)
    pdf.ln(0.8)
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 0.2, user["name"], ln=True)

    return pdf.output(dest="S").encode("latin-1")

# =========================================================
# 8. UI
# =========================================================
st.markdown("## ⚖️ Class Action: Ohio")

with st.sidebar:
    rank = "Substitute" if st.session_state.xp_points < 100 else "Teacher"
    st.markdown(
        f"<div class='rank-card'><h2>{st.session_state.xp_points} XP</h2><p>Rank: {rank}</p></div>",
        unsafe_allow_html=True
    )

zip_input = st.text_input("Enter ZIP Code", max_chars=5)

if zip_input:
    reps = get_reps_for_zip(zip_input)

    if not reps:
        st.error("No representatives found for that ZIP.")
    else:
        choice = st.selectbox("Select Representative", [r["display_label"] for r in reps])
        rep = next(r for r in reps if r["display_label"] == choice)

        st.markdown(
            f"<div class='status-banner'>Assigned School District:<br>{rep['school_district']}</div>",
            unsafe_allow_html=True
        )

        t_you, t_msg, t_go = st.tabs(["👤 YOU", "📝 MESSAGE", "🚀 DEPLOY"])

        with t_you:
            st.text_input("Full Name", key="u_name")
            st.text_input("Title / Role", key="u_role")
            st.checkbox("Voter", key="is_voter")
            st.checkbox("Taxpayer", key="is_taxpayer")
            st.checkbox("Homeowner", key="is_homeowner")
            st.number_input("Years in Ohio", min_value=0, key="years_ohio")

        with t_msg:
            st.text_area("Your Message", key="custom_note", height=140)

        with t_go:
            if st.session_state.u_name:
                user = {
                    "name": st.session_state.u_name,
                    "role": st.session_state.u_role,
                    "zip": zip_input
                }

                badges = {
                    "voter": st.session_state.is_voter,
                    "taxpayer": st.session_state.is_taxpayer,
                    "homeowner": st.session_state.is_homeowner,
                    "years": st.session_state.years_ohio
                }

                letter_text = build_letter_text(
                    user, rep, st.session_state.custom_note, badges
                )

                # EMAIL (uses SAME letter text)
                subject = urllib.parse.quote(
                    f"Public Schools in {rep['school_district']}"
                )
                body = urllib.parse.quote(letter_text)
                st.markdown(
                    f"<a href='mailto:{rep['rep_email']}?subject={subject}&body={body}' class='deploy-btn'>✉️ SEND EMAIL</a>",
                    unsafe_allow_html=True
                )

                # PDF (uses SAME letter text)
                pdf_bytes = generate_pdf(user, rep, letter_text)
                st.download_button("📄 DOWNLOAD PDF LETTER", pdf_bytes, "Advocacy_Letter.pdf")

                if st.button("✅ EARN XP"):
                    st.session_state.xp_points += 100
                    st.rerun()
            else:
                st.info("Enter your name to continue.")
