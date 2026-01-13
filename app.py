import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime
import io

# --- 1. APP CONFIG & CONSTANTS ---
VERSION = "1.9.4"
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????"  #

# Ensure the profile directory exists immediately
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# --- 2. HELPER FUNCTIONS ---

def get_profile_list():
    """Scans the profile directory for JSON files."""
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    # Changed fallback name to "Default"
    return sorted(files) if files else ["Default"]

def load_profile_file(name):
    """Loads a profile from disk or returns a default template."""
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            pass
    # Default data provided to give users a headstart
    return [{"name": "Standard Drawers", "prefix": "", "start": 1, "end": 1107, "cap": 1, "is_wall": False}]

def save_profile_file(name, data):
    """Saves the current configuration to a JSON file on the server."""
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def parse_sub_ranges(range_expr):
    """Parses ranges like '1-5, 10' into a set of integers."""
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
    """Converts a set of numbers back into a readable range string (e.g., 01-05)."""
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

@st.cache_data
def load_internal_catalog():
    """Loads parts.txt if it exists for better part descriptions."""
    if os.path.exists("parts.txt"):
        try:
            df_ref = pd.read_csv("parts.txt", sep='\t', encoding='latin1')
            return dict(zip(df_ref.iloc[:, 2].astype(str), df_ref.iloc[:, 3]))
        except: return {}
    return {}

CATALOG_LOOKUP = load_internal_catalog()

# --- 3. SESSION STATE INITIALIZATION ---

if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None
if 'active_profile' not in st.session_state:
    p_list = get_profile_list()
    st.session_state.active_profile = p_list[0]
if 'temp_categories' not in st.session_state:
    st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)
if 'expanded_index' not in st.session_state:
    st.session_state.expanded_index = None

# --- 4. PAGE SETUP ---
st.set_page_config(page_title=f"LEGO Auditor v{VERSION}", layout="wide", page_icon="🧱")

# --- 5. SIDEBAR: SETTINGS & PROFILE MANAGEMENT ---
st.sidebar.title("🧱 Auditor Settings")
st.sidebar.caption(f"v{VERSION} | {DEVELOPER}")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio("🚀 Select Tool:", ["Gap Auditor", "Condition Guard"])
st.sidebar.markdown("---")

# Profile Selection
profile_list = get_profile_list()
display_list = sorted(list(set(profile_list + [st.session_state.active_profile])))

selected_p = st.sidebar.selectbox("Active Profile:", display_list, 
                                   index=display_list.index(st.session_state.active_profile))

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    st.session_state.temp_categories = load_profile_file(selected_p)
    st.rerun()

# Profile Upload from Disk
with st.sidebar.expander("📂 Import Profile from PC"):
    up_prof = st.file_uploader("Upload .json", type="json")
    if up_prof:
        try:
            loaded_data = json.load(up_prof)
            st.session_state.temp_categories = loaded_data
            st.session_state.active_profile = up_prof.name.replace(".json", "")
            st.success("Loaded!")
        except:
            st.error("Invalid File")

# Profile Creation
with st.sidebar.expander("➕ Create New Profile"):
    new_prof_name = st.text_input("Profile Name", placeholder="MyStore_2")
    if st.button("Create"):
        if new_prof_name:
            save_profile_file(new_prof_name, load_profile_file("Default"))
            st.session_state.active_profile = new_prof_name
            st.rerun()

# --- 6. MAIN CONTENT: XML UPLOAD ---
st.title(f"🧱 {app_mode}")

