# streamlit_app.py
# Class Action: Ohio (Streamlit)
# Single-file master app:
# - CSV upload + cleaning
# - No KeyError on display_label
# - Removes commas from names
# - Live Ohio House roster fetch (used for statewide BCC list)
# - Letter PDFs
# - Email Draft PDFs where body text matches the Letter PDF text exactly
# - BCC batching into multiple email drafts (respects common recipient caps)
# - ZIP export
# - Gamified XP + rank

import io
import re
import zipfile
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional

import pandas as pd
import requests
import streamlit as st

try:
    from fpdf import FPDF
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

DEFAULT_BCC_BATCH_SIZE = 40  # conservative default

REQUIRED_COLUMNS_MIN = [
    "zip_code",
    "school_district",
    "rep_name",
    "rep_email",
    "rep_role",
    "rep_district",
    "rep_party",
]


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


def coerce_percent_like(val) -> str:
    s = safe_str(val)
    if not s:
        return ""
    if "%" in s:
        return s
    try:
        f = float(s)
        if 0 <= f <= 1:
            return f"{int(round(f * 100))}%"
        if 1 < f <= 100:
            return f"{int(round(f))}%"
    except Exception:
        pass
    return s


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
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_whitespace(c).lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS_MIN if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    df["zip_code"] = df["zip_code"].apply(safe_zip)
    df["school_district"] = df["school_district"].apply(clean_whitespace)

    df["rep_name"] = df["rep_name"].apply(titlecase_name)
    df["rep_email"] = df["rep_email"].apply(normalize_email)
    df["rep_role"] = df["rep_role"].apply(clean_whitespace)
    df["rep_district"] = df["rep_district"].apply(lambda x: clean_whitespace(str(x)))
    df["rep_party"] = df["rep_party"].apply(clean_whitespace)

    if "rep_stance" in df.columns:
        df["rep_stance"] = df["rep_stance"].apply(clean_whitespace)
    else:
        df["rep_stance"] = ""

    if "rep_career" in df.columns:
        df["rep_career"] = df["rep_career"].apply(clean_whitespace)
    else:
        df["rep_career"] = ""

    if "rep_address" in df.columns:
        df["rep_address"] = df["rep_address"].apply(clean_whitespace)
    else:
        df["rep_address"] = ""

    for col in ["enrollment", "poverty_rate", "minority_rate"]:
        if col not in df.columns:
            df[col] = ""
        else:
            if col.endswith("_rate"):
                df[col] = df[col].apply(coerce_percent_like)
            else:
                df[col] = df[col].apply(lambda x: clean_whitespace(str(x)))

    df = df[df["zip_code"].astype(str).str.len() > 0].copy()

    df["_dedup_key"] = (
        df["zip_code"].astype(str)
        + "|"
        + df["rep_email"].astype(str)
        + "|"
        + df["rep_role"].astype(str)
    )
    df = df.drop_duplicates(subset=["_dedup_key"]).drop(columns=["_dedup_key"])

    return df


def build_display_label(r: Dict) -> str:
    name = safe_str(r.get("rep_name") or r.get("name") or "")
    role = safe_str(r.get("rep_role") or r.get("role") or "")
    dist = safe_str(r.get("rep_district") or r.get("district") or "")
    party = safe_str(r.get("rep_party") or r.get("party") or "")
    stance = safe_str(r.get("rep_stance") or "")
    email = safe_str(r.get("rep_email") or r.get("email") or "")

    meta_bits = []
    if party:
        meta_bits.append(party)
    if dist:
        meta_bits.append(f"Dist {dist}")
    if role:
        meta_bits.append(role)
    if stance:
        meta_bits.append(stance)

    meta = " | ".join(meta_bits).strip()
    label = name if name else "Unknown Representative"
    if meta:
        label = f"{label} ({meta})"
    if email:
        label = f"{label} — {email}"
    return label


