import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
import json

# --- 1. PAGE CONFIG & NAV ---
st.set_page_config(page_title="Stock Ingest", page_icon="📥", layout="wide")

nav = st.columns(6)
nav[0].page_link("Home.py", label="HOME", icon="🏠")
nav[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
nav[5].page_link("pages/5_Stock_Ingest.py", label="INGEST", icon="📥")
st.divider()

# --- 2. DATA LOADERS ---
def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

COLOR_MAP = load_json_file("color_registry.json")

@st.cache_data
def map_store_by_family(xml_bytes):
    """Maps locations by ItemID + Condition, ignoring Color."""
    if not xml_bytes: return {}, {}
    root = ET.fromstring(xml_bytes)
    
    # Map: ItemID -> Condition -> Set of UnitIDs (e.g., '2431' -> 'N' -> {'D101', 'D105'})
    family_units = {} 
    # Map: UnitID -> Set of occupied Holes
    occupied_holes = {} 

    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem:
            # Extract Unit (e.g., D104) and Hole (e.g., 1)
            m = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if m:
                unit_id, holes = m.groups()
                
                # Add to Family Map
                if pid not in family_units: family_units[pid] = {}
                if cond not in family_units[pid]: family_units[pid][cond] = set()
                family_units[pid][cond].add(unit_id)
                
                # Track occupied holes for gap finding
                if unit_id not in occupied_holes: occupied_holes[unit_id] = set()
                if holes:
                    for h in re.split(r'[,/-]+', holes):
                        if h.isdigit(): occupied_holes[unit_id].add(int(h))

    # Convert sets to lists for caching
    serializable_families = {k: {ck: list(cv) for ck, cv in v.items()} for k, v in family_units.items()}
    serializable_holes = {k: list(v) for k, v in occupied_holes.items()}
    return serializable_families, serializable_holes

# --- 3. PROCESSING ---
if not st.session_state.get('xml_data'):
    st.error("⚠️ Upload Main Store XML on HOME page first.")
    st.stop()

FAMILIES_LIST, HOLES_LIST = map_store_by_family(st.session_state.xml_data)
# Restore sets for fast logic
FAMILIES = {k: {ck: set(cv) for ck, cv in v.items()} for k, v in FAMILIES_LIST.items()}
OCC_HOLES = {k: set(v) for k, v in HOLES_LIST.items()}

st.title("📥 Family-Based Stock Ingest")
st.markdown("Groups new parts into existing locations based on **Item ID + Condition**.")

ingest_file = st.file_uploader("Upload BrickStore XML", type="xml")

if ingest_file:
    new_tree = ET.parse(ingest_file)
    new_root = new_tree.getroot()
    new_items = new_root.findall(".//ITEM")
    
    display_data = []
    
    for item in new_items:
        pid = item.find("ITEMID").text
        color_id = item.find("COLOR").text
        cond = item.find("CONDITION").text.upper()
        
        color_name = COLOR_MAP.get(str(color_id), f"ID {color_id}")
        
        # 1. FIND FAMILY UNITS (ID + Condition only)
        possible_units = FAMILIES.get(pid, {}).get(cond, set())
        
        suggestion = "NO FAMILY FOUND"
        reason = "New Item ID for this store."
        found = False
        
        if possible_units:
            # Sort units to try and fill the lowest numbered drawer first
            sorted_units = sorted(list(possible_units))
            
            for unit_id in sorted_units:
                # Get unit capacity from your Auditor profile
                unit_cap = 1
                for cat in st.session_state.get('temp_categories', []):
                    if unit_id.startswith(cat['prefix']):
                        unit_cap = cat['cap']
                        break
                
                # 2. FIND FIRST EMPTY HOLE IN THAT UNIT
                for h in range(1, unit_cap + 1):
                    if h not in OCC_HOLES[unit_id]:
                        suggestion = f"{unit_id}-{h}"
                        reason = f"Matched Family ID {pid} in {unit_id}"
                        OCC_HOLES[unit_id].add(h) # Soft-lock the hole
                        found = True
                        break
                if found: break

        # Update XML
        rem_node = item.find("REMARKS")
        if rem_node is None: rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion

        display_data.append({
            "Item ID": pid,
            "Color": color_name,
            "Cond": "NEW" if cond == "N" else "USED",
            "Suggested Remark": suggestion,
            "Logic": reason
        })

    # --- 4. DISPLAY & DOWNLOAD ---
    st.dataframe(display_data, use_container_width=True)
    
    xml_out = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        "💾 DOWNLOAD PROCESSED XML",
        data=xml_out,
        file_name="Family_Mapped_Stock.xml",
        mime="application/xml",
        type="primary"
    )