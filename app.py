import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & TRACEABILITY ---
VERSION = "5.0.0 - THE COLOR COMMANDER"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
SCRIPT_PATH = os.path.abspath(__file__)
LAST_MODIFIED = datetime.fromtimestamp(os.path.getmtime(SCRIPT_PATH)).strftime('%Y-%m-%d %H:%M:%S')

# --- 2. MEMORY ENGINE ---
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

@st.cache_data
def load_parts_catalog():
    if os.path.exists("Parts.txt"):
        try:
            df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1')
            return dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
        except: return {}
    return {}

CATALOG_LOOKUP = load_parts_catalog()

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

# --- 4. SESSION STATE ---
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
if 'clue_index' not in st.session_state:
    st.session_state.clue_index = 0

# --- 5. PAGE STYLE ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide")

st.markdown("""
    <style>
    .trainer-card { background-color: #1e1b4b; padding: 25px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 20px; }
    .clue-box { background: rgba(99, 102, 241, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #6366f1; margin-top: 10px; }
    .status-badge { background-color: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #3b82f6; color: #f8fafc; font-family: monospace; font-size: 0.75rem; margin-bottom: 20px; }
    .hole-box { display: inline-block; width: 30px; height: 30px; margin: 2px; border-radius: 4px; text-align: center; font-size: 10px; line-height: 30px; font-weight: bold; color: white; border: 1px solid rgba(255,255,255,0.1); }
    .hole-empty { background-color: #10b981; }
    .hole-low { background-color: #f59e0b; }
    .hole-filled { background-color: #ef4444; opacity: 0.15; }
    .cat-header { font-size: 1.5rem; font-weight: bold; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-badge'><b>LIVE VERSION: {VERSION}</b><br>Saved: {LAST_MODIFIED}</div>", unsafe_allow_html=True)

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard", "Color Registry"], index=0)

if app_mode in ["Gap Auditor", "Condition Guard"]:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Audit Filters")
    qty_threshold = st.sidebar.number_input("Max Qty / Slot", min_value=0, value=0)
    purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "New Only", "Used Only"])

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Profiles & Layout")
profiles = get_profile_list()
selected_p = st.sidebar.selectbox("Load Profile", profiles, index=profiles.index(st.session_state.active_profile) if st.session_state.active_profile in profiles else 0)

# Profile Logic
if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    path = os.path.join(PROFILE_DIR, f"{selected_p}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            st.session_state.temp_categories = json.load(f)
    st.rerun()

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
    uploaded_xml = st.file_uploader("Upload store.xml to start:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

# --- 9. THE ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set(), "color_ids": set()}))
    container_contents = defaultdict(list)
    
    # Map ColorID -> List of PURE locations (locations with only ONE color)
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
                
                container_contents[norm_id].append({
                    "id": p_id, "name": p_name, "cid": cid, "cond": cond, "qty": qty, "h": h_raw or "1"
                })
                
                h_set = parse_holes(h_raw)
                for h in h_set:
                    container_stats[norm_id][h]["qty"] += qty
                    container_stats[norm_id][h]["conds"].add(cond)
                    container_stats[norm_id][h]["color_ids"].add(cid)

    # Secondary Pass: Find clues that are UNIQUE to a location
    for loc_id, holes in container_stats.items():
        for hole_num, stats in holes.items():
            if len(stats['color_ids']) == 1: # PURE LOCATION DETECTED
                target_cid = list(stats['color_ids'])[0]
                # Find the first item name in this pure location
                for content in container_contents[loc_id]:
                    if content['h'] == str(hole_num) or (content['h'] == "1" and hole_num == 1):
                        clue_str = f"<b>{content['name']}</b> (ID: {content['id']}) @ 📍 <b>{loc_id}{' (Hole '+str(hole_num)+')' if hole_num > 1 else ''}</b>"
                        if clue_str not in pure_clues_map[target_cid]:
                            pure_clues_map[target_cid].append(clue_str)

    # --- 💡 MODE: COLOR REGISTRY ---
    if app_mode == "Color Registry":
        st.info("Assign names to BrickLink color codes found in your inventory.")
        
        # Part A: The Trainer (Unknowns)
        unknowns = [c for c in pure_clues_map.keys() if c not in st.session_state.color_map]
        
        if unknowns:
            st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
            st.subheader("🔍 Unknown Color Discovery")
            
            target_cid = unknowns[0]
            clues = pure_clues_map[target_cid]
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.metric("Found ID", target_cid)
                if st.button("⏭️ NEXT PURE CLUE", use_container_width=True):
                    st.session_state.clue_index = (st.session_state.clue_index + 1) % len(clues)
                    st.rerun()
            
            with col2:
                train_name = st.text_input(f"Name for {target_cid}:", key="train_inp")
                if st.session_state.clue_index >= len(clues): st.session_state.clue_index = 0
                st.markdown(f"<div class='clue-box'><b>Unique Clue:</b><br>{clues[st.session_state.clue_index]}</div>", unsafe_allow_html=True)
            
            with col3:
                st.write("")
                if st.button("✅ LEARN NAME", use_container_width=True):
                    if train_name:
                        st.session_state.color_map[target_cid] = train_name
                        save_registry(st.session_state.color_map)
                        st.session_state.clue_index = 0
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.success("All colors in this XML are recognized!")

        # Part B: Proactive & List
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("➕ Manual Addition")
            m_id = st.text_input("Color ID #", placeholder="e.g. 11")
            m_name = st.text_input("Friendly Name", placeholder="e.g. Black")
            if st.button("Add to Registry"):
                if m_id and m_name:
                    st.session_state.color_map[str(m_id)] = m_name
                    save_registry(st.session_state.color_map)
                    st.rerun()

        with col_right:
            st.subheader("📋 Registry List")
            # Convert to DataFrame for a nice scrollable list
            if st.session_state.color_map:
                reg_df = pd.DataFrame(list(st.session_state.color_map.items()), columns=["ID", "Name"])
                st.dataframe(reg_df.sort_values(by="ID"), hide_index=True, use_container_width=True, height=300)
            else:
                st.write("Registry is empty.")

    # --- 💡 MODE: GAP AUDITOR ---
    elif app_mode == "Gap Auditor":
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
                if match_count == 0: st.warning("No matches.")

    # --- 💡 MODE: CONDITION GUARD ---
    elif app_mode == "Condition Guard":
        conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]
        if not conflicts:
            st.success("✅ Condition Purity: All containers consistent.")
        else:
            for c_id in sorted(conflicts):
                with st.expander(f"🔴 Conflict: {c_id}"):
                    for row in container_contents[c_id]:
                        c_name = st.session_state.color_map.get(row['cid'], f"Code {row['cid']}")
                        st.write(f"**{row['qty']}x** {row['name']} — {c_name} (**{row['cond']}**) @ Hole {row['h']}")

except Exception as e:
    st.error(f"Error: {e}")

if st.button("🔄 Clear and Restart"):
    st.session_state.xml_data = None
    st.session_state.clue_index = 0
    st.rerun()