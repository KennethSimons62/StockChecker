import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
import json
from collections import defaultdict

# --- 1. PAGE CONFIG & NAV (6 COLUMNS) ---
st.set_page_config(page_title="Stock Ingest", page_icon="📥", layout="wide")

# Ensure all 6 slots are defined to prevent IndexError
nav = st.columns(6)
nav[0].page_link("Home.py", label="HOME", icon="🏠")
nav[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
nav[5].page_link("pages/5_Stock_Ingest.py", label="INGEST", icon="📥")
st.divider()

# --- 2. LOAD EXTERNAL DATA (COLORS & STORAGE) ---
def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

COLOR_MAP = load_json_file("color_registry.json")
STORAGE_TAGS = load_json_file("storage_conditions.json")

# --- 3. PRE-PROCESS MAIN STORE DATA ---
@st.cache_data
def map_store_locations(xml_bytes):
    if not xml_bytes: return {}, {}
    root = ET.fromstring(xml_bytes)
    id_map = {} 
    occupied_holes = {} 
    
    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem:
            if pid not in id_map: id_map[pid] = {}
            if cond not in id_map[pid]: id_map[pid][cond] = set()
            id_map[pid][cond].add(rem)
            
            # Regex to find Unit (D104) and Hole (1)
            m = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if m:
                unit, holes = m.groups()
                if unit not in occupied_holes: occupied_holes[unit] = set()
                if holes:
                    for h in re.split(r'[,/-]+', holes):
                        if h.isdigit(): occupied_holes[unit].add(int(h))

    # Convert sets to lists for Streamlit Caching
    final_id_map = {k: {ck: list(cv) for ck, cv in v.items()} for k, v in id_map.items()}
    final_occupied = {k: list(v) for k, v in occupied_holes.items()}
    return final_id_map, final_occupied

# --- 4. EXECUTION ---
if not st.session_state.get('xml_data'):
    st.error("⚠️ No Main Inventory found. Please upload your Store XML on the HOME page.")
    st.stop()

# Load the maps
STORE_ID_MAP, OCC_HOLES_LIST = map_store_locations(st.session_state.xml_data)
# Re-convert to sets for lightning fast lookup
OCC_HOLES = {k: set(v) for k, v in OCC_HOLES_LIST.items()}

st.title("📥 Smart Stock Ingest")
st.markdown("Upload a **BrickStore XML** to auto-assign locations based on existing Part IDs.")

ingest_file = st.file_uploader("Upload Part-Out / New Stock XML", type="xml")

if ingest_file:
    new_tree = ET.parse(ingest_file)
    new_root = new_tree.getroot()
    new_items = new_root.findall(".//ITEM")
    
    display_results = []
    
    for item in new_items:
        pid = item.find("ITEMID").text
        color_id = item.find("COLOR").text
        cond_raw = item.find("CONDITION").text.upper()
        cond_full = "NEW" if cond_raw in ["N", "NEW"] else "USED"
        
        # Color Lookup from your JSON
        color_name = COLOR_MAP.get(str(color_id), f"ID {color_id}")
        
        # 1. FIND THE FAMILY: Where does this Part ID live currently?
        existing_locs = STORE_ID_MAP.get(pid, {}).get(cond_raw, [])
        suggestion = "NO FAMILY MATCH - ASSIGN MANUALLY"
        found = False
        
        if existing_locs:
            for loc in existing_locs:
                # Extract the unit ID (e.g., D104)
                unit_match = re.search(r'^([A-Za-z]*\d+)', loc)
                if unit_match:
                    unit_id = unit_match.group(1)
                    
                    # Find capacity from your profile settings
                    unit_cap = 1
                    for cat in st.session_state.get('temp_categories', []):
                        if unit_id.startswith(cat['prefix']):
                            unit_cap = cat['cap']
                            break
                    
                    # 2. FIND THE HOLE: Is there an empty slot in this family unit?
                    for h in range(1, unit_cap + 1):
                        if h not in OCC_HOLES[unit_id]:
                            suggestion = f"{unit_id}-{h}"
                            # Block this hole so the next part in the list doesn't take it
                            OCC_HOLES[unit_id].add(h)
                            found = True
                            break
                if found: break

        # Update the XML Remark field
        rem_node = item.find("REMARKS")
        if rem_node is None:
            rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion

        display_results.append({
            "Part ID": pid,
            "Color": color_name,
            "Condition": cond_full,
            "Suggestion": suggestion
        })

    # --- 5. RENDER & DOWNLOAD ---
    st.subheader("📋 Placement Results")
    st.dataframe(display_results, use_container_width=True)
    
    # Export back to XML
    xml_output = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        label="💾 DOWNLOAD UPDATED XML FOR BRICKSTORE",
        data=xml_output,
        file_name="Smart_Placement_Results.xml",
        mime="application/xml",
        type="primary",
        use_container_width=True
    )