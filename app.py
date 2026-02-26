import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & TRACEABILITY ---
VERSION = "3.7.0 - THE CLEANUP"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. STORAGE DEFAULTS (THE SAFETY NET) ---
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????" 

def get_seller_defaults():
    """Restores your exact storage specs if session state is lost."""
    return [
        {"name": "Standard Drawers", "prefix": "NONE", "start": 1, "end": 1107, "cap": 1},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
        {"name": "Multi Drawers (D)", "prefix": "D", "start": 1, "end": 38, "cap": 24},
        {"name": "Filing Cabinet (FC)", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
    ]

# --- 3. SESSION STATE INITIALIZATION ---
if 'temp_categories' not in st.session_state:
    st.session_state.temp_categories = get_seller_defaults()
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

# --- 4. UI STYLING ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .status-badge { background-color: #064e3b; padding: 10px; border-radius: 6px; border: 1px solid #10b981; color: #ecfdf5; font-family: monospace; font-size: 0.75rem; margin-bottom: 15px; }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; border: 1px solid rgba(0,0,0,0.2); }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #ef4444; opacity: 0.2; }
    .cat-title { font-size: 1.4rem; font-weight: bold; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR CONTROLS ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-badge'><b>LIVE: {VERSION}</b><br>Saved: {LAST_MODIFIED}</div>", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Global Search Filters")
qty_threshold = st.sidebar.number_input("Max Qty / Slot", min_value=0, value=0, help="Find holes with <= this many parts.")
purity_filter = st.sidebar.selectbox("Condition Filter", ["Show All", "Empty Only", "New Only", "Used Only"])

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Layout Editor")

for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"lab_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"pre_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start", value=int(cat['start']), key=f"sta_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End", value=int(cat['end']), key=f"end_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes", value=int(cat['cap']), key=f"cap_{i}")

st.sidebar.markdown("---")
if st.sidebar.button("💾 SAVE PROFILE PERMANENTLY"):
    if not os.path.exists(PROFILE_DIR): os.makedirs(PROFILE_DIR)
    with open(os.path.join(PROFILE_DIR, "Default.json"), "w") as f:
        json.dump(st.session_state.temp_categories, f, indent=4)
    st.sidebar.success("Profile Saved!")

# --- 6. DATA ENGINE ---
def normalize_id(prefix, number):
    """Aligns 'B1' and 'B 001' for matching logic."""
    try:
        n = str(int(number))
        p = "" if prefix.upper() == "NONE" else prefix.upper().strip()
        return f"{p}{n}"
    except: return f"{prefix}{number}"

def parse_sub_ranges(expr):
    holes = set()
    if not expr: return {1}
    clean = str(expr).replace('/', '-').replace('\\', '-').replace(' ', '')
    for p in re.split(r'[,;]+', clean):
        if not p: continue
        if '-' in p:
            try:
                s, e = p.split('-')
                holes.update(range(int(s), int(e) + 1))
            except: continue
        else:
            try: holes.add(int(p))
            except: continue
    return holes if holes else {1}

# --- 7. MAIN INTERFACE ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    st.info("👋 System online. Please upload your 'store.xml' to start.")
    uploaded_xml = st.file_uploader("Upload store.xml:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🔄 Clear and Start Over"):
    st.session_state.xml_data = None
    st.rerun()

# --- 8. AUDIT PROCESSING ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            rem = rem_node.text.strip()
            m = re.search(r'^([A-Za-z]*)\s*(\d+)(?:[-/\\ ]+([0-9/\\,-]+))?', rem)
            if m:
                pref, num, h_raw = m.groups()
                norm_id = normalize_id(pref or "NONE", num)
                
                cond = (item.find("CONDITION").text or "U").upper()
                qty = int(item.find("QTY").text or 0)
                
                h_set = parse_sub_ranges(h_raw)
                for h in h_set:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                
                container_contents[norm_id].append({
                    "id": item.find("ITEMID").text, "cond": cond, "qty": qty, "loc": h_raw or "Main"
                })

    if app_mode == "Gap Auditor":
        tabs = st.tabs([c['name'] for c in st.session_state.temp_categories])
        
        for idx, cat in enumerate(st.session_state.temp_categories):
            with tabs[idx]:
                local_prefix = str(cat['prefix'])
                local_cap = int(cat['cap'])
                
                st.markdown(f"<div class='cat-title'>{cat['name']}</div>", unsafe_allow_html=True)
                
                match_count = 0
                for n in range(int(cat['start']), int(cat['end']) + 1):
                    unit_id = normalize_id(local_prefix, n)
                    unit_data = container_stats.get(unit_id, {})
                    
                    unit_matches = {}
                    for h in range(1, local_cap + 1):
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
                        # CLEAN LABEL LOGIC: No "NONE" and No "Unit"
                        display_prefix = "" if local_prefix.upper() == "NONE" else local_prefix
                        if local_prefix.upper() == "NONE":
                            display_name = f"{n}"
                        else:
                            display_name = f"{display_prefix}{n:03d}"
                        
                        with st.expander(f"{display_name} — {len(unit_matches)} gaps"):
                            if local_cap > 1:
                                grid = "<div>"
                                for h in range(1, local_cap + 1):
                                    if h in unit_matches:
                                        st_cls = "hole-empty" if unit_matches[h]['qty'] == 0 else "hole-low"
                                        grid += f'<div class="hole-box {st_cls}">{h}</div>'
                                    else:
                                        grid += f'<div class="hole-box hole-filled">X</div>'
                                    if h % 10 == 0: grid += "<br>"
                                st.markdown(grid + "</div>", unsafe_allow_html=True)
                            else:
                                m = unit_matches[1]
                                st.write(f"Density: **{m['qty']}** items | Purity: **{m['purity']}**")

                if match_count == 0:
                    st.warning("No storage locations in this category match your search filters.")

    elif app_mode == "Condition Guard":
        conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]
        if not conflicts:
            st.success("✅ Condition Purity: All storage containers are consistent.")
        else:
            for c in sorted(conflicts):
                with st.expander(f"🔴 Conflict: {c}"):
                    for item in container_contents[c]:
                        st.write(f"{item['qty']}x Part {item['id']} ({item['cond']}) @ Hole {item['loc']}")

except Exception as e:
    st.error(f"Logic Error: {e}")