def reps_from_df(df: pd.DataFrame, zip_code: str, district: str) -> List[Dict]:
    sub = df.copy()
    if zip_code:
        sub = sub[sub["zip_code"] == zip_code]
    if district:
        sub = sub[sub["school_district"] == district]

    reps = sub.to_dict(orient="records")
    normalized = []
    for r in reps:
        if not isinstance(r, dict):
            try:
                r = dict(r)
            except Exception:
                r = {"_raw": str(r)}
        r["display_label"] = safe_str(r.get("display_label")) or build_display_label(r)
        normalized.append(r)
    return normalized


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
# 7) LETTER + EMAIL TEXT (PDF SOURCE OF TRUTH)
# -----------------------------
def build_letter_text(
    sender_name: str,
    sender_city: str,
    sender_zip: str,
    rep_name: str,
    rep_role: str,
    rep_district: str,
    issue: str,
    story: str,
    ask_1: str,
    ask_2: str,
    ask_3: str,
    closing: str,
) -> str:
    today_str = date.today().strftime("%B %d, %Y")

    sender_name = remove_commas_from_name(sender_name)
    rep_name = remove_commas_from_name(rep_name)

    header = f"{today_str}\n\n{rep_name}\n{rep_role} — District {rep_district}\n"

    body = (
        f"Dear {rep_name},\n\n"
        f"My name is {sender_name}. I live in {sender_city}, Ohio {sender_zip}.\n\n"
        f"I am writing about: {clean_whitespace(issue)}\n\n"
    )

    if story.strip():
        body += f"My experience:\n{story.strip()}\n\n"

    body += "What I am asking you to do:\n"
    if ask_1.strip():
        body += f"1) {ask_1.strip()}\n"
    if ask_2.strip():
        body += f"2) {ask_2.strip()}\n"
    if ask_3.strip():
        body += f"3) {ask_3.strip()}\n"

    body += "\n"
    if closing.strip():
        body += f"{closing.strip()}\n\n"
    body += f"Respectfully,\n{sender_name}\n"

    return header + "\n" + body


def build_email_subject(issue: str) -> str:
    issue = clean_whitespace(issue)
    if not issue:
        return "Constituent message"
    return (issue[:72] + "...") if len(issue) > 72 else issue


def build_email_text_with_bcc(
    to_email: str,
    subject: str,
    bcc_emails: List[str],
    body_text_same_as_letter: str,
) -> str:
    to_email = normalize_email(to_email)
    subject = clean_whitespace(subject)
    bcc_line = ", ".join(bcc_emails) if bcc_emails else ""

    # Email Draft PDF text.
    # Body equals the Letter PDF text exactly.
    return "\n".join(
        [
            f"To: {to_email}",
            f"Subject: {subject}",
            (f"BCC: {bcc_line}" if bcc_line else "BCC:"),
            "",
            body_text_same_as_letter.strip(),
            "",
        ]
    )


# -----------------------------
# 8) PDF + ZIP
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

    safe_text = text.replace("\u2014", "-").replace("\u2019", "'")
    safe_text = safe_text.replace("\u201c", '"').replace("\u201d", '"')

    for line in safe_text.split("\n"):
        pdf.multi_cell(0, 6, line)

    return pdf.output(dest="S").encode("latin-1", errors="ignore")


def filename_safe(s: str) -> str:
    s = safe_str(s)
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] if len(s) > 80 else s