if st.session_state.xml_data is None:
    uploaded_xml = st.file_uploader("Upload your store.xml to begin:", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.rerun()
    st.stop()

if st.button("🔄 Upload Different Store / Clear"):
    st.session_state.xml_data = None
    st.rerun()

# --- 7. XML PROCESSING LOGIC ---
try:
    root = ET.fromstring(st.session_state.xml_data)
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
            p_name = item.find("ITEMNAME").text if item.find("ITEMNAME") is not None else p_id
            p_desc = CATALOG_LOOKUP.get(p_id, p_name)
            
            loc_parts = re.split(r'[- ]', rem_text, 1)
            loc_detail = loc_parts[1] if len(loc_parts) > 1 else "Main"

            container_contents[drawer_id].append({
                "id": p_id, "desc": p_desc, "cond": cond, "qty": qty, "loc": loc_detail
            })

    if app_mode == "Gap Auditor":
        audit_results = {}
        for cat in st.session_state.temp_categories:
            prefix = cat['prefix']
            pat = r"\b(\d{4})\b" if cat.get('is_wall') else rf"{prefix}(\d+)(?:-([0-9/\\-]+))?"
            found = defaultdict(set)
            
            for txt in all_remarks:
                for m in re.findall(pat, txt):
                    if cat.get('is_wall'): 
                        found[int(m)].add(1)
                    else:
                        num_id, r_ex = m
                        if r_ex: found[int(num_id)].update(parse_sub_ranges(r_ex))
                        else: found[int(num_id)].add(1)

            missing = []
            total_range = range(int(cat['start']), int(cat['end']) + 1)
            filled_slots = 0
            cap = int(cat.get('cap', 1))
            total_slots = len(total_range) * cap

            for n in total_range:
                occ = found[n]
                filled_slots += len([s for s in occ if s <= cap])
                miss_holes = sorted(list(set(range(1, cap + 1)) - occ))
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
                if not res['missing']: 
                    st.success(f"✅ All drawers in {cat['name']} are accounted for!")
                else:
                    for num, gaps in res['missing']:
                        lbl = f"{cat['prefix']}{num:03d}" if not cat.get('is_wall') else f"{num:04d}"
                        unique_key = f"gap_{cat['name']}_{num}"
                        is_exp = (st.session_state.expanded_index == unique_key)
                        with st.expander(f"Unit {lbl} - {len(gaps)} gaps", expanded=is_exp):
                            st.write(f"**Missing:** {', '.join(holes_to_ranges(gaps))}")
                            if st.button("Focus", key=f"btn_{unique_key}"):
                                st.session_state.expanded_index = unique_key
                                st.rerun()

    elif app_mode == "Condition Guard":
        conflicts = sorted([k for k, v in container_conditions.items() if len(v) > 1])
        if not conflicts:
            st.success("✅ No mixed-condition containers found!")
        else:
            st.error(f"Found {len(conflicts)} Containers with both New & Used items")
            for drawer in conflicts:
                unique_key = f"cond_{drawer}"
                is_exp = (st.session_state.expanded_index == unique_key)
                with st.expander(f"🔴 Conflict: {drawer}", expanded=is_exp):
                    c1, c2 = st.columns(2)
                    for cond_type, col in zip(['N', 'U'], [c1, col2 if 'col2' in locals() else c2]):
                        with col:
                            items_in_cond = [x for x in container_contents[drawer] if x['cond'] == cond_type]
                            st.markdown(f"**{'🆕 NEW' if cond_type == 'N' else '📜 USED'}** ({len(items_in_cond)} items)")
                            for p in items_in_cond:
                                st.write(f"**{p['qty']}x** {p['desc']}")
                                st.caption(f"Hole: {p['loc']} | ID: {p['id']}")
                    if st.button("Focus", key=f"focus_{drawer}"):
                        st.session_state.expanded_index = unique_key
                        st.rerun()

except Exception as e:
    st.error(f"Audit Error: {e}")

# --- 8. SIDEBAR: PROFILE EDITOR ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Profile Editor")

if st.sidebar.button("➕ Add New Row"):
    st.session_state.temp_categories.append({"name": "New Section", "prefix": "A", "start": 1, "end": 10, "cap": 1, "is_wall": False})
    st.rerun()

for i, cat in enumerate(st.session_state.temp_categories):
    with st.sidebar.expander(f"📁 Edit: {cat['name']}"):
        st.session_state.temp_categories[i]['name'] = st.text_input("Label", value=cat['name'], key=f"n_{i}")
        st.session_state.temp_categories[i]['prefix'] = st.text_input("Prefix", value=cat['prefix'], key=f"p_{i}")
        st.session_state.temp_categories[i]['start'] = st.number_input("Start #", value=int(cat['start']), key=f"s_{i}")
        st.session_state.temp_categories[i]['end'] = st.number_input("End #", value=int(cat['end']), key=f"e_{i}")
        st.session_state.temp_categories[i]['cap'] = st.number_input("Holes/Drawer", value=int(cat.get('cap', 1)), key=f"c_{i}")
        st.session_state.temp_categories[i]['is_wall'] = st.checkbox("4-digit", value=cat.get('is_wall', False), key=f"w_{i}")
        
        # Delete button placed inside the dropdown for a cleaner flow
        if st.button(f"🗑️ Delete {cat['name']}", key=f"del_{i}", use_container_width=True):
            st.session_state.temp_categories.pop(i)
            st.rerun()

# --- ADMIN LOCK LOGIC ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔐 Admin Access")
st.sidebar.caption("Admin Mode required to save changes to the central server.")
input_pass = st.sidebar.text_input("Enter Developer Key", type="password")

if input_pass == ADMIN_PASSWORD:
    if st.sidebar.button("💾 SAVE TO SERVER", type="primary", use_container_width=True):
        save_profile_file(st.session_state.active_profile, st.session_state.temp_categories)
        st.sidebar.success("Master File Updated on Server!")
else:
    st.sidebar.warning("Server Save: Locked")
    st.sidebar.info("Users should use 'BACKUP TO PC' for local sessions.")

st.sidebar.markdown("---")
st.sidebar.download_button(
    label="📥 BACKUP TO PC (.json)",
    data=json.dumps(st.session_state.temp_categories, indent=4),
    file_name=f"{st.session_state.active_profile}.json",
    mime="application/json",
    use_container_width=True
)