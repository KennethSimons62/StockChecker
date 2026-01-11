import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- APP METADATA ---
VERSION = "1.8.2"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"

# --- CATALOG LOADING ---
@st.cache_data
def load_internal_catalog():
    if os.path.exists("parts.txt"):
        try:
            df_ref = pd.read_csv("parts.txt", sep='\t', encoding='latin1')
            return dict(zip(df_ref.iloc[:, 2].astype(str), df_ref.iloc[:, 3]))
        except: return {}
    return {}

CATALOG_LOOKUP = load_internal_catalog()

# --- HELPER FUNCTIONS ---
def get_file_info(filepath):
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        dt_mtime = datetime.fromtimestamp(mtime)
        now = datetime.now()
        diff = now - dt_mtime
        if diff.days > 0: age_str = f"{diff.days} days ago"
        elif diff.seconds // 3600 > 0: age_str = f"{diff.seconds//3600} hours ago"
        else: age_str = f"{diff.seconds//60} mins ago"
        return dt_mtime.strftime("%d-%b %Y %H:%M"), age_str, diff.days
    return None, None, None

def parse_sub_ranges(range_expr):
    found_holes = set()
    std = str(range_expr).replace('/', '-').replace('\\', '-')
    for part in re.split(r'[,\s]+', std):
        part = part.strip()
        if not part or not any(char.isdigit() for char in part): continue
        if '-' in part:
            try:
                s_str, e_str = part.split('-', 1)
                found_holes.update(range(int(s_str), int(e_str) + 1))
            except: continue
        else:
            try: found_holes.add(int(part))
            except: continue
    return found_holes

def holes_to_ranges(numbers):
    if not numbers: return []
    numbers = sorted(list(numbers))
    ranges = []
    start = prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1: prev = n
        else:
            ranges.append((start, prev)); start = prev = n
    ranges.append((start, prev))
    return [f"{s:02d}-{e:02d}" if s != e else f"{s:02d}" for s, e in ranges]

def parse_location_detail(remark):
    """Extracts the specific hole/slot from the remark."""
    parts = re.split(r'[- ]', remark.strip(), 1)
    if len(parts) > 1:
        return parts[1]
    return "Main"

def get_profile_list():
    if not os.path.exists("lego_profiles"): os.makedirs("lego_profiles")
    files = [f.replace(".json", "") for f in os.listdir("lego_profiles") if f.endswith(".json")]
    return sorted(files) if files else ["Default_Store"]

def load_profile_file(name):
    path = os.path.join("lego_profiles", f"{name}.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return [{"name": "Wall Drawers", "prefix": "", "start": 1, "end": 100, "cap": 1, "is_wall": True}]

def save_profile_file(name, data):
    path = os.path.join("lego_profiles", f"{name}.json")
    with open(path, "w") as f: json.dump(data, f, indent=4)

# --- APP SETUP ---
st.set_page_config(page_title=f"LEGO Auditor - {DEVELOPER}", layout="wide", page_icon="🧱")

if 'expanded_index' not in st.session_state: st.session_state.expanded_index = None

# --- SIDEBAR ---
st.sidebar.markdown(f"### 🧱 LEGO Master Auditor")
st.sidebar.caption(f"v{VERSION} | {DEVELOPER}")
st.sidebar.divider()

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])
st.sidebar.divider()

profile_list = get_profile_list()
if 'active_profile' not in st.session_state: st.session_state.active_profile = profile_list[0]
selected_p = st.sidebar.selectbox("Active Store Profile:", profile_list, index=profile_list.index(st.session_state.active_profile))

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    st.session_state.temp_categories = load_profile_file(selected_p)
    st.session_state.expanded_index = None
    st.rerun()

if 'temp_categories' not in st.session_state:
    st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)

# --- MAIN CONTENT ---
st.title(f"🧱 {app_mode}")
XML_FILE = "store.xml"
file_ts, file_age, days_old = get_file_info(XML_FILE)