def make_bundle_zip(files: List[Tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname, data in files:
            z.writestr(fname, data)
    buf.seek(0)
    return buf.read()


# -----------------------------
# 9) LIVE OHIO HOUSE ROSTER (STATEWIDE BCC SOURCE)
# -----------------------------
def rep_email_for_district(d: int) -> str:
    return f"rep{d:02d}@ohiohouse.gov"


@st.cache_data(ttl=6 * 60 * 60)
def fetch_ohio_house_roster() -> Tuple[pd.DataFrame, str, str]:
    """
    Returns: (roster_df, source_url, fetched_at)
    Best effort parse.
    """
    url = "https://www.legislature.ohio.gov/members/house-directory"
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    html = r.text

    # Try tables first
    rows = []
    try:
        tables = pd.read_html(html)
        # Look for a table that has "District" and "Member" columns
        best = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("district" in c for c in cols) and any("member" in c or "name" in c for c in cols):
                best = t
                break

        if best is not None and not best.empty:
            cols = {str(c).lower(): c for c in best.columns}
            district_col = cols.get("district", None)
            member_col = None
            for k in cols:
                if "member" in k or "name" in k:
                    member_col = cols[k]
                    break

            party_col = None
            for k in cols:
                if "party" in k:
                    party_col = cols[k]
                    break

            for _, row in best.iterrows():
                dist_raw = safe_str(row.get(district_col, "")) if district_col else ""
                name_raw = safe_str(row.get(member_col, "")) if member_col else ""
                party_raw = safe_str(row.get(party_col, "")) if party_col else ""

                m = re.search(r"(\d+)", dist_raw)
                if not m:
                    continue
                d = int(m.group(1))

                party = party_raw[:1].upper() if party_raw else ""
                rows.append(
                    {
                        "rep_district": str(d),
                        "rep_name": titlecase_name(name_raw),
                        "rep_party": party,
                        "rep_role": "State Rep",
                        "rep_email": rep_email_for_district(d),
                        "source": "legislature.ohio.gov house-directory",
                        "fetched_at": fetched_at,
                    }
                )
    except Exception:
        rows = []

    # Fallback regex parse
    if not rows:
        pattern = re.compile(r">([^<]+?)\s+District\s+(\d+)\s*\|\s*([DRI])", re.IGNORECASE)
        matches = pattern.findall(html)
        seen = set()
        for name, dist, party in matches:
            try:
                d = int(dist)
            except Exception:
                continue
            if d in seen:
                continue
            seen.add(d)
            rows.append(
                {
                    "rep_district": str(d),
                    "rep_name": titlecase_name(name),
                    "rep_party": party.upper(),
                    "rep_role": "State Rep",
                    "rep_email": rep_email_for_district(d),
                    "source": "legislature.ohio.gov house-directory",
                    "fetched_at": fetched_at,
                }
            )

    roster_df = pd.DataFrame(rows)
    if not roster_df.empty:
        roster_df = roster_df.dropna(subset=["rep_district"]).copy()
        roster_df["rep_district_int"] = roster_df["rep_district"].astype(int)
        roster_df = roster_df.sort_values("rep_district_int").drop(columns=["rep_district_int"])

    return roster_df, url, fetched_at


def build_bcc_list_from_roster(roster_df: pd.DataFrame) -> List[str]:
    if roster_df is None or roster_df.empty:
        return []
    if "rep_email" not in roster_df.columns:
        return []
    return unique_emails(roster_df["rep_email"].astype(str).tolist())


def school_districts_by_house_district(local_df: pd.DataFrame) -> pd.DataFrame:
    if local_df is None or local_df.empty:
        return pd.DataFrame(columns=["rep_district", "school_districts", "zip_count", "school_district_count"])

    tmp = local_df.copy()
    tmp["rep_district"] = tmp["rep_district"].astype(str).str.strip()

    out_rows = []
    for rep_dist, g in tmp.groupby("rep_district", dropna=False):
        dists = sorted([x for x in g["school_district"].dropna().unique().tolist() if str(x).strip()])
        zips = sorted([x for x in g["zip_code"].dropna().unique().tolist() if str(x).strip()])
        out_rows.append(
            {
                "rep_district": str(rep_dist),
                "school_districts": " | ".join(dists),
                "zip_count": len(zips),
                "school_district_count": len(dists),
            }
        )
    return pd.DataFrame(out_rows)


# -----------------------------
# 10) SIDEBAR
# -----------------------------
with st.sidebar:
    st.header("Roster")

    refresh_roster = st.button("Refresh Ohio House roster")
    if refresh_roster:
        fetch_ohio_house_roster.clear()

    roster_df = None
    roster_url = ""
    roster_fetched_at = ""
    try:
        roster_df, roster_url, roster_fetched_at = fetch_ohio_house_roster()
        st.session_state.roster_df = roster_df
    except Exception as e:
        st.session_state.roster_df = None
        st.error(f"Roster fetch failed: {e}")

    if st.session_state.roster_df is not None and not st.session_state.roster_df.empty:
        st.caption("Roster source")
        st.write(roster_url)
        st.caption("Last fetch")
        st.write(roster_fetched_at)

    st.divider()
    st.header("Data")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    sample_btn = st.button("Load sample data")

    st.divider()
    st.header("Your info")

    sender_name = st.text_input("Your name", value="")
    sender_city = st.text_input("City", value="Hamilton")
    sender_zip = st.text_input("ZIP", value="45011")

    st.divider()
    st.header("Mission")

    issue = st.text_input("Issue (short)", value="Protect public schools and retain educators")
    story = st.text_area("Your experience (short)", value="", height=120)

    ask_1 = st.text_input("Ask 1", value="Support a fair evaluation and staffing process that protects students.")
    ask_2 = st.text_input("Ask 2", value="Oppose policy changes that weaken teacher quality or stability.")
    ask_3 = st.text_input("Ask 3", value="Meet with local educators and families in this zip code.")

    closing = st.text_area(
        "Closing line",
        value="Thank you for your time and for serving our community.",
        height=80,
    )

    st.divider()
    st.caption("Drafts and exports only. You control delivery.")


# -----------------------------
# 11) LOAD DATA
# -----------------------------
def load_sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "zip_code": "45011",
                "school_district": "Hamilton City Schools",
                "rep_name": "Hall, Thomas",
                "rep_email": "rep46@ohiohouse.gov",
                "rep_role": "State Rep",
                "rep_district": "46",
                "rep_party": "R",
                "rep_stance": "Unknown",
            },
            {
                "zip_code": "45202",
                "school_district": "Cincinnati Public Schools",
                "rep_name": "Isaacsohn, Dani",
                "rep_email": "rep24@ohiohouse.gov",
                "rep_role": "State Rep",
                "rep_district": "24",
                "rep_party": "D",
                "rep_stance": "Unknown",
            },
        ]
    )


