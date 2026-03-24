import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict

# --- 1. ASSETS & CONFIG ---
REGISTRY_FILE = "color_registry.json"
PROFILE_DIR = "lego_profiles"

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

@st.cache_data
def load_parts_catalog():
    if os.path.exists("Parts.txt"):
        try:
            df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1', on_bad_lines='skip')
            return dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
        except: return {}
    return {}

COLOR_MAP = load_registry()
CATALOG_LOOKUP = load_parts_catalog()

# --- 2. SESSION STATE & PROFILES ---
if 'active_profile' not in st.session_state:
    st.session_state.active_profile = "Default"

if 'temp_categories' not in st.session_state:
    path = os.path.join(PROFILE_DIR, f"{st.session_state.active_profile}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            st.session_state.temp_categories = json.load(f)
    else:
        st.session_state.temp_categories = [
            {"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1},
            {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
            {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
            {"name": "Drawers (D)", "prefix": "D", "start": 1, "end": 38, "cap": 24},
            {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
        ]

# --- 3. PAGE UI ---
st.header("🔍 Gap Auditor")

if not st.session_state.xml_data:
    st.warning("Please upload a store.xml on the Home page.")
    st.stop()

# --- 4. SIDEBAR TOOLS ---
with st.sidebar:
    st.subheader("🔍 Audit Filters")
    qty_threshold = st.number_input("Max Qty to Show", min_value=0, value=999)
    purity_filter = st.selectbox("Condition Focus", ["Show All", "Empty Only", "NEW Only", "USED Only", "Mixed Only"])
    
    st.markdown("---")
    st.subheader("🛠️ Layout Editor")
    for i in range(len(st.session_state.temp_categories)):
        cat = st.session_state.temp_categories[i]
        with st.sidebar.expander(f"📁 {cat['name']}"):
            st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"gap_lab_{i}")
            st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"gap_pre_{i}")
            st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"gap_sta_{i}")
            st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"gap_end_{i}")
            st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Unit", value=int(cat['cap']), key=f"gap_cap_{i}")

# --- 5. LOGIC HELPERS ---
def get_clean_id(prefix, number):
    try: return f"{prefix.upper().strip()}{int(number)}"
    except: return f"{prefix}{number}"

def parse_holes(expr):
    holes = set()
    if not expr: return {1}
    clean = str(expr).replace('/', '-').replace('\\', '-').replace(' ', '')
    for p in re.split(r'[,;]+', clean):
        if not p: continue
        try:
            if '-' in p:
                pts = p.split('-')
                holes.update(range(int(pts[0]), int(pts[1]) + 1))
            else: holes.add(int(p))
        except: continue
    return holes if holes else {1}

# --- 6. DATA PROCESSING ---
root = ET.fromstring(st.session_state.xml_data)
items = root.findall(".//ITEM")

container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set(), "items": []}))

for item in items:
    rem_node = item.find("REMARKS")
    if rem_node is not None and rem_node.text:
        locations = re.split(r'[/\\,]', rem_node.text.strip())
        for loc_str in locations:
            m = re.search(r'^([A-Za-z]*)\s*(\d+)(?:[-/\\ ]+([0-9/\\,-]+))?', loc_str.strip())
            if m:
                pref, num, h_raw = m.groups()
                norm_id = get_clean_id(pref or "", num)
                cond = (item.find("CONDITION").text or "U").upper()
                qty = int(item.find("QTY").text or 0)
                p_id = item.find("ITEMID").text
                p_name = CATALOG_LOOKUP.get(p_id, f"Part {p_id}")
                
                h_set = parse_holes(h_raw)
                for h in h_set:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                    container_stats[norm_id][h]["items"].append({
                        "name": p_name, "qty": qty, "cond": cond, "cid": item.find("COLOR").text
                    })

# --- 7. RESULTS DISPLAY ---
tabs = st.tabs([c['name'] for c in st.session_state.temp_categories])
for idx, cat in enumerate(st.session_state.temp_categories):
    with tabs[idx]:
        pref, cap = str(cat['prefix']).upper().strip(), int(cat['cap'])
        
        for n in range(int(cat['start']), int(cat['end']) + 1):
            uid = get_clean_id(pref, n)
            udata = container_stats.get(uid, {})
            umatches = {}
            
            for h in range(1, cap + 1):
                hinfo = udata.get(h, {"qty": 0, "conds": set()})
                if hinfo["qty"] == 0: c_state = "EMPTY"
                elif len(hinfo["conds"]) > 1: c_state = "MIXED"
                elif "N" in hinfo["conds"]: c_state = "NEW"
                else: c_state = "USED"

                if hinfo["qty"] <= qty_threshold:
                    if (purity_filter == "Show All") or (purity_filter.startswith(c_state.split()[0])):
                        umatches[h] = {"qty": hinfo["qty"], "state": c_state, "items": hinfo.get("items", [])}
            
            if umatches:
                total_parts = sum(m['qty'] for m in umatches.values())
                label = "EMPTY" if total_parts == 0 else f"{total_parts} Parts"
                with st.expander(f"📦 {pref}{n} — [{label}]"):
                    for h_n, data in umatches.items():
                        st.write(f"**📍 Slot {h_n}** | Condition: {data['state']}")
                        for itm in data['items']:
                            c_name = COLOR_MAP.get(itm['cid'], f"Color {itm['cid']}")
                            st.write(f"  * {itm['qty']}x {itm['name']} ({c_name})")