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

# --- 2. PRE-PROCESS MAIN STORE (FIXED FOR CACHING) ---
@st.cache_data
def map_store_locations(xml_bytes):
    root = ET.fromstring(xml_bytes)
    # Use standard dicts for compatibility with st.cache_data
    id_map = {} # PartID -> Condition -> List of Locations
    occupied_holes = {} # UnitID -> List of occupied Holes
    
    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem:
            # 1. Update ID Map
            if pid not in id_map: id_map[pid] = {}
            if cond not in id_map[pid]: id_map[pid][cond] = set()
            id_map[pid][cond].add(rem)
            
            # 2. Update Occupied Holes
            # Regex picks up the Unit (D104) and the Hole (1)
            m = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if m:
                unit, holes = m.groups()
                if unit not in occupied_holes: occupied_holes[unit] = set()
                if holes:
                    for h in re.split(r'[,/-]+', holes):
                        if h.isdigit(): 
                            occupied_holes[unit].add(int(h))

    # Convert sets to lists/dicts so Streamlit can serialize/cache them
    final_id_map = {k: {ck: list(cv) for ck, cv in v.items()} for k, v in id_map.items()}
    final_occupied = {k: list(v) for k, v in occupied_holes.items()}
    
    return final_id_map, final_occupied

# Call the fixed function
STORE_ID_MAP, OCCUPIED_HOLES_LIST = map_store_locations(st.session_state.xml_data)

# Re-convert the occupied holes back to sets for FAST lookup during the loop
OCCUPIED_HOLES = {k: set(v) for k, v in OCCUPIED_HOLES_LIST.items()}
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

    # --- 4. DATA LOOKUP & DISPLAY ---
# Helper for color names (Matches your Registry logic)
@st.cache_data
def get_color_map():
    # Standard BrickLink Color Map snippet
    return {
        "1": "White", "2": "Tan", "3": "Yellow", "4": "Orange", "5": "Red",
        "6": "Green", "7": "Blue", "8": "Brown", "9": "Light Gray", "10": "Dark Gray",
        "11": "Black", "12": "Medium Orange", "13": "Pink", "14": "Bright Pink",
        "15": "White", "17": "Light Green", "18": "Light Yellow", "19": "Dark Blue",
        "20": "Light Aqua", "23": "Bright Pink", "25": "Orange", "26": "Light Purple",
        "27": "Dark Turquoise", "28": "Dark Tan", "29": "Bright Light Blue",
        "31": "Medium Dark Pink", "32": "Light Lime", "33": "Light Blue",
        "34": "Lime", "35": "Light Orange", "36": "Bright Light Orange",
        "37": "Medium Orange", "38": "Bright Light Yellow", "39": "Dark Red",
        "40": "Dark Orange", "41": "Aqua", "42": "Medium Blue", "43": "Violet",
        "44": "Dark Pink", "46": "Yellowish Green", "47": "Dark Pink",
        "48": "Sand Green", "49": "Very Light Gray", "50": "Dark Gray",
        "51": "Salmon", "54": "Light Pink", "55": "Sand Blue", "56": "Light Salmon",
        "57": "Sand Red", "58": "Very Light Orange", "59": "Dark Brown",
        "60": "White", "62": "Medium Blue", "63": "Dark Blue-Gray", "68": "Dark Orange",
        "69": "Dark Tan", "70": "Medium Dark Flesh", "71": "Light Bluish Gray",
        "72": "Dark Bluish Gray", "73": "Medium Violet-Heiler", "74": "Medium Lime",
        "76": "Medium Green", "77": "Light Flesh", "78": "Dark Flesh",
        "80": "Dark Green", "81": "Flat Silver", "82": "Medium Orange",
        "84": "Medium Dark Gray", "85": "Dark Bluish Gray", "86": "Light Bluish Gray",
        "89": "Dark Purple", "90": "Light Flesh", "91": "Dark Flesh",
        "150": "Medium Nougat", "155": "Olive Green", "156": "Medium Azure",
        "212": "Bright Light Carnation", "216": "Sand Green"
    }

COLOR_MAP = get_color_map()

if ingest_file:
    # ... (Keep the XML processing logic from the previous step) ...
    
    results = []
    for item in new_items:
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        color_id = item.find("COLOR").text
        
        # Look up the Color Name
        color_name = COLOR_MAP.get(str(color_id), f"ID {color_id}")
        
        # ... (Suggestion logic from previous step) ...
        
        results.append({
            "Part ID": pid,
            "Color": color_name,  # Now showing the Name
            "Condition": "NEW" if cond == "N" else "USED",
            "Suggested Location": suggestion
        })

    # --- RENDER TABLE ---
    st.subheader("📋 Suggested Placements")
    st.dataframe(
        results, 
        use_container_width=True,
        column_config={
            "Suggested Location": st.column_config.TextColumn(
                "Suggested Location",
                help="Based on where this Part ID currently lives in your store.",
                width="large",
            )
        }
    )
    
    # --- DOWNLOAD BUTTON ---
    updated_xml = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        "💾 DOWNLOAD UPDATED XML",
        data=updated_xml,
        file_name="Smart_Ingest_Results.xml",
        mime="application/xml",
        use_container_width=True,
        type="primary"
    )