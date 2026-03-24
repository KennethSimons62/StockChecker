import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. VERSION & TRACEABILITY ---
VERSION = "6.2.5 - FINAL STABLE RESTORE"
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
            {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30},
            {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18},
            {"name": "Drawers (D)", "prefix": "D", "start": 1, "end": 38, "cap": 24},
            {"name": "Filing Cabinet", "prefix": "FC", "start": 1, "end": 2, "cap": 25}
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
    .trainer-card { padding: 20px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 20px; }
    .clue-box { background: rgba(99, 102, 241, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #6366f1; margin-top: 10px; color: #a5b4fc; font-size: 1.1rem; font-weight: bold; }
    .status-badge { background-color: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #3b82f6; color: #f8fafc; font-family: monospace; font-size: 0.75rem; margin-bottom: 20px; }
    .cat-header { font-size: 1.5rem; font-weight: bold; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: 20px; }
    .part-row { font-size: 0.85rem; border-left: 2px solid #3b82f6; padding-left: 10px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 5. THE SIDEBAR ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.markdown(f"<div class='status-badge'><b>VERSION: {VERSION}</b></div>", unsafe_allow_html=True)

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
for i in range(len(st.session_state.temp_categories)):
    cat = st.session_state.temp_categories[i]
    with st.sidebar.expander(f"📁 {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"lab_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"pre_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"sta_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"end_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Unit", value=int(cat['cap']), key=f"cap_{i}")

if app_mode == "Gap Auditor":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filters")
    qty_threshold = st.sidebar.number_input("Max Qty to Audit", min_value=0, value=999)
    purity_filter = st.sidebar.selectbox("Condition Focus", ["Show All", "Empty Only", "NEW Only", "USED Only", "Mixed Only"])

# --- 6. CORE LOGIC HELPERS ---
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
            raw_remarks = rem_node.text.strip()
            locations = re.split(r'[/\\,]', raw_remarks)
            for loc_str in locations:
                m = re.search(r'^([A-Za-z]*)\s*(\d+)(?:[-/\\ ]+([0-9/\\,-]+))?', loc_str.strip())
                if m:
                    pref, num, h_raw = m.groups()
                    norm_id = get_clean_id(pref or "", num)
                    cid = str(item.find("COLOR").text)
                    cond = (item.find("CONDITION").text or "U").upper()
                    qty = int(item.find("QTY").text or 0)
                    p_id = item.find("ITEMID").text
                    p_name = CATALOG_LOOKUP.get(p_id, f"Part {p_id}")
                    
                    container_contents[norm_id].append({"id": p_id, "name": p_name, "cid": cid, "cond": cond, "qty": qty, "h": h_raw or "1"})
                    for h in parse_holes(h_raw):
                        container_stats[norm_id][h]["qty"] += qty
                        container_stats[norm_id][h]["conds"].add(cond)
                        container_stats[norm_id][h]["color_ids"].add(cid)

    # --- MODE: GAP AUDITOR ---
    if app_mode == "Gap Auditor":
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
                        hinfo = udata.get(h, {"qty": 0, "conds": set()})
                        state = "EMPTY" if hinfo["qty"] == 0 else ("MIXED" if len(hinfo["conds"]) > 1 else ("NEW" if "N" in hinfo["conds"] else "USED"))
                        if hinfo["qty"] <= qty_threshold:
                            if purity_filter == "Show All" or purity_filter.startswith(state):
                                h_contents = [i for i in container_contents[uid] if str(i['h']) == str(h) or (i['h'] == "1" and h == 1)]
                                umatches[h] = {"qty": hinfo["qty"], "state": state, "items": h_contents}
                    if umatches:
                        tot = sum(m['qty'] for m in umatches.values())
                        label = "EMPTY" if tot == 0 else f"{tot} Parts"
                        with st.expander(f"📦 {pref}{n} — [{label}]"):
                            for h_n, data in umatches.items():
                                st.write(f"**📍 Slot {h_n}** | {data['state']}")
                                for itm in data['items']:
                                    cn = st.session_state.color_map.get(itm['cid'], f"Code {itm['cid']}")
                                    st.markdown(f"<div class='part-row'><b>{itm['qty']}x</b> {itm['name']} ({cn})</div>", unsafe_allow_html=True)

    # --- MODE: CONDITION GUARD (RESTORED FROM v5.6.0) ---
    elif app_mode == "Condition Guard":
        conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]
        if not conflicts:
            st.success("✅ Consistent Conditions.")
        else:
            for c_id in sorted(conflicts):
                with st.expander(f"🔴 Conflict in {c_id}"):
                    for row in container_contents[c_id]:
                        c_n = st.session_state.color_map.get(row['cid'], f"Code {row['cid']}")
                        st.write(f"**{row['qty']}x** {row['name']} — {c_n} ({row['cid']}) [**{row['cond']}**]")

    # --- MODE: COLOR REGISTRY ---
    elif app_mode == "Color Registry":
        # Clue Extraction
        for loc_id, hs in container_stats.items():
            for h_n, stats in hs.items():
                for t_cid in stats['color_ids']:
                    if t_cid not in st.session_state.color_map:
                        for content in container_contents[loc_id]:
                            if content['h'] == str(h_n) or (content['h'] == "1" and h_n == 1):
                                clue = f"<b>{content['name']}</b> at 📍 <b>{loc_id}{' ('+str(h_n)+')' if h_n > 1 else ''}</b>"
                                if clue not in pure_clues_map[t_cid]: pure_clues_map[t_cid].append(clue)

        all_found = sorted(list(pure_clues_map.keys()), key=lambda x: int(x) if x.isdigit() else 999)
        unknowns = [c for c in all_found if c not in st.session_state.color_map]
        
        if unknowns:
            st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
            st.subheader("🔍 Discovery Zone")
            target = unknowns[0]
            clues = pure_clues_map[target]
            if st.session_state.clue_index >= len(clues): st.session_state.clue_index = 0
            c1, col2, col3 = st.columns([1, 2, 1])
            with c1: 
                st.metric("Missing ID", target)
                if st.button("⏭️ Next Clue"):
                    st.session_state.clue_index = (st.session_state.clue_index + 1) % len(clues)
                    st.rerun()
            with col2: 
                t_name = st.text_input("Color Name:", key=f"t_{st.session_state.reset_key}")
                st.markdown(f"<div class='clue-box'>{clues[st.session_state.clue_index]}</div>", unsafe_allow_html=True)
            with col3:
                st.write("")
                if st.button("💾 Save to Registry", use_container_width=True):
                    if t_name:
                        st.session_state.color_map[target] = t_name
                        save_registry(st.session_state.color_map)
                        st.session_state.clue_index = 0
                        trigger_reset(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        h1, h2 = st.columns([2, 1])
        with h1: st.subheader("🎨 Swatch Gallery")
        with h2: search = st.text_input("🔍 Search Registry...", placeholder="ID or Name")
        if st.session_state.color_map:
            all_c = sorted(st.session_state.color_map.keys(), key=lambda x: int(x) if x.isdigit() else 999)
            filt = [c for c in all_c if search.lower() in c or search.lower() in st.session_state.color_map[c].lower()] if search else all_c
            cols = st.columns(12)
            for i, cid in enumerate(filt):
                with cols[i % 12]:
                    img_p = os.path.join(IMAGE_DIR, f"{cid.zfill(3)}.png")
                    if os.path.exists(img_p): st.image(img_p)
                    else: st.markdown(f"<div style='text-align:center; color:#f87171; font-size:0.6rem;'>NO IMG<br>{cid}</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.6rem; font-weight:bold; line-height:1; margin:0;'>{st.session_state.color_map[cid]}</p>", unsafe_allow_html=True)

        with st.expander("⌨️ Manual Entry"):
            m1, m2 = st.columns(2)
            mid = m1.text_input("ID #", key=f"man_id_{st.session_state.reset_key}")
            mna = m2.text_input("Name", key=f"man_na_{st.session_state.reset_key}")
            if st.button("Manual Save"):
                if mid and mna:
                    st.session_state.color_map[str(mid)] = mna
                    save_registry(st.session_state.color_map)
                    trigger_reset(); st.rerun()

except Exception as e:
    st.error(f"Error: {e}")

if st.button("🔄 Clear Upload"):
    st.session_state.xml_data = None
    st.rerun()