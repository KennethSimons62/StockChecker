import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & TRACEABILITY ---
VERSION = "5.5.5 - THE FINAL REFINEMENT"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. FILE SYSTEM & ASSETS ---
REGISTRY_FILE = "color_registry.json"
PROFILE_DIR = "lego_profiles"
IMAGE_DIR = "color_images"

for d in [PROFILE_DIR, IMAGE_DIR]:
    if not os.path.exists(d):
        try: os.makedirs(d)
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

@st.cache_data
def load_parts_catalog():
    if os.path.exists("Parts.txt"):
        try:
            df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1', on_bad_lines='skip')
            return dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
        except: return {}
    return {}

CATALOG_LOOKUP = load_parts_catalog()

# --- 3. SESSION STATE ---
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

if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None
if 'clue_index' not in st.session_state:
    st.session_state.clue_index = 0
if 'reset_key' not in st.session_state:
    st.session_state.reset_key = 0

def trigger_reset():
    st.session_state.reset_key += 1

# --- 4. PAGE STYLE ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .trainer-card { background-color: #1e1b4b; padding: 25px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 20px; color: white; }
    .clue-box { background: rgba(99, 102, 241, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #6366f1; margin-top: 10px; color: #a5b4fc; }
    .status-badge { background-color: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #3b82f6; color: #f8fafc; font-family: monospace; font-size: 0.75rem; margin-bottom: 20px; }
    .cat-header { font-size: 1.5rem; font-weight: bold; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: 20px; }
    
    /* COMPACT SWATCH GRID */
    .gallery-label {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        text-align: center;
        margin-top: 4px;
        line-height: 1.1;
        display: block;
    }
    .swatch-box-mini {
        border: 1px solid #334155;
        background: #0f172a;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        min-height: 130px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. THE SIDEBAR (PERMANENT TOP PRIORITY) ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-badge'><b>LIVE VERSION: {VERSION}</b><br>Saved: {LAST_MODIFIED}</div>", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard", "Color Registry"])

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Profile Commander")
def get_profile_list():
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default"]

profiles = get_profile_list()
selected_p = st.sidebar.selectbox("Load Profile", profiles, index=profiles.index(st.session_state.active_profile) if st.session_state.active_profile in profiles else 0)

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    path = os.path.join(PROFILE_DIR, f"{selected_p}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            st.session_state.temp_categories = json.load(f)
    st.rerun()

new_p_name = st.sidebar.text_input("Profile Name", value=st.session_state.active_profile)
if st.sidebar.button("💾 SAVE PROFILE"):
    path = os.path.join(PROFILE_DIR, f"{new_p_name}.json")
    with open(path, "w") as f:
        json.dump(st.session_state.temp_categories, f, indent=4)
    st.session_state.active_profile = new_p_name
    st.sidebar.success("Saved!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Layout Editor")
for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"sidebar_lab_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"sidebar_pre_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"sidebar_sta_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"sidebar_end_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Unit", value=int(cat['cap']), key=f"sidebar_cap_{i}")

if app_mode in ["Gap Auditor", "Condition Guard"]:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Search Filters")
    qty_threshold = st.sidebar.number_input("Max Qty / Slot", min_value=0, value=0)
    purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "New Only", "Used Only"])

# --- 6. CORE LOGIC HELPERS ---
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

# --- 7. MAIN CONTENT FLOW ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    uploaded_xml = st.file_uploader("Upload store.xml to begin:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

# --- 8. THE DATA ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set(), "color_ids": set()}))
    container_contents = defaultdict(list)
    pure_clues_map = defaultdict(list) 

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
                cid = str(item.find("COLOR").text)
                p_id = item.find("ITEMID").text
                p_name = CATALOG_LOOKUP.get(p_id, "Unknown Part")
                
                container_contents[norm_id].append({"id": p_id, "name": p_name, "cid": cid, "cond": cond, "qty": qty, "h": h_raw or "1"})
                
                h_set = parse_holes(h_raw)
                for h in h_set:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                    container_stats[norm_id][h]["color_ids"].add(cid)

    for loc_id, holes in container_stats.items():
        for hole_num, stats in holes.items():
            if len(stats['color_ids']) == 1:
                target_cid = list(stats['color_ids'])[0]
                for content in container_contents[loc_id]:
                    if content['h'] == str(hole_num) or (content['h'] == "1" and hole_num == 1):
                        clue_str = f"<b>{content['name']}</b> @ 📍 <b>{loc_id}{' ('+str(hole_num)+')' if hole_num > 1 else ''}</b>"
                        if clue_str not in pure_clues_map[target_cid]:
                            pure_clues_map[target_cid].append(clue_str)

    # --- MODE: COLOR REGISTRY ---
    if app_mode == "Color Registry":
        all_xml_cids = set(pure_clues_map.keys())
        unknowns = [c for c in all_xml_cids if c not in st.session_state.color_map]
        
        # Discovery Zone
        if unknowns:
            st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
            st.subheader("🔍 Discovery Zone")
            target_cid = unknowns[0]
            clues = pure_clues_map[target_cid]
            if st.session_state.clue_index >= len(clues): st.session_state.clue_index = 0
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.metric("ID Found", target_cid)
                if st.button("⏭️ NEXT PURE CLUE"):
                    st.session_state.clue_index = (st.session_state.clue_index + 1) % len(clues)
                    st.rerun()
            with col2:
                train_name = st.text_input(f"Friendly Name:", key=f"reg_train_{st.session_state.reset_key}")
                st.markdown(f"<div class='clue-box'>{clues[st.session_state.clue_index]}</div>", unsafe_allow_html=True)
            with col3:
                st.write("")
                if st.button("💾 SAVE NAME", use_container_width=True):
                    if train_name:
                        st.session_state.color_map[target_cid] = train_name
                        save_registry(st.session_state.color_map)
                        st.session_state.clue_index = 0
                        trigger_reset()
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("🎨 Swatch Gallery")
        if st.session_state.color_map:
            cols = st.columns(10) 
            sorted_cids = sorted(st.session_state.color_map.keys(), key=lambda x: int(x) if x.isdigit() else 999)
            for i, cid in enumerate(sorted_cids):
                with cols[i % 10]:
                    try: padded = f"{int(cid):03d}"
                    except: padded = cid
                    img_path = os.path.join(IMAGE_DIR, f"{padded}.png")
                    
                    st.markdown("<div class='swatch-box-mini'>", unsafe_allow_html=True)
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=False, width=60)
                    else:
                        st.caption(f"{padded}.png")
                    
                    st.markdown(f"<div class='gallery-label'>{st.session_state.color_map[cid]} ({cid})</div></div>", unsafe_allow_html=True)

        with st.expander("⌨️ Manual Registry Entry"):
            m1, m2 = st.columns(2)
            mid = m1.text_input("ID #", key=f"man_id_{st.session_state.reset_key}")
            mna = m2.text_input("Name", key=f"man_na_{st.session_state.reset_key}")
            if st.button("Manual Save"):
                if mid and mna:
                    st.session_state.color_map[str(mid)] = mna
                    save_registry(st.session_state.color_map)
                    trigger_reset()
                    st.rerun()

    # --- MODE: GAP AUDITOR ---
    elif app_mode == "Gap Auditor":
        tabs = st.tabs([c['name'] for c in st.session_state.temp_categories])
        for idx, cat in enumerate(st.session_state.temp_categories):
            with tabs[idx]:
                pref, cap = str(cat['prefix']).upper().strip(), int(cat['cap'])
                st.markdown(f"<div class='cat-header'>{cat['name']}</div>", unsafe_allow_html=True)
                for n in range(int(cat['start']), int(cat['end']) + 1):
                    uid = get_clean_id(pref, n)
                    udata = container_stats.get(uid, {})
                    umatches = {}
                    for h in range(1, cap + 1):
                        hinfo = udata.get(h, {"qty": 0, "conds": set(), "color_ids": set()})
                        if hinfo["qty"] <= qty_threshold:
                            p_st = "EMPTY" if not hinfo["conds"] else "NEW" if "N" in hinfo["conds"] else "USED"
                            if purity_filter == "Show All" or purity_filter.upper().startswith(p_st):
                                umatches[h] = {"cids": hinfo["color_ids"]}
                    if umatches:
                        with st.expander(f"{pref}{n:03d} — {len(umatches)} slots"):
                            for h_n, m_d in umatches.items():
                                names = [st.session_state.color_map.get(cid, f"Code {cid}") + f" ({cid})" for cid in m_d['cids']]
                                st.write(f"📍 Slot {h_n}: {', '.join(names)}")

    # --- MODE: CONDITION GUARD ---
    elif app_mode == "Condition Guard":
        conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]
        if not conflicts: st.success("✅ Consistent.")
        else:
            for c_id in sorted(conflicts):
                with st.expander(f"🔴 Conflict in {c_id}"):
                    for row in container_contents[c_id]:
                        c_n = st.session_state.color_map.get(row['cid'], f"Code {row['cid']}")
                        st.write(f"**{row['qty']}x** {row['name']} — {c_n} ({row['cid']}) [**{row['cond']}**]")

except Exception as e:
    st.error(f"Error: {e}")

if st.button("🔄 Clear Upload"):
    st.session_state.xml_data = None
    st.rerun()