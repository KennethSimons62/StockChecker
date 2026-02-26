import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime
import io
import time

# --- 1. APP CONFIG & CONSTANTS ---
VERSION = "3.0.0 - PROOF EDITION"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

# PROOF LOGIC: Get the actual location and time of this file
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

# --- 2. HELPER FUNCTIONS ---

def get_profile_list():
    if not os.path.exists(PROFILE_DIR): return ["Default"]
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default"]

def load_profile_file(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except: pass
    return [
        {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi-Slot Drawers", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

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
        if not part or '-' not in part:
            try: found_holes.add(int(part))
            except: continue
        else:
            try:
                s, e = part.split('-')
                found_holes.update(range(int(s), int(e) + 1))
            except: continue
    return found_holes if found_holes else {1}

# --- 3. SESSION STATE ---
if 'xml_data' not in st.session_state: st.session_state.xml_data = None
if 'active_profile' not in st.session_state: st.session_state.active_profile = "Default"
if 'temp_categories' not in st.session_state: st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)

# --- 4. PAGE SETUP ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .proof-box { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px; }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 9px; line-height: 30px; font-weight: bold; color: white; }
    .hole-empty { background-color: #166534; }
    .hole-low { background-color: #854d0e; }
    .hole-filled { background-color: #991b1b; opacity: 0.4; }
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: THE PROOF PANEL ---
st.sidebar.title("🔍 Version Proof")
with st.sidebar.container():
    st.markdown(f"""
    <div class='proof-box'>
    <b>Current Version:</b><br><code style='color:#38bdf8'>{VERSION}</code><br><br>
    <b>File Path:</b><br><code style='font-size:10px'>{SCRIPT_PATH}</code><br><br>
    <b>File Last Saved:</b><br><code style='color:#fbbf24'>{LAST_MODIFIED}</code>
    </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("🚨 FORCE REFRESH EVERYTHING"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")
qty_threshold = st.sidebar.number_input("Max Qty in Hole", min_value=0, value=0)
purity_filter = st.sidebar.selectbox("Condition", ["Show All", "Empty Only", "New Only", "Used Only"])

# --- 6. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    st.info("Please upload 'store.xml' to start.")
    uploaded_xml = st.file_uploader("Upload XML", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

# --- 7. LOGIC ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem_text = rem_node.text.strip()
            drawer_id = re.split(r'[-/\\ ]', rem_text)[0]
            cond = (item.find("CONDITION").text or "U").upper()
            qty = int(item.find("QTY").text or 0)
            
            loc_parts = re.split(r'[- ]', rem_text, 1)
            holes = parse_sub_ranges(loc_parts[1]) if len(loc_parts) > 1 else {1}
            
            for h in holes:
                container_stats[drawer_id][h]["qty"] += qty
                container_stats[drawer_id][h]["conds"].add(cond)
            
            container_contents[drawer_id].append({
                "desc": CATALOG_LOOKUP.get(item.find("ITEMID").text, "Unknown"),
                "cond": cond, "qty": qty, "loc": loc_parts[1] if len(loc_parts) > 1 else "Main"
            })

    if app_mode == "Gap Auditor":
        for cat in st.session_state.temp_categories:
            prefix, cap = cat['prefix'], int(cat['cap'])
            matches = []
            for n in range(int(cat['start']), int(cat['end']) + 1):
                label = f"{prefix}{n}" if prefix == "" else f"{prefix}{n:03d}"
                unit_matches = {}
                for h in range(1, cap + 1):
                    h_info = container_stats[label].get(h, {"qty": 0, "conds": set()})
                    q = h_info["qty"]
                    c = "EMPTY" if not h_info["conds"] else "NEW" if "N" in h_info["conds"] else "USED"
                    
                    if q <= qty_threshold:
                        if purity_filter == "Show All" or purity_filter.upper().startswith(c):
                            unit_matches[h] = {"qty": q, "cond": c}
                if unit_matches: matches.append((label, unit_matches))

            with st.expander(f"📂 {cat['name']} ({len(matches)} Units)"):
                for lbl, m_holes in matches:
                    st.write(f"**{lbl}**")
                    grid = "<div>"
                    for h in range(1, cap + 1):
                        s = "hole-empty" if h in m_holes and m_holes[h]['qty']==0 else "hole-low" if h in m_holes else "hole-filled"
                        grid += f'<div class="hole-box {s}">{h if h in m_holes else "X"}</div>'
                        if h % 10 == 0: grid += "<br>"
                    st.markdown(grid + "</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")