if file_ts:
    age_color = "red" if days_old >= 1 else "green"
    st.info(f"📁 **Auto-Loaded:** `{XML_FILE}`")
    st.markdown(f"**Last Modified:** {file_ts} (<span style='color:{age_color}; font-weight:bold;'>{file_age}</span>)", unsafe_allow_html=True)
    
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        items = root.findall(".//ITEM")

        container_contents = defaultdict(list)
        container_conditions = defaultdict(set)
        all_remarks = []

        for item in items:
            rem_node = item.find("REMARKS")
            if rem_node is not None and rem_node.text:
                rem_text = rem_node.text.strip()
                all_remarks.append(rem_text)
                drawer_id = re.split(r'[-/\\ ]', rem_text)[0]
                cond = (item.find("CONDITION").text or "U").upper()
                qty = int(item.find("QTY").text if item.find("QTY") is not None else 0)
                container_conditions[drawer_id].add(cond)
                
                p_id = item.find("ITEMID").text
                p_desc = CATALOG_LOOKUP.get(p_id, item.find("ITEMNAME").text if item.find("ITEMNAME") is not None else p_id)
                container_contents[drawer_id].append({
                    "id": p_id, "desc": p_desc, "cond": cond, "qty": qty, 
                    "loc": parse_location_detail(rem_text)
                })

        # --- GAP AUDITOR ---
        if app_mode == "Gap Auditor":
            audit_results = {}
            for cat in st.session_state.temp_categories:
                prefix = cat['prefix']
                pat = r"\b(\d{4})\b" if cat.get('is_wall') else rf"{prefix}(\d+)(?:-([0-9/\\-]+))?"
                found = defaultdict(set)
                for txt in all_remarks:
                    for m in re.findall(pat, txt):
                        if cat.get('is_wall'): found[int(m)].add(1)
                        else:
                            num_id, r_ex = m
                            if r_ex: found[int(num_id)].update(parse_sub_ranges(r_ex))
                            else: found[int(num_id)].add(1)

                missing = []
                total_range = range(int(cat['start']), int(cat['end']) + 1)
                filled_slots = 0
                total_slots = len(total_range) * int(cat['cap'])
                for n in total_range:
                    occ = found[n]
                    filled_slots += len([s for s in occ if s <= int(cat['cap'])])
                    miss_holes = sorted(list(set(range(1, int(cat['cap']) + 1)) - occ))
                    if miss_holes: missing.append((n, miss_holes))
                audit_results[cat['name']] = {"missing": missing, "pct": (filled_slots/total_slots if total_slots > 0 else 0)}

            cols = st.columns(len(audit_results))
            for i, (name, data) in enumerate(audit_results.items()):
                cols[i].metric(name, f"{int(data['pct']*100)}%")
                cols[i].progress(data['pct'])

            tabs = st.tabs([cat['name'] for cat in st.session_state.temp_categories])
            for i, cat in enumerate(st.session_state.temp_categories):
                with tabs[i]:
                    res = audit_results[cat['name']]
                    if not res['missing']: st.success("✅ Clean!")
                    else:
                        for idx, (num, gaps) in enumerate(res['missing']):
                            lbl = f"{cat['prefix']}{num:03d}" if not cat.get('is_wall') else f"{num:04d}"
                            unique_key = f"gap_{cat['name']}_{num}"
                            is_expanded = (st.session_state.expanded_index == unique_key)
                            with st.expander(f"Unit {lbl} - {len(gaps)} gaps", expanded=is_expanded):
                                st.write(f"Missing holes: {', '.join(holes_to_ranges(gaps))}")
                                if st.button("Focus", key=f"btn_{unique_key}"):
                                    st.session_state.expanded_index = unique_key
                                    st.rerun()

        # --- CONDITION GUARD ---
        elif app_mode == "Condition Guard":
            conflicts = sorted([k for k, v in container_conditions.items() if len(v) > 1])
            if not conflicts: st.success("✅ Clean!")
            else:
                st.error(f"Found {len(conflicts)} Mixed Containers")
                for drawer in conflicts:
                    unique_key = f"cond_{drawer}"
                    is_expanded = (st.session_state.expanded_index == unique_key)
                    with st.expander(f"🔴 Conflict: {drawer}", expanded=is_expanded):
                        c1, c2 = st.columns(2)
                        for cond, col in zip(['N', 'U'], [c1, c2]):
                            with col:
                                drawer_items = [x for x in container_contents[drawer] if x['cond'] == cond]
                                total_qty = sum(item['qty'] for item in drawer_items)
                                st.markdown(f"**{'🆕 NEW' if cond == 'N' else '📜 USED'}** ({total_qty} pcs)")
                                for p in drawer_items:
                                    st.write(f"**{p['qty']}x** {p['desc']}")
                                    st.caption(f"📍 Hole: **{p['loc']}** | ID: {p['id']}")
                                    st.divider()
                        if st.button("Focus", key=f"focus_{drawer}"):
                            st.session_state.expanded_index = unique_key
                            st.rerun()

    except Exception as e:
        st.error(f"Error processing XML: {e}")
else:
    st.warning("⚠️ **store.xml not found!** Ensure your file is named exactly 'store.xml' in the script folder.")

# --- SIDEBAR EDITOR ---
st.sidebar.divider()
st.sidebar.subheader("🛠️ Profile Editor")
for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 Edit {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"n_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"p_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"s_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"e_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Drawer", value=int(cat.get('cap', 1)), key=f"c_{i}")
        st.session_state.temp_categories[i]['is_wall'] = st.checkbox("4-digit", value=cat.get('is_wall', False), key=f"w_{i}")

if st.sidebar.button("💾 SAVE PROFILE", type="primary", use_container_width=True):
    save_profile_file(st.session_state.active_profile, st.session_state.temp_categories)
    st.sidebar.success("Saved!")