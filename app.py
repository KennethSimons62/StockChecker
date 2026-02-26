import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & TRACEABILITY ---
VERSION = "4.8.1 - THE FULL WORKHORSE"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. MEMORY ENGINE (Color Registry) ---
REGISTRY_FILE = "color_registry.json"
PROFILE_DIR = "lego_profiles"

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_registry(data):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=4)

if 'color_map' not in st.session_state:
    st.session_state.color_map = load_registry()

# --- 3. STORAGE DEFAULTS ---
def get_seller_defaults():
    return [
        {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi Drawers (D)", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet (FC)", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

def get_profile_list():
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default"]

# --- 4. SESSION STATE ANCHORING ---
if 'active_profile' not in st.session_state:
    st.session_state.active_profile = "Default"

if 'temp_categories' not in st.session_state:
    path = os.path.join(PROFILE_DIR, f"{st.session_state.active_profile}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            st.session_state.temp_categories = json.load(f)
    else:
        st.session_state.temp_categories = get_seller_defaults()

if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

# --- 5. PAGE STYLE ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .trainer-zone { background-color: #1e1b4b; padding: 20px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 25px; color: white; }
    .status-badge { background-color: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #3b82f6; color: #f8fafc; font-family: monospace; font-size: 0.75rem; margin-bottom: 20px; }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; border: 1px solid rgba(255,255,255,0.1); }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #ef4444; opacity: 0.15; }
    .cat-header { font-size: 1.5rem; font-weight: bold; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR (The Command Center) ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-badge'><b>LIVE VERSION: {VERSION}</b><br>Saved: {LAST_MODIFIED}</div>", unsafe_allow_html=True)

st.sidebar.subheader("🔍 Search Filters")
qty_threshold = st.sidebar.number_input("Max Qty / Slot", min_value=0, value=0)
purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "New Only", "Used Only"])

st.sidebar.markdown("---")
app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Profile Commander")
profiles = get_profile_list()
selected_p = st.sidebar.selectbox("Load Profile", profiles, index=profiles.index(st.session_state.active_profile) if st.session_state.active_profile in profiles else 0)

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    path = os.path.join(PROFILE_DIR, f"{selected_p}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            st.session_state.temp_categories = json.load(f)
    st.rerun()

new_name = st.sidebar.text_input("Profile Name", value=st.session_state.active_profile)
col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    if st.button("💾 SAVE", use_container_width=True):
        path = os.path.join(PROFILE_DIR, f"{new_name}.json")
        with open(path, "w") as f:
            json.dump(st.session_state.temp_categories, f, indent=4)
        st.session_state.active_profile = new_name
        st.sidebar.success("Saved!")
        st.rerun()
with col_s2:
    if st.button("🗑️ DELETE", use_container_width=True):
        path = os.path.join(PROFILE_DIR, f"{st.session_state.active_profile}.json")
        if os.path.exists(path) and st.session_state.active_profile != "Default":
            os.remove(path)
            st.session_state.active_profile = "Default"
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Layout Editor")
for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"lab_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"pre_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"sta_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"end_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Unit", value=int(cat['cap']), key=f"cap_{i}")

# --- 7. CORE LOGIC ---
def get_clean_id(prefix, number):
    try:
        n = str(int(number))
        p = prefix.upper().strip()
        return f"{p}{n}"
    except: return f"{prefix}{number}"

def parse_holes(expr):
    holes = set()
    if not expr: return {1}
    clean = str(expr).replace('/', '-').replace('\\', '-').replace(' ', '')
    for p in re.split(r'[,;]+', clean):
        if not p: continue
        if '-' in p:
            try:
                pts = p.split('-')
                holes.update(range(int(pts[0]), int(pts[1]) + 1))
            except: continue
        else:
            try: holes.add(int(p))
            except: continue
    return holes if holes else {1}

# --- 8. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    uploaded_xml = st.file_uploader("Upload store.xml to Audit or Train:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

# --- 9. THE AUDIT & TRAINING ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set(), "color_ids": set()}))
    all_found_colors = set()

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem = rem_node.text.strip()
            m = re.search(r'^([A-Za-z]*)\s*(\d+)(?:[-/\\ ]+([0-9/\\,-]+))?', rem)
            if m:
                pref, num, h_raw = m.groups()
                norm_id = get_clean_id(pref or "", num)
                cond = (item.find("CONDITION").text or "U").upper()
                qty = int(item.find("QTY").text or 0)
                cid = item.find("COLOR").text
                all_found_colors.add(cid)
                
                h_set = parse_holes(h_raw)
                for h in h_set:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                    container_stats[norm_id][h]["color_ids"].add(cid)

    # --- 🧠 TRAINING ZONE ---
    unknowns = [c for c in all_found_colors if c not in st.session_state.color_map]
    if unknowns:
        st.markdown(f"<div class='trainer-zone'><h3>🧠 Training Mode: {len(unknowns)} New Colors Found</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        target = unknowns[0]
        with col1: st.metric("BrickLink Code", target)
        with col2: color_name = st.text_input(f"Name for code {target}:", placeholder="e.g. Dark Bluish Gray")
        with col3: 
            st.write("") # Spacer
            if st.button("✅ LEARN"):
                if color_name:
                    st.session_state.color_map[target] = color_name
                    save_registry(st.session_state.color_map)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if app_mode == "Gap Auditor":
        tabs = st.tabs([c['name'] for c in st.session_state.temp_categories])
        for idx, cat in enumerate(st.session_state.temp_categories):
            with tabs[idx]:
                curr_prefix, curr_cap = str(cat['prefix']).upper().strip(), int(cat['cap'])
                st.markdown(f"<div class='cat-header'>{cat['name']}</div>", unsafe_allow_html=True)
                
                match_count = 0
                for n in range(int(cat['start']), int(cat['end']) + 1):
                    unit_id = get_clean_id(curr_prefix, n)
                    unit_data = container_stats.get(unit_id, {})
                    unit_matches = {}
                    for h in range(1, curr_cap + 1):
                        h_info = unit_data.get(h, {"qty": 0, "conds": set(), "color_ids": set()})
                        q = h_info["qty"]
                        p_state = "EMPTY" if not h_info["conds"] else "NEW" if "N" in h_info["conds"] else "USED"
                        if q <= qty_threshold:
                            if purity_filter == "Show All" or purity_filter.upper().startswith(p_state):
                                unit_matches[h] = {"qty": q, "purity": p_state, "cids": h_info["color_ids"]}
                    
                    if unit_matches:
                        match_count += 1
                        display_id = f"{curr_prefix}{n:03d}" if curr_prefix else f"{n}"
                        with st.expander(f"{display_id} — {len(unit_matches)} gaps"):
                            if curr_cap > 1:
                                grid = "<div>"
                                for h in range(1, curr_cap + 1):
                                    s_cls = "hole-empty" if h in unit_matches and unit_matches[h]['qty'] == 0 else "hole-low" if h in unit_matches else "hole-filled"
                                    grid += f'<div class="hole-box {s_cls}">{h if h in unit_matches else "X"}</div>'
                                    if h % 10 == 0: grid += "<br>"
                                st.markdown(grid + "</div>", unsafe_allow_html=True)
                            
                            for h_num, m_data in unit_matches.items():
                                if m_data['cids']:
                                    names = [st.session_state.color_map.get(cid, f"Code {cid}") for cid in m_data['cids']]
                                    st.markdown(f"📍 **Slot {h_num}:** {', '.join(names)}")

except Exception as e:
    st.error(f"Error: {e}")

if st.button("🔄 Clear Upload"):
    st.session_state.xml_data = None
    st.rerun()