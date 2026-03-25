import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from collections import defaultdict

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

if not st.session_state.get('xml_data'):
    st.warning("⚠️ Please upload your main Store XML on the HOME page first.")
    st.stop()

# --- 2. PRE-PROCESS MAIN STORE ---
@st.cache_data
def map_store_locations(xml_bytes):
    root = ET.fromstring(xml_bytes)
    # Map: PartID -> Condition -> Set of Location Strings (e.g., "D104-1")
    id_map = defaultdict(lambda: defaultdict(set))
    # Map: UnitID (e.g., "D104") -> Set of occupied Holes {1, 2}
    occupied_holes = defaultdict(set)
    
    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem:
            id_map[pid][cond].add(rem)
            # Extract Unit and Hole (e.g., D104 and 1)
            m = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if m:
                unit, holes = m.groups()
                if holes:
                    # Quick parse of hole numbers
                    for h in re.split(r'[,/-]+', holes):
                        if h.isdigit(): occupied_holes[unit].add(int(h))
    return id_map, occupied_holes

STORE_ID_MAP, OCCUPIED_HOLES = map_store_locations(st.session_state.xml_data)

# --- 3. UPLOAD NEW STOCK ---
st.title("📥 Smart Stock Ingest")
st.markdown("Upload your BrickStore Part-Out file to find matching locations.")

ingest_file = st.file_uploader("Upload New Stock (XML)", type="xml")

if ingest_file:
    new_root = ET.fromstring(ingest_file.getvalue())
    new_items = new_root.findall(".//ITEM")
    
    results = []
    
    for item in new_items:
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        color = item.find("COLOR").text
        
        # 1. Look for existing locations for this ID + Condition
        existing_locs = STORE_ID_MAP.get(pid, {}).get(cond, [])
        
        suggestion = "NEEDS NEW LOCATION"
        found_unit = None
        
        if existing_locs:
            # Try to find an empty hole in the SAME units where family lives
            for loc in existing_locs:
                unit_match = re.search(r'^([A-Za-z]*\d+)', loc)
                if unit_match:
                    unit_id = unit_match.group(1)
                    # Find cap for this unit from session_state profile
                    unit_cap = 1
                    for cat in st.session_state.get('temp_categories', []):
                        if unit_id.startswith(cat['prefix']):
                            unit_cap = cat['cap']
                            break
                    
                    # Find first empty hole
                    for h in range(1, unit_cap + 1):
                        if h not in OCCUPIED_HOLES[unit_id]:
                            suggestion = f"{unit_id}-{h} (Family Match)"
                            found_unit = unit_id
                            # Mark this hole as "soft-taken" so the next part doesn't take it
                            OCCUPIED_HOLES[unit_id].add(h)
                            break
                if found_unit: break
        
        # Apply suggestion to the XML object
        rem_node = item.find("REMARKS")
        if rem_node is None:
            rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion
        
        results.append({
            "Part": pid,
            "Color": color,
            "Condition": cond,
            "Suggested": suggestion
        })

    # --- 4. DISPLAY & EXPORT ---
    st.table(results)
    
    # Export back to XML
    updated_xml = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        "💾 Download Updated XML for BrickStore",
        data=updated_xml,
        file_name="Smart_Ingest_Results.xml",
        mime="application/xml"
    )