import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & PROOF (Ensuring we are live and working) ---
VERSION = "3.3.0 - THE ARCHITECT"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. FILE SYSTEM & PROFILE ENGINE ---
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

def get_profile_list():
    """Scans the profile folder for JSON files."""
    if not os.path.exists(PROFILE_DIR): return ["Default"]
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default"]

def load_profile_file(name):
    """Loads a specific profile or returns the hardcoded master defaults."""
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except: pass
    
    # Master Defaults for the Seller
    return [
        {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi-Slot Drawers", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

def save_profile_file(name, data):
    """Saves the current session data to a JSON file on the server."""
    if not os.path.exists(PROFILE_DIR): os.makedirs(PROFILE_DIR)
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# --- 3. UI STYLE & THEME ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .live-badge { 
        background-color: #064e3b; 
        padding: 10px; 
        border-radius: 6px; 
        border: 1px solid #10b981; 
        color: #ecfdf5;
        font-family: monospace;
        font-size: 0.75rem;
        margin-bottom: 15px;
    }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #ef4444; opacity: 0.25; }
    </style>
""", unsafe_allow_html=True)

# --- 4. SESSION STATE INITIALIZATION ---
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None
if 'active_profile' not in st.session_state:
    st.session_state.active_profile = "Default"
if 'temp_categories' not in st.session_state:
    st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)

# --- 5. SIDEBAR (The Control Tower) ---
st.sidebar.title("🧱 Auditor Settings")

# Live Proof Badge
st.sidebar.markdown(f"""
<div class='live-badge'>
    <b>STATUS: SYSTEM ONLINE</b><br>
    Ver: {VERSION}<br>
    Saved: {LAST_MODIFIED}
</div>
""", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Profile Management")

# Profile Selector
profile_list = get_profile_list()
selected_p = st.sidebar.selectbox("Active Profile:", profile_list, index=profile_list.index(st.session_state.active_profile) if st.session_state.active_profile in profile_list else 0)

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    st.session_state.temp_categories = load_profile_file(selected_p)
    st.rerun()

# Search Filters
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Search Filters")
qty_threshold = st.sidebar.number_input("Max Density (Qty/Slot)", min_value=0, value=0)
purity_filter = st.sidebar.selectbox("Condition Purity", ["Show All", "Empty Only", "New Only", "Used Only"])

# Profile Editor
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Storage Layout")

for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"n_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"p_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"s_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"e_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes", value=int(cat.get('cap', 1)), key=f"c_{i}")

st.sidebar.markdown("---")
input_pass = st.sidebar.text_input("Admin Key", type="password")
if input_pass == ADMIN_PASSWORD:
    if st.sidebar.button("💾 SAVE PROFILE TO SERVER"):
        save_profile_file(st.session_state.active_profile, st.session_state.temp_categories)
        st.sidebar.success(f"Profile '{st.session_state.active_profile}' updated!")

# --- 6. DATA LOADING & HELPERS ---
@st.cache_data
def load_references():
    color_map, parts_map = {}, {}
    if os.path.exists("bricklink_colors.csv"):
        df = pd.read_csv("bricklink_colors.csv")
        color_map = dict(zip(df['Bricklink ID'], df['Bricklink Name']))
    if os.path.exists("Parts.txt"):
        df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1')
        parts_map = dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
    return color_map, parts_map

COLOR_LOOKUP, CATALOG_LOOKUP = load_references()

def parse_sub_ranges(range_expr):
    found_holes = set()
    if not range_expr: return {1}
    std = str(range_expr).replace('/', '-').replace('\\', '-').replace(' ', '')
    for part in re.split(r'[,;]+', std):
        if not part: continue
        if '-' in part:
            try:
                pts = part.split('-')
                found_holes.update(range(int(pts[0]), int(pts[1]) + 1))
            except: continue
        else:
            try: found_holes.add(int(part))
            except: continue
    return found_holes if found_holes else {1}

# --- 7. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    st.info("👋 Welcome back. Please upload your BrickLink 'store.xml' to start the audit.")
    uploaded_xml = st.file_uploader("Upload store.xml:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🔄 Clear Current Session"):
    st.session_state.xml_data = None
    st.rerun()

# --- 8. AUDIT ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem = rem_node.text.strip()
            parts = re.split(r'[-/\\ ]', rem, 1)
            drawer_id = parts[0]
            cond = (item.find("CONDITION").text or "U").upper()
            qty = int(item.find("QTY").text or 0)
            
            holes = parse_sub_ranges(parts[1]) if len(parts) > 1 else {1}
            for h in holes:
                container_stats[drawer_id][h]["qty"] += qty
                container_stats[drawer_id][h]["conds"].add(cond)
            
            p_id = item.find("ITEMID").text
            container_contents[drawer_id].append({
                "desc": CATALOG_LOOKUP.get(p_id, p_id),
                "cond": cond, "qty": qty, "loc": parts[1] if len(parts) > 1 else "Main"
            })

    if app_mode == "Gap Auditor":
        tabs = st.tabs([cat['name'] for cat in st.session_state.temp_categories])
        
        for i, cat in enumerate(st.session_state.temp_categories):
            with tabs[i]:
                prefix, cap = cat['prefix'], int(cat['cap'])
                match_count = 0
                
                for n in range(cat['start'], cat['end'] + 1):
                    # Standard formatting (e.g. 105 or B012)
                    label = f"{prefix}{n}" if prefix == "" else f"{prefix}{n:03d}"
                    unit_data = container_stats[label]
                    unit_matches = {}
                    
                    for h in range(1, cap + 1):
                        h_info = unit_data.get(h, {"qty": 0, "conds": set()})
                        q = h_info["qty"]
                        if not h_info["conds"]: purity = "EMPTY"
                        elif len(h_info["conds"]) > 1: purity = "MIXED"
                        else: purity = "NEW" if "N" in h_info["conds"] else "USED"
                        
                        if q <= qty_threshold:
                            if purity_filter == "Show All" or purity_filter.upper().startswith(purity):
                                unit_matches[h] = {"qty": q, "purity": purity}
                    
                    if unit_matches:
                        match_count += 1
                        with st.expander(f"Unit {label} — {len(unit_matches)} slots available"):
                            if cap > 1:
                                grid_html = "<div>"
                                for h in range(1, cap + 1):
                                    if h in unit_matches:
                                        status = "hole-empty" if unit_matches[h]['qty'] == 0 else "hole-low"
                                        grid_html += f'<div class="hole-box {status}">{h}</div>'
                                    else:
                                        grid_html += f'<div class="hole-box hole-filled">X</div>'
                                    if h % 10 == 0: grid_html += "<br>"
                                st.markdown(grid_html + "</div>", unsafe_allow_html=True)
                            else:
                                m = unit_matches[1]
                                st.write(f"Qty: **{m['qty']}** | Condition: **{m['purity']}**")

                if match_count == 0:
                    st.warning(f"No storage gaps found in {cat['name']} matching your criteria.")

    elif app_mode == "Condition Guard":
        conflicts = [d_id for d_id, d_conds in container_stats.items() if any(len(h["conds"]) > 1 for h in d_conds.values())]
        
        if not conflicts:
            st.success("✅ Condition Purity Verified: No mixed New/Used containers.")
        else:
            st.error(f"Found {len(conflicts)} Containers with Condition Conflicts")
            for c in sorted(conflicts):
                with st.expander(f"🔴 Conflict: {c}"):
                    for item in container_contents[c]:
                        st.write(f"{item['qty']}x {item['desc']} ({item['cond']}) @ Hole {item['loc']}")

except Exception as e:
    st.error(f"Audit Error: {e}")