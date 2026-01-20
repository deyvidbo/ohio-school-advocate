import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
from datetime import date
import io

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Class Action Ohio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. PERSISTENT SESSION STATE ---
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'district_stats' not in st.session_state:
    st.session_state.district_stats = {}
if 'hall_of_fame' not in st.session_state:
    st.session_state.hall_of_fame = ["David M. Bothast"]

# --- 3. DATA ENGINE (Optimized for 2026 Directory) ---
@st.cache_data
def load_data():
    try:
        # Crucial: rep_district must be a string to maintain "01", "02" etc.
        df = pd.read_csv("ohio_districts.csv", dtype={'zip_code': str, 'rep_district': str})
        df.fillna("N/A", inplace=True)
        return df
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

df = load_data()