try:
    if sample_btn:
        st.session_state.loaded_df = normalize_dataframe(load_sample_df())

    if uploaded is not None:
        df_raw = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
        st.session_state.loaded_df = normalize_dataframe(df_raw)

except KeyError as e:
    st.error(f"CSV issue: {e}")
    st.session_state.loaded_df = None
except Exception as e:
    st.error(f"Could not load CSV: {e}")
    st.session_state.loaded_df = None

df = st.session_state.loaded_df
roster_df = st.session_state.roster_df


# -----------------------------
# 12) HEADER + DASHBOARD
# -----------------------------
st.title("Class Action: Ohio")
st.write("Draft letters. Draft emails. Export clean packets. Track your progress.")

rank, floor, ceil = rank_for_xp(st.session_state.xp)
c1, c2, c3 = st.columns(3)
c1.metric("Rank", rank)
c2.metric("XP", st.session_state.xp)
c3.metric("Actions logged", len(st.session_state.actions))

if ceil > floor:
    progress = (st.session_state.xp - floor) / (ceil - floor)
    st.progress(max(0.0, min(1.0, float(progress))))
else:
    st.progress(1.0)

st.markdown(
    '<div class="warroom-card"><div class="small-muted">'
    "Letters and email drafts add XP in this session."
    "</div></div>",
    unsafe_allow_html=True,
)

st.divider()


# -----------------------------
# 13) TABS
# -----------------------------
tab_roster, tab_warroom, tab_builder, tab_logs = st.tabs(
    ["Ohio House Roster", "War Room", "Builder", "Logs"]
)

with tab_roster:
    st.subheader("Ohio House roster (live fetch)")

    if roster_df is None or roster_df.empty:
        st.warning("Roster not available right now.")
    else:
        st.dataframe(
            roster_df[["rep_district", "rep_name", "rep_party", "rep_email"]],
            use_container_width=True,
            hide_index=True,
        )

        roster_csv = roster_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download roster CSV",
            data=roster_csv,
            file_name=f"ohio_house_roster_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

    st.divider()
    st.subheader("School districts per House district (from your uploaded master CSV)")

    if df is None or df.empty:
        st.info("Upload your master CSV to compute school districts per House district.")
    else:
        sd_map = school_districts_by_house_district(df)
        if roster_df is not None and not roster_df.empty:
            merged = roster_df.merge(sd_map, on="rep_district", how="left")
        else:
            merged = sd_map

        cols = ["rep_district"]
        for c in ["rep_name", "rep_party", "rep_email", "school_district_count", "zip_count", "school_districts"]:
            if c in merged.columns:
                cols.append(c)

        st.dataframe(merged[cols], use_container_width=True, hide_index=True)

        merged_csv = merged.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download roster + school districts CSV",
            data=merged_csv,
            file_name=f"ohio_roster_school_districts_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

with tab_warroom:
    st.subheader("Targets")

    if df is None:
        st.info("Upload a CSV to begin. Or load sample data in the sidebar.")
        st.stop()

    zips = sorted([z for z in df["zip_code"].dropna().unique().tolist() if z])
    districts = sorted([d for d in df["school_district"].dropna().unique().tolist() if d])

    left, right = st.columns(2)
    with left:
        zip_choice = st.selectbox("ZIP", [""] + zips, index=0)
    with right:
        district_choice = st.selectbox("School district", [""] + districts, index=0)

    reps = reps_from_df(df, zip_choice, district_choice)

    if not reps:
        st.warning("No representatives found for that filter.")
    else:
        labels = [r["display_label"] for r in reps]
        selected_labels = st.multiselect(
            "Select targets",
            options=labels,
            default=labels[: min(2, len(labels))],
        )
        selected_reps = [reps[labels.index(l)] for l in selected_labels] if selected_labels else []

        st.write(f"Selected targets: {len(selected_reps)}")

        if selected_reps:
            keep_cols = ["rep_name", "rep_email", "rep_role", "rep_district", "rep_party", "rep_stance"]
            view_df = pd.DataFrame(selected_reps)
            keep_cols = [c for c in keep_cols if c in view_df.columns]
            st.dataframe(view_df[keep_cols], use_container_width=True, hide_index=True)

