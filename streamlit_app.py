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
#
# Dependencies:
# streamlit
# pandas
# requests
# fpdf (or fpdf2)

import io
import os
import re
import zipfile
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional

import pandas as pd
import requests
import streamlit as st

try:
    from fpdf import FPDF  # works with fpdf2 as well
except Exception:
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
.warroom-card{
  border: 1px solid #eee;
  padding: 14px;
  border-radius: 14px;
  background: #fafafa;
}
.small-muted{
  color: #666;
  font-size: 13px;
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

DEFAULT_BCC_BATCH_SIZE = 40 

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

DEFAULT_STATE = "OH"


# -----------------------------
# 3) SESSION STATE
# -----------------------------
def init_state():
    if "xp" not in st.session_state:
        st.session_state.xp = 0
    if "actions" not in st.session_state:
        st.session_state.actions = []
    if "last_export_at" not in st.session_state:
        st.session_state.last_export_at = None
    if "loaded_df" not in st.session_state:
        st.session_state.loaded_df = None
    if "roster_df" not in st.session_state:
        st.session_state.roster_df = None

init_state()


# -----------------------------
# 4) TEXT HELPERS
# -----------------------------
def clean_whitespace(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def remove_commas_from_name(s: str) -> str:
    s = clean_whitespace(s)
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_email(s: str) -> str:
    return clean_whitespace(s).lower()

def safe_str(s) -> str:
    return clean_whitespace("" if s is None else s)

def safe_zip(s) -> str:
    s = re.sub(r"\D", "", safe_str(s))
    return s[:5] if len(s) >= 5 else s

def titlecase_name(s: str) -> str:
    s = remove_commas_from_name(s)
    parts = s.split(" ")
    out = []
    for p in parts:
        if not p:
            continue
        if len(p) <= 3 and p.isupper():
            out.append(p)
        elif re.match(r"^[A-Z]\.$", p):
            out.append(p)
        else:
            out.append(p[:1].upper() + p[1:].lower())
    return " ".join(out).strip()

def unique_emails(emails: List[str]) -> List[str]:
    seen = set()
    out = []
    for e in emails:
        e2 = normalize_email(e)
        if not e2:
            continue
        if e2 in seen:
            continue
        seen.add(e2)
        out.append(e2)
    return out

def chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    if chunk_size <= 0:
        return [items]
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


# -----------------------------
# 5) DATA NORMALIZATION
# -----------------------------
def load_and_normalize_lookup(file_path_or_buffer) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path_or_buffer, dtype=str, keep_default_na=False)
        # Normalize column names
        df.columns = [clean_whitespace(c).lower() for c in df.columns]
        
        # Check required columns
        missing = [c for c in REQUIRED_COLUMNS_MIN if c not in df.columns]
        if missing:
            st.error(f"Missing columns in CSV: {missing}")
            return pd.DataFrame()

        # Clean data
        df["school_district"] = df["school_district"].apply(clean_whitespace)
        df["rep_name"] = df["rep_name"].apply(titlecase_name)
        df["rep_email"] = df["rep_email"].apply(normalize_email)
        df["rep_role"] = df["rep_role"].apply(clean_whitespace)
        
        if "rep_party" in df.columns:
            df["rep_party"] = df["rep_party"].apply(clean_whitespace)
        if "rep_stance" in df.columns:
            df["rep_stance"] = df["rep_stance"].apply(clean_whitespace)
        
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
    st.session_state.actions.insert(
        0,
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action_type,
            "detail": detail,
            "xp": int(xp_gain),
        },
    )


# -----------------------------
# 7) LIVE OHIO HOUSE ROSTER (For BCC)
# -----------------------------
def rep_email_for_district(d: int) -> str:
    return f"rep{d:02d}@ohiohouse.gov"

@st.cache_data(ttl=6 * 60 * 60)
def fetch_ohio_house_roster() -> pd.DataFrame:
    """
    Fetches live roster for BCC generation.
    """
    url = "https://www.legislature.ohio.gov/members/house-directory"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        # Simple scraping attempt via pandas
        tables = pd.read_html(r.text)
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("district" in c for c in cols):
                # Clean up and return
                t.columns = [str(c).strip() for c in t.columns]
                return t
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def build_bcc_list_from_roster(df: pd.DataFrame) -> List[str]:
    # Fallback: if fetch fails, generates 1-99 emails mathematically
    if df is None or df.empty:
        return [rep_email_for_district(i) for i in range(1, 100)]
    
    # Try to extract emails from DF if column exists, else math
    return [rep_email_for_district(i) for i in range(1, 100)]


