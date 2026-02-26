import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & PROOF (Keep this to ensure we are always live) ---
VERSION = "3.2.0 - FULL RESTORATION"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. CONFIG & STORAGE DEFAULTS ---
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

def get_default_categories():
    """Your specific storage layout as described."""
    return [
        {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi-Slot Drawers", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

# --- 3. UI STYLE ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .proof-panel { 
        background-color: #064e3b; 
        padding: 12px; 
        border-radius: 8px; 
        border: 1px solid #10b981; 
        color: #ecfdf5;
        font-family: monospace;
        font-size: 0.8rem;
        margin-bottom: 20px;
    }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #ef4444; opacity: 0.3; }
    </style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR CONTROLS ---
st.sidebar.title("🧱 Auditor Settings")

# Live Proof Panel
st.sidebar.markdown(f"""
<div class='proof-panel'>
    <b>✅ SYSTEM LIVE</b><br>
    Ver: {VERSION}<br>
    Saved: {LAST_MODIFIED}
</div>
""", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Search Filters")
qty_threshold = st.sidebar.number_input("Max Qty in Hole (Density)", min_value=0, value=0, help="Find slots with <= this many parts.")
purity_filter = st.sidebar.selectbox("Condition Focus (Purity)", ["Show All", "Empty Only", "New Only", "Used Only"])

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Storage Profile Editor")

# Initialize Session State for Categories
if 'temp_categories' not in st.session_state:
    st.session_state.temp_categories = get_default_categories()

for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"n_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"p_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start", value=int(cat['start']), key=f"s_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End", value=int(cat['end']), key=f"e_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes", value=int(cat.get('cap', 1)), key=f"c_{i}")

# --- 5. DATA LOADING HELPERS ---
@st.cache_data
def load_references():
    color_map = {}
    parts_map = {}
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

# --- 6. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

if st.session_state.xml_data is None:
    st.info("👋 Everything is restored. Please upload your 'store.xml' to begin.")
    uploaded_xml = st.file_uploader("Upload store.xml:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🔄 Clear and Restart"):
    st.session_state.xml_data = None
    st.rerun()

# --- 7. AUDIT LOGIC ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem = rem_node.text.strip()
            # Split to get ID (B001) and Subloc (05)
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
                    # Standard formatting: Drawer 105 or Box B012
                    label = f"{prefix}{n}" if prefix == "" else f"{prefix}{n:03d}"
                    unit_data = container_stats[label]
                    unit_matches = {}
                    
                    for h in range(1, cap + 1):
                        h_info = unit_data.get(h, {"qty": 0, "conds": set()})
                        q = h_info["qty"]
                        # Determine purity
                        if not h_info["conds"]: purity = "EMPTY"
                        elif len(h_info["conds"]) > 1: purity = "MIXED"
                        else: purity = "NEW" if "N" in h_info["conds"] else "USED"
                        
                        # Apply Filters
                        if q <= qty_threshold:
                            if purity_filter == "Show All" or purity_filter.upper().startswith(purity):
                                unit_matches[h] = {"qty": q, "purity": purity}
                    
                    if unit_matches:
                        match_count += 1
                        with st.expander(f"Unit {label} — {len(unit_matches)} slots match"):
                            # Grid Visualization
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
                                # Single drawer layout
                                m = unit_matches[1]
                                st.write(f"Qty: **{m['qty']}** | Condition: **{m['purity']}**")

                if match_count == 0:
                    st.warning("No storage locations found matching your current filters.")

    elif app_mode == "Condition Guard":
        # Check drawer purity
        conflict_list = []
        for d_id, d_conds in container_stats.items():
            # Check if any individual hole has mixed conditions or if the whole unit is mixed
            for h_id, h_data in d_conds.items():
                if len(h_data["conds"]) > 1:
                    conflict_list.append(d_id)
                    break
        
        if not conflict_list:
            st.success("✅ Your inventory condition is pure! No mixed New/Used containers.")
        else:
            st.error(f"Found {len(conflict_list)} Containers with Condition Conflicts")
            for c in sorted(conflict_list):
                with st.expander(f"🔴 Conflict: {c}"):
                    for item in container_contents[c]:
                        st.write(f"{item['qty']}x {item['desc']} ({item['cond']}) @ Hole {item['loc']}")

except Exception as e:
    st.error(f"Logic Error: {e}")