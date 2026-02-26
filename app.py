import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. PROOF & DIAGNOSTICS ---
VERSION = "3.1.0 - SUCCESS CHECK"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. CONFIG & SETUP ---
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

@st.cache_data
def load_color_map():
    if os.path.exists("bricklink_colors.csv"):
        try:
            df = pd.read_csv("bricklink_colors.csv")
            return dict(zip(df['Bricklink ID'], df['Bricklink Name']))
        except: return {}
    return {}

@st.cache_data
def load_internal_catalog():
    if os.path.exists("Parts.txt"):
        try:
            df_ref = pd.read_csv("Parts.txt", sep='\t', encoding='latin1')
            return dict(zip(df_ref.iloc[:, 2].astype(str), df_ref.iloc[:, 3]))
        except: return {}
    return {}

COLOR_LOOKUP = load_color_map()
CATALOG_LOOKUP = load_internal_catalog()

def parse_sub_ranges(range_expr):
    found_holes = set()
    if not range_expr: return {1}
    std = str(range_expr).replace('/', '-').replace('\\', '-').replace(' ', '')
    for part in re.split(r'[,;]+', std):
        if not part: continue
        if '-' in part:
            try:
                pts = part.split('-')
                if len(pts) == 2:
                    found_holes.update(range(int(pts[0]), int(pts[1]) + 1))
            except: continue
        else:
            try: found_holes.add(int(part))
            except: continue
    return found_holes if found_holes else {1}

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .success-nav { background-color: #064e3b; padding: 20px; border-radius: 12px; border: 2px solid #10b981; color: #ecfdf5; margin-bottom: 20px; }
    .hole-box { display: inline-block; width: 32px; height: 32px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 32px; font-weight: bold; color: white; }
    .hole-empty { background-color: #059669; }
    .hole-low { background-color: #d97706; }
    .hole-filled { background-color: #991b1b; opacity: 0.3; }
    </style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("🧱 Auditor Settings")

# THE PROOF BOX
st.sidebar.markdown(f"""
<div class='success-nav'>
    <h3 style='margin:0;'>✅ UPDATE SUCCESSFUL</h3>
    <hr style='margin:10px 0;'>
    <b>Version:</b> {VERSION}<br>
    <b>Saved:</b> {LAST_MODIFIED}
</div>
""", unsafe_allow_html=True)

st.sidebar.info(f"**Running From:**\n{SCRIPT_PATH}")

if st.sidebar.button("🚨 CLEAR APP CACHE"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")
qty_threshold = st.sidebar.number_input("Max Qty in Hole", min_value=0, value=0)
purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "New Only", "Used Only"])

# --- 5. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

# Session State for XML
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

if st.session_state.xml_data is None:
    st.info("Please upload your BrickLink 'store.xml' file.")
    uploaded_xml = st.file_uploader("Upload store.xml:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🗑️ Clear Data"):
    st.session_state.xml_data = None
    st.rerun()

# --- 6. CORE LOGIC ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    # Storage Mapping
    stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    
    for item in items:
        rem = item.find("REMARKS").text.strip() if item.find("REMARKS") is not None else ""
        if not rem: continue
        
        parts = re.split(r'[-/\\ ]', rem, 1)
        drawer_id = parts[0]
        cond = (item.find("CONDITION").text or "U").upper()
        qty = int(item.find("QTY").text or 0)
        
        holes = parse_sub_ranges(parts[1]) if len(parts) > 1 else {1}
        for h in holes:
            stats[drawer_id][h]["qty"] += qty
            stats[drawer_id][h]["conds"].add(cond)

    if app_mode == "Gap Auditor":
        # Using Seller's Exact Defaults
        categories = [
            {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
            {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
            {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
            {"name": "Multi Drawers", "prefix": "D", "start": 1, "end": 38, "cap": 24},
            {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
        ]

        for cat in categories:
            prefix, cap = cat['prefix'], cat['cap']
            results = []
            
            for n in range(cat['start'], cat['end'] + 1):
                label = f"{prefix}{n}" if prefix == "" else f"{prefix}{n:03d}"
                unit_data = stats[label]
                unit_matches = {}
                
                for h in range(1, cap + 1):
                    h_info = unit_data.get(h, {"qty": 0, "conds": set()})
                    q = h_info["qty"]
                    c = "EMPTY" if not h_info["conds"] else "NEW" if "N" in h_info["conds"] else "USED"
                    
                    if q <= qty_threshold:
                        if purity_filter == "Show All" or purity_filter.upper().startswith(c):
                            unit_matches[h] = {"qty": q, "cond": c}
                
                if unit_matches:
                    results.append((label, unit_matches))

            with st.expander(f"📂 {cat['name']} - {len(results)} Available Units"):
                if not results:
                    st.write("No matching slots found.")
                else:
                    for lbl, m_holes in results:
                        st.write(f"**Unit {lbl}**")
                        grid = "<div>"
                        for h in range(1, cap + 1):
                            color_class = "hole-empty" if h in m_holes and m_holes[h]['qty'] == 0 else "hole-low" if h in m_holes else "hole-filled"
                            grid += f'<div class="hole-box {color_class}">{h if h in m_holes else "X"}</div>'
                            if h % 10 == 0: grid += "<br>"
                        st.markdown(grid + "</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Processing Error: {e}")