with tab_builder:
    st.subheader("Draft builder")

    if df is None:
        st.info("Upload a CSV to begin. Or load sample data in the sidebar.")
        st.stop()

    zips = sorted([z for z in df["zip_code"].dropna().unique().tolist() if z])
    districts = sorted([d for d in df["school_district"].dropna().unique().tolist() if d])

    b1, b2 = st.columns(2)
    with b1:
        zip_choice_b = st.selectbox("ZIP (builder)", [""] + zips, index=0, key="zip_builder")
    with b2:
        district_choice_b = st.selectbox(
            "School district (builder)", [""] + districts, index=0, key="dist_builder"
        )

    reps_b = reps_from_df(df, zip_choice_b, district_choice_b)
    if not reps_b:
        st.warning("No representatives found for that filter.")
        st.stop()

    labels_b = [r["display_label"] for r in reps_b]
    selected_label_b = st.selectbox("Primary target (preview)", labels_b, index=0)

    chosen_rep = reps_b[labels_b.index(selected_label_b)]

    sender_zip_clean = safe_zip(sender_zip)
    sender_city_clean = clean_whitespace(sender_city)
    sender_name_clean = remove_commas_from_name(sender_name) if sender_name else "A concerned constituent"

    letter_text = build_letter_text(
        sender_name=sender_name_clean,
        sender_city=sender_city_clean,
        sender_zip=sender_zip_clean,
        rep_name=chosen_rep.get("rep_name", ""),
        rep_role=chosen_rep.get("rep_role", ""),
        rep_district=chosen_rep.get("rep_district", ""),
        issue=issue,
        story=story,
        ask_1=ask_1,
        ask_2=ask_2,
        ask_3=ask_3,
        closing=closing,
    )

    email_subject = build_email_subject(issue)

    # BCC settings
    st.divider()
    st.subheader("BCC settings")

    bcc_enabled = st.checkbox("Include statewide BCC list in email drafts", value=True)
    bcc_batch_size = st.number_input(
        "BCC batch size",
        min_value=1,
        max_value=200,
        value=DEFAULT_BCC_BATCH_SIZE,
        step=5,
    )

    statewide_bcc = build_bcc_list_from_roster(roster_df) if bcc_enabled else []
    primary_to = normalize_email(chosen_rep.get("rep_email", ""))
    statewide_bcc = [e for e in statewide_bcc if e != primary_to]
    bcc_batches = chunk_list(statewide_bcc, int(bcc_batch_size)) if statewide_bcc else [[]]

    st.write(f"Total statewide BCC emails: {len(statewide_bcc)}")
    st.write(f"Email draft batches: {len(bcc_batches)}")

    # Build an email draft preview for batch 1
    email_text_preview = build_email_text_with_bcc(
        to_email=primary_to,
        subject=email_subject,
        bcc_emails=bcc_batches[0] if bcc_batches else [],
        body_text_same_as_letter=letter_text,
    )

    p1, p2 = st.columns(2)
    with p1:
        st.markdown("Letter preview")
        st.text_area("", value=letter_text, height=420, key="letter_preview")
    with p2:
        st.markdown("Email draft preview (matches PDFs)")
        st.text_area("", value=email_text_preview, height=420, key="email_preview")

    st.divider()
    st.subheader("Generate files")

    colA, colB, colC = st.columns(3)
    with colA:
        gen_letter_pdf = st.button("Generate letter PDF")
    with colB:
        gen_email_pdfs = st.button("Generate email draft PDF(s)")
    with colC:
        gen_bundle = st.button("Generate ZIP (letters + email drafts)")

    ext = "pdf" if FPDF is not None else "txt"

    if gen_letter_pdf:
        title = f"Letter — {chosen_rep.get('rep_name','Representative')}"
        data = pdf_from_text(title, letter_text)
        add_action("Letter draft", f"{chosen_rep.get('rep_name','')}", XP_PER_LETTER)
        st.download_button(
            "Download letter file",
            data=data,
            file_name=f"{filename_safe(title)}.{ext}",
            mime="application/pdf" if ext == "pdf" else "text/plain",
        )

    if gen_email_pdfs:
        # One PDF per batch
        files_out = []
        for i, bcc_batch in enumerate(bcc_batches, start=1):
            email_text = build_email_text_with_bcc(
                to_email=primary_to,
                subject=email_subject,
                bcc_emails=bcc_batch,
                body_text_same_as_letter=letter_text,
            )
            title = f"Email Draft — {chosen_rep.get('rep_name','Representative')} — Batch {i:03d}"
            data = pdf_from_text(title, email_text)
            files_out.append((f"{filename_safe(title)}.{ext}", data))

        add_action("Email drafts", f"{chosen_rep.get('rep_name','')} ({len(files_out)} batch)", XP_PER_EMAIL)

        if len(files_out) == 1:
            st.download_button(
                "Download email draft file",
                data=files_out[0][1],
                file_name=files_out[0][0],
                mime="application/pdf" if ext == "pdf" else "text/plain",
            )
        else:
            z = make_bundle_zip(files_out)
            st.download_button(
                "Download email draft ZIP",
                data=z,
                file_name=f"email_drafts_{date.today().isoformat()}.zip",
                mime="application/zip",
            )

    if gen_bundle:
        batch_reps = reps_b
        files: List[Tuple[str, bytes]] = []

        # Build statewide list once per bundle
        statewide_bcc_all = build_bcc_list_from_roster(roster_df) if bcc_enabled else []

        for r in batch_reps:
            rep_name = safe_str(r.get("rep_name")) or "Representative"
            rep_role = safe_str(r.get("rep_role"))
            rep_dist = safe_str(r.get("rep_district"))
            rep_email = normalize_email(r.get("rep_email", ""))

            lt = build_letter_text(
                sender_name=sender_name_clean,
                sender_city=sender_city_clean,
                sender_zip=sender_zip_clean,
                rep_name=rep_name,
                rep_role=rep_role,
                rep_district=rep_dist,
                issue=issue,
                story=story,
                ask_1=ask_1,
                ask_2=ask_2,
                ask_3=ask_3,
                closing=closing,
            )

            subj = build_email_subject(issue)

            # Letter PDF
            letter_title = f"Letter — {rep_name}"
            files.append((f"letters/{filename_safe(letter_title)}.{ext}", pdf_from_text(letter_title, lt)))

            # Email Draft PDFs in BCC batches (body equals letter text)
            bcc_list = [e for e in unique_emails(statewide_bcc_all) if e and e != rep_email]
            batches = chunk_list(bcc_list, int(bcc_batch_size)) if bcc_list else [[]]

            for i, bcc_batch in enumerate(batches, start=1):
                email_text = build_email_text_with_bcc(
                    to_email=rep_email,
                    subject=subj,
                    bcc_emails=bcc_batch,
                    body_text_same_as_letter=lt,
                )
                email_title = f"Email Draft — {rep_name} — Batch {i:03d}"
                files.append((f"emails/{filename_safe(email_title)}.{ext}", pdf_from_text(email_title, email_text)))

        if st.session_state.actions:
            log_df = pd.DataFrame(st.session_state.actions)
            files.append(("action_log.csv", log_df.to_csv(index=False).encode("utf-8")))

        bundle = make_bundle_zip(files)
        add_action("Export", f"{len(batch_reps)} targets", XP_PER_EXPORT)
        st.session_state.last_export_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        st.download_button(
            "Download ZIP bundle",
            data=bundle,
            file_name=f"class_action_ohio_bundle_{date.today().isoformat()}.zip",
            mime="application/zip",
        )

with tab_logs:
    st.subheader("Action log")

    if not st.session_state.actions:
        st.write("No actions yet.")
    else:
        log_df = pd.DataFrame(st.session_state.actions)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

        log_csv = log_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download action log CSV",
            data=log_csv,
            file_name=f"action_log_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

        st.write(f"Last export: {st.session_state.last_export_at or 'None'}")


# -----------------------------
# 14) DATA HEALTH CHECKS
# -----------------------------
with st.expander("Data health checks", expanded=False):
    if df is None:
        st.write("No dataset loaded.")
    else:
        st.write("Columns found:")
        st.write(list(df.columns))

        st.write("Row count:", len(df))
        st.write("ZIP count:", df["zip_code"].nunique())
        st.write("District count:", df["school_district"].nunique())

        st.dataframe(df.head(20), use_container_width=True, hide_index=True)