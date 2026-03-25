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

# --- 2. THE FAMILY ENGINE ---
@st.cache_data
def analyze_store_families(xml_bytes):
    """Creates a map of where every Part ID lives, regardless of color."""
    root = ET.fromstring(xml_bytes)
    # PartID -> Condition -> Set of Units (e.g. '2431' -> 'U' -> {'C062', 'C089'})
    family_map = {}
    # UnitID -> Set of taken holes (e.g. 'C062' -> {1, 2, 18})
    occupied_holes = {}

    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()

        if rem and rem != "**":
            # Extract Unit and Hole. Supports 'C062-18', 'D025-01/02', '0352' (treated as unit 0352)
            # This regex captures the primary location identifier
            match = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if match:
                unit_id, hole_str = match.groups()
                
                # Add to family knowledge
                if pid not in family_map: family_map[pid] = {}
                if cond not in family_map[pid]: family_map[pid][cond] = set()
                family_map[pid][cond].add(unit_id)

                # Add to hole occupancy
                if unit_id not in occupied_holes: occupied_holes[unit_id] = set()
                if hole_str:
                    # Split '01/02' or '16-18' into individual numbers
                    for h in re.split(r'[,/-]+', hole_str):
                        if h.isdigit(): occupied_holes[unit_id].add(int(h))

    # Convert sets to lists for Streamlit caching
    clean_families = {k: {ck: list(cv) for ck, cv in v.items()} for k, v in family_map.items()}
    clean_holes = {k: list(v) for k, v in occupied_holes.items()}
    return clean_families, clean_holes

# --- 3. PAGE LOGIC ---
if not st.session_state.get('xml_data'):
    st.error("❌ No Main Inventory! Upload store.xml on the HOME page.")
    st.stop()

# Load Family Maps
F_LIST, H_LIST = analyze_store_families(st.session_state.xml_data)
FAMILIES = {k: {ck: set(cv) for ck, cv in v.items()} for k, v in F_LIST.items()}
OCCUPIED = {k: set(v) for k, v in H_LIST.items()}

# Load Color Registry
if os.path.exists("color_registry.json"):
    with open("color_registry.json", "r") as f:
        COLOR_MAP = json.load(f)
else:
    COLOR_MAP = {}

st.title("📥 Family-Match Stock Ingest")
st.markdown("Assigns locations based strictly on **Part ID + Condition**.")

new_file = st.file_uploader("Upload newstock.xml", type="xml")

if new_file:
    tree = ET.parse(new_file)
    root = tree.getroot()
    results = []

    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        cid = item.find("COLOR").text
        
        color_name = COLOR_MAP.get(str(cid), f"Color {cid}")
        
        # FIND THE FAMILY UNITS
        units_with_this_part = FAMILIES.get(pid, {}).get(cond, set())
        
        suggestion = "NEW DRAWER REQUIRED"
        found = False
        
        if units_with_this_part:
            # Sort so we try to fill D001 before D099
            for unit in sorted(list(units_with_this_part)):
                # Default capacity if not found in Auditor Profile
                cap = 20 
                for cat in st.session_state.get('temp_categories', []):
                    if unit.startswith(cat['prefix']):
                        cap = cat['cap']
                        break
                
                # FIND THE FIRST HOLE
                for h in range(1, cap + 1):
                    if h not in OCCUPIED[unit]:
                        suggestion = f"{unit}-{h}"
                        OCCUPIED[unit].add(h) # Soft-lock for next item in list
                        found = True
                        break
                if found: break

        # Update the Remark in the XML
        rem_node = item.find("REMARKS")
        if rem_node is None: rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion

        results.append({
            "Part ID": pid,
            "Color": color_name,
            "Cond": "New" if cond == 'N' else 'Used',
            "Family Units": ", ".join(units_with_this_part) if units_with_this_part else "None",
            "Suggested": suggestion
        })

    st.dataframe(results, use_container_width=True)
    
    # Export
    xml_data = ET.tostring(root, encoding='utf-8')
    st.download_button("💾 DOWNLOAD PROCESSED XML", data=xml_data, 
                       file_name="Mapped_New_Stock.xml", mime="application/xml")