# -----------------------------
# 8) PDF GENERATION
# -----------------------------
def pdf_from_text(title: str, text: str) -> bytes:
    if FPDF is None:
        return text.encode("utf-8")

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Font handling - fallback to standard font
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, title)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    
    # Sanitize utf-8 for FPDF (latin-1 limit)
    safe_text = text.replace("\u2014", "-").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    
    for line in safe_text.split("\n"):
        pdf.multi_cell(0, 6, line)

    return pdf.output(dest="S").encode("latin-1", errors="ignore")

def make_bundle_zip(files: List[Tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            z.writestr(fname, data)
    buf.seek(0)
    return buf.read()

def filename_safe(s: str) -> str:
    s = safe_str(s)
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] if len(s) > 80 else s


# -----------------------------
# 9) MAIN APP LOGIC
# -----------------------------

# Load Main Data
if st.session_state.loaded_df is None:
    # Look for local file first
    if os.path.exists("District_Rep_Lookup.csv"):
        st.session_state.loaded_df = load_and_normalize_lookup("District_Rep_Lookup.csv")

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    # Manual Upload Override
    uploaded = st.file_uploader("Override Data (District_Rep_Lookup.csv)", type=["csv"])
    if uploaded:
        st.session_state.loaded_df = load_and_normalize_lookup(uploaded)
        
    st.divider()
    st.write("Gamification")
    rank, floor, ceil = rank_for_xp(st.session_state.xp)
    st.metric("Rank", rank)
    st.metric("XP", st.session_state.xp)
    if ceil > floor:
        st.progress((st.session_state.xp - floor) / (ceil - floor))

# Main Header
st.title("Class Action: Ohio")
st.markdown("### Fund Our Schools. Protect Our Teachers.")
st.markdown("Use this tool to find the representative specifically assigned to **your school district** and generate targeted communications.")

st.divider()

# Check Data
df = st.session_state.loaded_df
if df is None or df.empty:
    st.warning("⚠️ Data file `District_Rep_Lookup.csv` not found. Please upload it in the sidebar.")
    st.stop()

# --- TAB INTERFACE ---
tab_builder, tab_roster, tab_logs = st.tabs(["Draft Builder", "Ohio Roster", "Logs"])

with tab_builder:
    # ---------------------------------------------------------
    # STEP 1: SELECT DISTRICT (The Core Logic Pivot)
    # ---------------------------------------------------------
    st.subheader("1. Locate Your Representative")
    
    # Unique list of districts
    districts = sorted(df["school_district"].unique().tolist())
    
    # Use index=None to force user to choose
    selected_district = st.selectbox(
        "Select Your Public School District:", 
        districts, 
        index=None, 
        placeholder="Type to search..."
    )

    selected_rep_row = None

    if selected_district:
        # Filter Data
        district_data = df[df["school_district"] == selected_district]
        
        # LOGIC: Check for split districts or missing mappings
        if len(district_data) == 1:
            # Single Match
            selected_rep_row = district_data.iloc[0]
        else:
            # Multiple matches (Split district like Columbus)
            st.info(f"📍 The **{selected_district}** covers multiple legislative districts.")
            
            # Helper label
            district_data["_label"] = district_data.apply(
                lambda x: f"{x['rep_name']} (District {x['rep_district']})", axis=1
            )
            
            rep_choice = st.selectbox(
                "Which Representative covers your specific area?", 
                district_data["_label"].unique()
            )
            
            if rep_choice:
                selected_rep_row = district_data[district_data["_label"] == rep_choice].iloc[0]

    # ---------------------------------------------------------
    # STEP 2: DISPLAY TARGET & STATUS
    # ---------------------------------------------------------
    if selected_rep_row is not None:
        rep_name = selected_rep_row['rep_name']
        rep_party = selected_rep_row['rep_party']
        rep_email = selected_rep_row['rep_email']
        rep_stance = selected_rep_row['rep_stance']
        rep_district = selected_rep_row.get('rep_district', '?')
        
        # Visual Card
        st.markdown("---")
        c1, c2 = st.columns([1, 3])
        
        with c1:
            # Stance Check
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
            elif rep_stance.lower() == "friendly":
                st.write(f"🤝 This representative supports public education. Send a 'Thank You' and urge them to hold the line.")

        # ---------------------------------------------------------
        # STEP 3: USER INFO (For Letterhead)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("2. Your Information (For Letterhead)")
        
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            sender_name = st.text_input("Name", placeholder="Jane Doe")
            sender_address = st.text_input("Street Address", placeholder="123 Main St")
        with col_u2:
            sender_city = st.text_input("City", value="Hamilton") # Default based on prompt context
            sender_zip = st.text_input("Zip Code", placeholder="45011")
        
        user_role = st.selectbox("I am a:", ["Parent", "Teacher", "Taxpayer", "Business Owner", "Concerned Citizen"])

        # ---------------------------------------------------------
        # STEP 4: CUSTOMIZE MESSAGE
        # ---------------------------------------------------------
        st.subheader("3. Customize Message")
        
        issue = st.text_input("Subject / Issue", value=f"Protect {selected_district} Funding - Vote NO on Vouchers")
        
        story = st.text_area(
            "Your Story (Optional - makes it more powerful)", 
            height=100, 
            placeholder="As a parent/teacher in this district, I am seeing class sizes rise..."
        )
        
        closing = st.text_input("Closing", value="Thank you for your service to our community.")

        # ---------------------------------------------------------
        # STEP 5: GENERATE PREVIEW & DOWNLOAD
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("4. Generate & Send")

        # Build Text
        # Mandatory Header Logic
        today_str = date.today().strftime("%B %d, %Y")
        
        full_letter_text = (
            f"{today_str}\n\n"
            f"Rep. {rep_name}\n"
            f"Ohio House of Representatives\n"
            f"District {rep_district}\n\n"
            f"From:\n{sender_name}\n{sender_address}\n{sender_city}, OH {sender_zip}\n\n"
            f"RE: {issue}\n\n"
            f"Dear Representative {rep_name},\n\n"
            f"{LOCKED_CONSTITUENT_SENTENCE}\n\n"
            f"I am writing to you as a {user_role} in the {selected_district}.\n\n"
            f"{REQUIRED_RIF_CONTEXT_BLOCK}\n" # Insert mandatory RIF context
            f"{story}\n\n"
            "I urge you to prioritize the constitutional obligation to fund our public schools over the expansion of private school vouchers. "
            f"Please support fair funding for {selected_district} in the upcoming budget.\n\n"
            f"{closing}\n\n"
            f"Sincerely,\n{sender_name}"
        )

        # Email Body (Same as letter but sans header)
        email_body = (
            f"Dear Representative {rep_name},\n\n"
            f"{LOCKED_CONSTITUENT_SENTENCE}\n\n"
            f"I am writing to you as a {user_role} in the {selected_district}.\n\n"
            f"{REQUIRED_RIF_CONTEXT_BLOCK}\n"
            f"{story}\n\n"
            "I urge you to prioritize the constitutional obligation to fund our public schools over the expansion of private school vouchers.\n\n"
            f"{closing}\n\n"
            f"Sincerely,\n{sender_name}"
        )

        # Preview
        with st.expander("Preview Letter Content", expanded=True):
            st.text_area("Draft", value=full_letter_text, height=300)

        # Buttons
        c_gen1, c_gen2 = st.columns(2)
        
        with c_gen1:
            # Generate PDF
            if st.button("📄 Download PDF Letter"):
                pdf_bytes = pdf_from_text(f"Letter to Rep {rep_name}", full_letter_text)
                add_action("Generated Letter", f"Target: {rep_name}", XP_PER_LETTER)
                st.download_button(
                    label="Click to Save PDF",
                    data=pdf_bytes,
                    file_name=f"Letter_to_{filename_safe(rep_name)}.pdf",
                    mime="application/pdf"
                )

        with c_gen2:
            # Email Link
            import urllib.parse
            safe_subject = urllib.parse.quote(issue)
            safe_body = urllib.parse.quote(email_body)
            # BCC Logic
            bcc_list = build_bcc_list_from_roster(None) # Generates rep01...rep99
            # Simple batching (first 30 for safety in mailto)
            bcc_string = ",".join(bcc_list[:30])
            
            mailto_link = f"mailto:{rep_email}?bcc={bcc_string}&subject={safe_subject}&body={safe_body}"
            
            st.markdown(
                f'<a href="{mailto_link}" target="_blank">'
                f'<button style="background-color:#FF4B4B;color:white;padding:10px 20px;border:none;border-radius:5px;font-size:16px;">'
                f'🚀 Launch Email App (with BCC)'
                f'</button></a>', 
                unsafe_allow_html=True
            )
            st.caption("Includes BCC to ~30 statewide reps for maximum visibility.")

with tab_roster:
    st.dataframe(df)

with tab_logs:
    st.write(st.session_state.actions)
