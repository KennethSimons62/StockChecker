import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os  # <--- This was the missing piece causing your error
import pandas as pd
from collections import defaultdict

def load_storage_tags():
    if os.path.exists("storage_conditions.json"):
        with open("storage_conditions.json", "r") as f:
            return json.load(f)
    return {}

STORAGE_TAGS = load_storage_tags() # Load the NEW/USED rules

# --- 1. PAGE CONFIG & SLEEK NAV ---
st.set_page_config(page_title="Gap Auditor", page_icon="🔍", layout="wide")

# Minimalist Navigation Bar (No black boxes)
nav_cols = st.columns(5)
nav_cols[0].page_link("home.py", label="HOME HUB", icon="🏠")
nav_cols[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav_cols[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav_cols[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav_cols[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
st.divider()

# --- 2. ASSETS & DIRECTORY CHECKS ---
REGISTRY_FILE = "color_registry.json"
PROFILE_DIR = "lego_profiles"

if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

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

# --- 3. SESSION STATE & PROFILE COMMANDER ---
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
            {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30}
        ]

with st.sidebar:
    st.header("📂 Profile Commander")
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    profiles = sorted(files) if files else ["Default"]
    
    selected_p = st.selectbox("Load Profile", profiles, index=profiles.index(st.session_state.active_profile) if st.session_state.active_profile in profiles else 0)

    if selected_p != st.session_state.active_profile:
        st.session_state.active_profile = selected_p
        path = os.path.join(PROFILE_DIR, f"{selected_p}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                st.session_state.temp_categories = json.load(f)
        st.rerun()

    new_p_name = st.text_input("Profile Name", value=st.session_state.active_profile)
    if st.button("💾 SAVE PROFILE"):
        path = os.path.join(PROFILE_DIR, f"{new_p_name}.json")
        with open(path, "w") as f:
            json.dump(st.session_state.temp_categories, f, indent=4)
        st.session_state.active_profile = new_p_name
        st.success("Profile Saved!")
        st.rerun()

    st.markdown("---")
    st.header("🛠️ Layout Editor")
    for i in range(len(st.session_state.temp_categories)):
        cat = st.session_state.temp_categories[i]
        with st.expander(f"📁 {cat['name']}"):
            st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"edit_lab_{i}")
            st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"edit_pre_{i}")
            st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"edit_sta_{i}")
            st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"edit_end_{i}")
            st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Unit", value=int(cat['cap']), key=f"edit_cap_{i}")

    if st.button("➕ ADD NEW STORAGE"):
        st.session_state.temp_categories.append({"name": "New Storage", "prefix": "X", "start": 1, "end": 10, "cap": 1})
        st.rerun()

    if len(st.session_state.temp_categories) > 1:
        if st.button("🗑️ REMOVE LAST"):
            st.session_state.temp_categories.pop()
            st.rerun()

    st.markdown("---")
    st.header("🔍 Audit Filters")
    qty_threshold = st.number_input("Max Qty to Show", min_value=0, value=0)
    purity_filter = st.selectbox("Condition Focus", ["Show All", "Empty Only", "NEW Only", "USED Only", "Mixed Only"])

# --- 4. DATA ENGINE ---
if not st.session_state.get('xml_data'):
    st.warning("⚪ No Store Data. Please go to the HOME HUB to upload your XML.")
    st.stop()

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

# --- 5. CLEAN RESULTS ---
st.subheader("🔍 Gap Audit Results")
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
                icon = "🆓" if total_parts == 0 else "🧱"
                label = "EMPTY" if total_parts == 0 else f"{total_parts} Parts"
                
                with st.expander(f"{icon} {pref}{n} — [{label}]"):
                    for h_n, data in umatches.items():
                        st.markdown(f"**📍 Slot {h_n}** | `{data['state']}`")
                        for itm in data['items']:
                            c_name = COLOR_MAP.get(itm['cid'], f"Color {itm['cid']}")
                            st.write(f"  * {itm['qty']}x {itm['name']} ({c_name})")

# --- 6. UPGRADED AUDIT RESULTS ---
st.subheader("🔍 Gap Audit & Purity Check")
tabs = st.tabs([c['name'] for c in st.session_state.temp_categories])

for idx, cat in enumerate(st.session_state.temp_categories):
    with tabs[idx]:
        pref = str(cat['prefix']).upper().strip()
        cap = int(cat['cap'])
        
        for n in range(int(cat['start']), int(cat['end']) + 1):
            uid = get_clean_id(pref, n)
            
            # --- PURITY LOGIC ---
            # What IS the unit supposed to be? (From your Config page)
            assigned_cond = STORAGE_TAGS.get(uid, "NOT SET") 
            
            udata = container_stats.get(uid, {})
            umatches = {}
            has_purity_error = False

            for h in range(1, cap + 1):
                hinfo = udata.get(h, {"qty": 0, "conds": set(), "items": []})
                
                # Determine current status of the slot
                if hinfo["qty"] == 0: c_state = "EMPTY"
                elif len(hinfo["conds"]) > 1: c_state = "MIXED"
                elif "N" in hinfo["conds"]: c_state = "NEW"
                else: c_state = "USED"

                # Check for Purity Conflict:
                # If the unit is tagged "NEW" but the slot has "USED" parts (or vice-versa)
                if assigned_cond != "NOT SET" and c_state not in ["EMPTY", "MIXED"]:
                    if c_state != assigned_cond:
                        has_purity_error = True

                # Filter logic
                if hinfo["qty"] <= qty_threshold:
                    if (purity_filter == "Show All") or (purity_filter.startswith(c_state.split()[0])):
                        umatches[h] = {"qty": hinfo["qty"], "state": c_state, "items": hinfo["items"]}

            # --- RENDER THE BOX ---
            if umatches:
                total_parts = sum(m['qty'] for m in umatches.values())
                
                # Visual Alerts
                label_prefix = "⚠️ PURITY ERROR" if has_purity_error else "✅"
                if total_parts == 0: 
                    icon, label = "🆓", "EMPTY UNIT"
                else: 
                    icon, label = "🧱", f"{total_parts} Parts ({assigned_cond})"

                # The Expander header changes color/text if there's a mismatch
                with st.expander(f"{label_prefix} {icon} {uid} — {label}"):
                    if has_purity_error:
                        st.error(f"🚨 **CONFLICT:** This unit is designated as **{assigned_cond}**, but contains items marked otherwise!")
                    
                    for h_n, data in umatches.items():
                        col_a, col_b = st.columns([1, 4])
                        col_a.markdown(f"**Slot {h_n}**")
                        
                        # Color code the slot state
                        s_color = "green" if data['state'] == assigned_cond else "red"
                        if data['state'] == "EMPTY": s_color = "gray"
                        
                        col_b.markdown(f":{s_color}[{data['state']}]")
                        
                        for itm in data['items']:
                            c_name = COLOR_MAP.get(itm['cid'], f"ID {itm['cid']}")
                            st.caption(f"↳ {itm['qty']}x {itm['name']} ({c_name})")