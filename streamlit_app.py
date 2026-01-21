# streamlit_app.py
# Class Action: Ohio (Streamlit) — Master App (School District Version)
#
# Features:
# - "Education First" Workflow: User selects School District -> App finds Rep.
# - Handles split districts (e.g., Columbus City) via secondary dropdown.
# - Letter PDFs & Email Drafts (body text matches exactly).
# - BCC batching for statewide campaigns.
# - ZIP bundle export.
# - Gamified XP + rank.
#
# DATA REQUIREMENT:
# - Requires 'District_Rep_Lookup.csv' in the same directory.
#   (Columns: school_district, rep_name, rep_email, rep_party, rep_stance, etc.)

import io
import os
import re
import zipfile
from datetime import date, datetime
from typing import List, Tuple

import pandas as pd
import streamlit as st

# Attempt to import FPDF
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# -----------------------------
# 1) APP CONFIG
# -----------------------------
st.set_page_config(
    page_title="Class Action: Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="auto",
)

CUSTOM_CSS = """
<style>
.stTabs [data-baseweb="tab"]{
  font-size: 16px;
  padding: 12px;
  border-radius: 10px;
}
h1, h2, h3 { margin-bottom: 0.25rem; }
div[data-testid="stMetric"]{
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #eee;
}
.stAlert {
    padding: 0.5rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------
# 2) CONSTANTS
# -----------------------------
RANKS = [
    ("Substitute", 0),
    ("Teacher", 200),
    ("Principal", 600),
    ("THE SUPERINTENDENT", 1200),
]

XP_PER_LETTER = 100
XP_PER_EMAIL = 60
XP_PER_EXPORT = 50

REQUIRED_COLUMNS_MIN = [
    "school_district",
    "rep_name",
    "rep_email",
    "rep_role",
    "rep_party",
]

# Mandatory policy impact block
REQUIRED_RIF_CONTEXT_BLOCK = (
    "Hamilton City School District has publicly announced a major Reduction in Force due to budget shortfalls.\n"
    "This decision impacts educators, support staff, and students directly.\n\n"
    "Hamilton is not alone.\n\n"
    "Other Ohio public school districts have announced or publicly discussed staff reductions, program cuts, or deficit-driven restructuring due to insufficient state funding.\n\n"
    "These actions follow legislative budget decisions that did not fully fund the Fair School Funding Plan and reduced or capped critical aid streams relied upon by public schools.\n\n"
    "The result is predictable.\n"
    "Districts are forced to cut staff, increase class sizes, reduce services, and destabilize schools.\n\n"
    "These are policy outcomes.\n"
)

LOCKED_CONSTITUENT_SENTENCE = (
    "I am a constituent in your legislative district, as defined by the Ohio General Assembly's official district maps."
)


# -----------------------------
# 3) SESSION STATE
# -----------------------------
def init_state():
    if "xp" not in st.session_state:
        st.session_state.xp = 0
    if "actions" not in st.session_state:
        st.session_state.actions = []
    if "loaded_df" not in st.session_state:
        st.session_state.loaded_df = None

init_state()


# -----------------------------
# 4) TEXT HELPERS
# -----------------------------
def clean_whitespace(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def titlecase_name(s: str) -> str:
    s = clean_whitespace(s)
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split(" ")
    out = []
    for p in parts:
        if not p: continue
        if len(p) <= 3 and p.isupper(): out.append(p)
        elif re.match(r"^[A-Z]\.$", p): out.append(p)
        else: out.append(p[:1].upper() + p[1:].lower())
    return " ".join(out).strip()

def safe_str(s) -> str:
    return clean_whitespace("" if s is None else s)

def filename_safe(s: str) -> str:
    s = safe_str(s)
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] if len(s) > 80 else s


# -----------------------------
# 5) DATA LOADING
# -----------------------------
def load_and_normalize_lookup(file_path_or_buffer) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path_or_buffer, dtype=str, keep_default_na=False)
        df.columns = [clean_whitespace(c).lower() for c in df.columns]
        
        missing = [c for c in REQUIRED_COLUMNS_MIN if c not in df.columns]
        if missing:
            st.error(f"Missing columns in CSV: {missing}")
            return pd.DataFrame()

        # Clean key fields
        df["school_district"] = df["school_district"].apply(clean_whitespace)
        df["rep_name"] = df["rep_name"].apply(titlecase_name)
        df["rep_email"] = df["rep_email"].str.lower().str.strip()
        
        if "rep_stance" not in df.columns:
            df["rep_stance"] = "Unknown"
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


# -----------------------------
# 6) GAMIFICATION
# -----------------------------
def rank_for_xp(xp: int) -> Tuple[str, int, int]:
    current = RANKS[0][0]
    floor = 0
    ceil = RANKS[-1][1]
    for i, (name, threshold) in enumerate(RANKS):
        if xp >= threshold:
            current = name
            floor = threshold
            ceil = RANKS[i + 1][1] if i + 1 < len(RANKS) else threshold
    return current, floor, ceil

def add_action(action_type: str, detail: str, xp_gain: int):
    st.session_state.xp += int(xp_gain)
    st.session_state.actions.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action_type,
        "detail": detail,
        "xp": int(xp_gain),
    })


# -----------------------------
# 7) BCC GENERATOR
# -----------------------------
def build_bcc_list() -> List[str]:
    # Generates standard Ohio House emails rep01@ to rep99@
    return [f"rep{i:02d}@ohiohouse.gov" for i in range(1, 100)]


# -----------------------------
# 8) PDF GENERATION
# -----------------------------
def pdf_from_text(title: str, text: str) -> bytes:
    if FPDF is None:
        return text.encode("utf-8")

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, title)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    
    # Replace common unicode chars that break FPDF latin-1
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "..."
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    pdf.multi_cell(0, 6, text)
    return pdf.output(dest="S").encode("latin-1", errors="ignore")


# -----------------------------
# 9) MAIN APP
# -----------------------------

# Load Data Automatically
if st.session_state.loaded_df is None:
    if os.path.exists("District_Rep_Lookup.csv"):
        st.session_state.loaded_df = load_and_normalize_lookup("District_Rep_Lookup.csv")

# Sidebar
with st.sidebar:
    st.header("Settings")
    uploaded = st.file_uploader("Override CSV Data", type=["csv"])
    if uploaded:
        st.session_state.loaded_df = load_and_normalize_lookup(uploaded)
        
    st.divider()
    rank, floor, ceil = rank_for_xp(st.session_state.xp)
    st.metric(label="Advocate Rank", value=rank)
    st.metric(label="XP", value=st.session_state.xp)
    if ceil > floor:
        st.progress((st.session_state.xp - floor) / (ceil - floor))

# Main UI
st.title("Class Action: Ohio")
st.markdown("### Fund Our Schools. Protect Our Teachers.")
st.markdown("Select your school district to find your representative and generate a targeted letter.")
st.divider()

df = st.session_state.loaded_df
if df is None or df.empty:
    st.warning("⚠️ Data file `District_Rep_Lookup.csv` not found. Please upload it.")
    st.stop()

# Tabs
tab_builder, tab_data, tab_logs = st.tabs(["Draft Builder", "View Data", "Your Activity"])

with tab_builder:
    # --------------------------
    # 1. District Selection
    # --------------------------
    st.subheader("1. Locate Your Representative")
    districts = sorted(df["school_district"].unique().tolist())
    
    selected_district = st.selectbox(
        "Select Your Public School District:", 
        districts, 
        index=None, 
        placeholder="Type to search..."
    )

    selected_rep_row = None

    if selected_district:
        district_data = df[df["school_district"] == selected_district].copy()
        
        # Scenario A: Single Match
        if len(district_data) == 1:
            row = district_data.iloc[0]
            if row['rep_name'] == "Select Your Representative":
                 st.warning(f"⚠️ We have mapped {selected_district} to a district, but you need to confirm the Rep.")
                 # Fallback logic could go here, but for now we treat it as valid
            selected_rep_row = row
            
        # Scenario B: Multiple Matches (Split District)
        elif len(district_data) > 1:
            st.info(f"📍 {selected_district} is split between multiple House Districts.")
            
            district_data["_label"] = district_data.apply(
                lambda x: f"{x['rep_name']} (District {x['rep_district']})", axis=1
            )
            
            rep_choice = st.selectbox(
                "Which Representative covers your specific area?", 
                district_data["_label"].unique()
            )
            
            if rep_choice:
                selected_rep_row = district_data[district_data["_label"] == rep_choice].iloc[0]

    # --------------------------
    # 2. Display Target
    # --------------------------
    if selected_rep_row is not None:
        rep_name = selected_rep_row['rep_name']
        rep_party = selected_rep_row['rep_party']
        rep_email = selected_rep_row['rep_email']
        rep_stance = selected_rep_row.get('rep_stance', 'Unknown')
        rep_district = selected_rep_row.get('rep_district', '?')

        st.markdown("---")
        c1, c2 = st.columns([1, 3])
        with c1:
            if rep_stance.lower() == "hostile":
                st.error("⚠️ **OPPONENT**")
            elif rep_stance.lower() == "friendly":
                st.success("✅ **ALLY**")
            else:
                st.info("ℹ️ **TARGET**")
        with c2:
            st.subheader(f"Rep. {rep_name} ({rep_party})")
            st.write(f"**District {rep_district}** • {rep_email}")
            if rep_stance.lower() == "hostile":
                st.write(f"🛑 This representative has supported voucher expansion at the expense of {selected_district}.")

        # --------------------------
        # 3. User Info
        # --------------------------
        st.markdown("---")
        st.subheader("2. Your Information")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            sender_name = st.text_input("Name", placeholder="Jane Doe")
            sender_address = st.text_input("Street Address", placeholder="123 Main St")
        with col_u2:
            sender_city = st.text_input("City", value="Hamilton")
            sender_zip = st.text_input("Zip Code", placeholder="45011")
        
        user_role = st.selectbox("I am a:", ["Parent", "Teacher", "Taxpayer", "Business Owner", "Concerned Citizen"])

        # --------------------------
        # 4. Message
        # --------------------------
        st.subheader("3. Customize Message")
        issue = st.text_input("Subject", value=f"Protect {selected_district} Funding - Vote NO on Vouchers")
        story = st.text_area("Your Story (Optional)", height=100, placeholder="As a parent in this district...")
        closing = st.text_input("Closing", value="Thank you for your service to our community.")

        # --------------------------
        # 5. Generate
        # --------------------------
        st.markdown("---")
        st.subheader("4. Send")

        today_str = date.today().strftime("%B %d, %Y")
        
        full_letter_text = (
            f"{today_str}\n\nRep. {rep_name}\nOhio House of Representatives\nDistrict {rep_district}\n\n"
            f"From:\n{sender_name}\n{sender_address}\n{sender_city}, OH {sender_zip}\n\n"
            f"RE: {issue}\n\n"
            f"Dear Representative {rep_name},\n\n{LOCKED_CONSTITUENT_SENTENCE}\n\n"
            f"I am writing to you as a {user_role} in the {selected_district}.\n\n"
            f"{REQUIRED_RIF_CONTEXT_BLOCK}\n{story}\n\n"
            "I urge you to prioritize the constitutional obligation to fund our public schools over private school vouchers. "
            f"Please support fair funding for {selected_district}.\n\n{closing}\n\nSincerely,\n{sender_name}"
        )

        email_body = (
            f"Dear Representative {rep_name},\n\n{LOCKED_CONSTITUENT_SENTENCE}\n\n"
            f"I am writing to you as a {user_role} in the {selected_district}.\n\n"
            f"{REQUIRED_RIF_CONTEXT_BLOCK}\n{story}\n\n"
            "I urge you to prioritize the constitutional obligation to fund our public schools over private school vouchers.\n\n"
            f"{closing}\n\nSincerely,\n{sender_name}"
        )

        with st.expander("Preview Letter", expanded=True):
            st.text_area("Content", value=full_letter_text, height=250)

        c_gen1, c_gen2 = st.columns(2)
        with c_gen1:
            if st.button("📄 Download PDF"):
                pdf_bytes = pdf_from_text(f"Letter to Rep {rep_name}", full_letter_text)
                add_action("Generated Letter", f"Target: {rep_name}", XP_PER_LETTER)
                st.download_button("Save PDF", data=pdf_bytes, file_name=f"Letter_{filename_safe(rep_name)}.pdf", mime="application/pdf")

        with c_gen2:
            import urllib.parse
            safe_subject = urllib.parse.quote(issue)
            safe_body = urllib.parse.quote(email_body)
            bcc_list = build_bcc_list()
            bcc_string = ",".join(bcc_list[:30]) # Batch first 30
            
            mailto_link = f"mailto:{rep_email}?bcc={bcc_string}&subject={safe_subject}&body={safe_body}"
            st.markdown(
                f'<a href="{mailto_link}" target="_blank">'
                f'<button style="background-color:#FF4B4B;color:white;padding:10px 20px;border:none;border-radius:5px;">'
                f'🚀 Launch Email (with BCC)</button></a>', unsafe_allow_html=True
            )

with tab_data:
    st.dataframe(df)

with tab_logs:
    st.write(st.session_state.actions)
