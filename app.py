import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & PROOF ---
VERSION = "3.5.0 - THE PREFIX ISOLATOR"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. CONFIG & PROFILE ENGINE ---
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

if not os.path.exists(PROFILE_DIR):
    try: os.makedirs(PROFILE_DIR)
    except: pass

def load_profile_file(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except: pass
    
    # Seller's Exact Storage Specifications
    return [
        {"name": "Standard Drawers", "prefix": "NONE", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi-Slot Drawers (D)", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet (FC)", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

# --- 3. HELPER: ID NORMALIZATION ---
def get_norm_id(prefix, number):
    """Ensures 'B 001' and 'B1' both become 'B1' for perfect matching."""
    try:
        num_clean = str(int(number))
        pre_clean = "" if prefix.upper() == "NONE" else prefix.upper().strip()
        return f"{pre_clean}{num_clean}"
    except:
        return f"{prefix}{number}"

# --- 4. UI STYLE ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .status-card { background-color: #064e3b; padding: 12px; border-radius: 8px; border: 1px solid #10b981; color: #ecfdf5; font-family: monospace; font-size: 0.8rem; margin-bottom: 20px; }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; border: 1px solid rgba(0,0,0,0.1); }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #991b1b; opacity: 0.2; }
    .category-header { font-size: 1.5rem; font-weight: bold; color: #3b82f6; margin-bottom: 10px; border-bottom: 2px solid #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# --- 5. SESSION STATE ---
if 'xml_data' not in st.session_state: st.session_state.xml_data = None
if 'active_profile' not in st.session_state: st.session_state.active_profile = "Default"
if 'temp_categories' not in st.session_state: st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)

# --- 6. SIDEBAR ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-card'><b>SYSTEM LIVE</b><br>Ver: {VERSION}<br>Saved: {LAST_MODIFIED}</div>", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Search Filters")
qty_threshold = st.sidebar.number_input("Max Density (Qty/Slot)", min_value=0, value=0, help="0 = Only show completely empty holes.")
purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "New Only", "Used Only"])

st.sidebar.markdown("---")
if st.sidebar.button("💾 SAVE PROFILE"):
    path = os.path.join(PROFILE_DIR, f"{st.session_state.active_profile}.json")
    with open(path, "w") as f:
        json.dump(st.session_state.temp_categories, f, indent=4)
    st.sidebar.success("Saved!")

# --- 7. DATA LOADING ---
@st.cache_data
def load_references():
    color_map, parts_map = {}, {}
    if os.path.exists("bricklink_colors.csv"):
        df = pd.read_csv("bricklink_colors.csv")
        color_map = dict(zip(df['Bricklink ID'], df['Bricklink Name']))
    if os.path.exists("Parts.txt"):
        try:
            df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1')
            parts_map = dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
        except: pass
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

# --- 8. MAIN CONTENT ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    st.info("👋 Awaiting XML upload...")
    uploaded_xml = st.file_uploader("Upload store.xml:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🗑️ Clear XML"):
    st.session_state.xml_data = None
    st.rerun()

# --- 9. THE AUDIT ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    # [PrefixID][HoleNumber] = {qty, conds}
    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem = rem_node.text.strip()
            # This regex splits Prefix, Number, and Sub-locations
            match = re.search(r'^([A-Za-z]*)\s*(\d+)(?:[-/\\ ]+([0-9/\\,-]+))?', rem)
            if match:
                prefix, num, holes_raw = match.groups()
                norm_id = get_norm_id(prefix or "NONE", num)
                
                cond = (item.find("CONDITION").text or "U").upper()
                qty = int(item.find("QTY").text or 0)
                
                holes = parse_sub_ranges(holes_raw)
                for h in holes:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                
                container_contents[norm_id].append({
                    "desc": CATALOG_LOOKUP.get(item.find("ITEMID").text, "Lego Part"),
                    "cond": cond, "qty": qty, "loc": holes_raw if holes_raw else "Main"
                })

    if app_mode == "Gap Auditor":
        tabs = st.tabs([cat['name'] for cat in st.session_state.temp_categories])
        
        for i, cat in enumerate(st.session_state.temp_categories):
            with tabs[i]:
                # --- ISOLATION ZONE ---
                # We pull local variables to ensure no leakage between tabs
                t_prefix = str(cat['prefix'])
                t_cap = int(cat['cap'])
                t_start = int(cat['start'])
                t_end = int(cat['end'])
                
                st.markdown(f"<div class='category-header'>{cat['name']} (Prefix: {t_prefix})</div>", unsafe_allow_html=True)
                
                results_found = 0
                for n in range(t_start, t_end + 1):
                    # 1. Generate the EXACT ID for this category
                    search_id = get_norm_id(t_prefix, n)
                    unit_data = container_stats.get(search_id, {})
                    
                    unit_matches = {}
                    has_parts_beyond_threshold = False

                    for h in range(1, t_cap + 1):
                        h_info = unit_data.get(h, {"qty": 0, "conds": set()})
                        q = h_info["qty"]
                        
                        # Determine Purity
                        if not h_info["conds"]: p = "EMPTY"
                        elif len(h_info["conds"]) > 1: p = "MIXED"
                        else: p = "NEW" if "N" in h_info["conds"] else "USED"
                        
                        # Filter Check
                        if q <= qty_threshold:
                            if purity_filter == "Show All" or purity_filter.upper().startswith(p):
                                unit_matches[h] = {"qty": q, "purity": p}
                        else:
                            has_parts_beyond_threshold = True

                    # Only show if there's a gap AND (if threshold is 0, don't show occupied units)
                    if unit_matches:
                        results_found += 1
                        display_lbl = f"{t_prefix}{n}" if t_prefix == "NONE" else f"{t_prefix}{n:03d}"
                        
                        with st.expander(f"Unit {display_lbl} — {len(unit_matches)} slots match"):
                            if t_cap > 1:
                                # Render the visual grid
                                grid_html = "<div>"
                                for h in range(1, t_cap + 1):
                                    if h in unit_matches:
                                        status = "hole-empty" if unit_matches[h]['qty'] == 0 else "hole-low"
                                        grid_html += f'<div class="hole-box {status}">{h}</div>'
                                    else:
                                        grid_html += f'<div class="hole-box hole-filled">X</div>'
                                    if h % 10 == 0: grid_html += "<br>"
                                st.markdown(grid_html + "</div>", unsafe_allow_html=True)
                            else:
                                # Single unit detail
                                m = unit_matches[1]
                                st.write(f"Qty: **{m['qty']}** | Condition: **{m['purity']}**")

                if results_found == 0:
                    st.warning("No matches found in this category.")

    elif app_mode == "Condition Guard":
        conflicts = [d for d, holes in container_stats.items() if any(len(h["conds"]) > 1 for h in holes.values())]
        if not conflicts:
            st.success("✅ Condition Guard: No mixed containers found.")
        else:
            for c in sorted(conflicts):
                with st.expander(f"🔴 Conflict: {c}"):
                    for item in container_contents[c]:
                        st.write(f"{item['qty']}x {item['desc']} ({item['cond']}) @ Hole {item['loc']}")

except Exception as e:
    st.error(f"Audit Error: {e}")