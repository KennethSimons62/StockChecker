import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
import json

# --- 1. PAGE CONFIG & NAV ---
st.set_page_config(page_title="Stock Ingest", page_icon="📥", layout="wide")

# Ensure 6 columns to match your other pages and avoid IndexError
nav = st.columns(6)
nav[0].page_link("Home.py", label="HOME", icon="🏠")
nav[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
nav[5].page_link("pages/5_Stock_Ingest.py", label="INGEST", icon="📥")
st.divider()

# --- 2. UNIVERSAL DATA LOADER ---
# We use st.cache_resource here so it updates only when the XML actually changes
@st.cache_data
def get_store_mapping(xml_bytes):
    """
    Scans the entire store.xml to map Part IDs to their 'Vessels'.
    Works for 'C151-01' (Vessel: C151) and '0487' (Vessel: 0487).
    """
    if not xml_bytes:
        return {}, {}
    
    root = ET.fromstring(xml_bytes)
    family_map = {} # PartID -> Set of Vessel Names
    occupied = {}   # Vessel Name -> Set of Hole Numbers
    
    # .//ITEM ensures we search every single item in the file
    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem and rem != "**":
            # Split by dash, slash, or space to get the 'Vessel' (e.g., C151 or 0487)
            parts = re.split(r'[-/ ]+', rem)
            vessel = parts[0]
            
            # Map Part ID to this Vessel
            if pid not in family_map:
                family_map[pid] = set()
            family_map[pid].add(vessel)
            
            # Track which holes are taken in this vessel
            if vessel not in occupied:
                occupied[vessel] = set()
            
            # If a hole number exists (e.g., the '01' in 'C151-01'), record it
            if len(parts) > 1 and parts[1].isdigit():
                occupied[vessel].add(int(parts[1]))
            else:
                # If it's a flat number like 0487, mark hole 1 as 'filled'
                occupied[vessel].add(1)
                
    # Convert sets to lists for Streamlit caching compatibility
    serial_families = {k: list(v) for k, v in family_map.items()}
    serial_occupied = {k: list(v) for k, v in occupied.items()}
    return serial_families, serial_occupied

# --- 3. LOAD EXTERNAL COLOR REGISTRY ---
def load_color_name(color_id):
    if os.path.exists("color_registry.json"):
        with open("color_registry.json", "r") as f:
            reg = json.load(f)
            return reg.get(str(color_id), f"Color {color_id}")
    return f"Color {color_id}"

# --- 4. MAIN INTERFACE ---
st.title("📥 Universal Stock Ingest")
st.markdown("Assigns locations based on the **Vessel** (Case or Box) where the family already lives.")

# Ensure the store file exists in session state
if not st.session_state.get('xml_data'):
    st.error("❌ No Store Inventory found. Please upload your store.xml on the HOME page.")
    st.stop()

# Get the mapping (Cached for speed)
f_map_raw, occ_raw = get_store_mapping(st.session_state.xml_data)
# Restore to sets for fast lookup
FAMILY_MAP = {k: set(v) for k, v in f_map_raw.items()}
OCCUPIED = {k: set(v) for k, v in occ_raw.items()}

# --- 5. FILE UPLOAD ---
ingest_file = st.file_uploader("Upload New Stock / Part-Out XML", type="xml")

if ingest_file:
    new_root = ET.fromstring(ingest_file.getvalue())
    display_results = []
    
    for item in new_root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cid = item.find("COLOR").text
        color_name = load_color_name(cid)
        
        # 1. FIND THE HOME VESSEL(S)
        vessels_found = FAMILY_MAP.get(pid, set())
        
        suggestion = "NEW VESSEL REQ."
        found = False
        
        if vessels_found:
            # Sort vessels (Alpha-prefixes like C151 first)
            for v_id in sorted(list(vessels_found)):
                # 2. FIND THE NEXT HOLE (1-50 range for safety)
                for h in range(1, 51):
                    if h not in OCCUPIED.get(v_id, set()):
                        suggestion = f"{v_id}-{h:02d}"
                        # Lock this hole so it's not suggested twice in one run
                        if v_id not in OCCUPIED: OCCUPIED[v_id] = set()
                        OCCUPIED[v_id].add(h)
                        found = True
                        break
                if found: break

        # Update the XML Remark for the final download
        rem_node = item.find("REMARKS")
        if rem_node is None:
            rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion

        display_results.append({
            "Part ID": pid,
            "Color": color_name,
            "Known Vessels": ", ".join(vessels_found) if vessels_found else "None",
            "Suggested Remark": suggestion
        })

    # Display the results
    st.subheader("📋 Processing Results")
    st.dataframe(display_results, use_container_width=True)
    
    # Final XML Export
    processed_xml = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        "💾 DOWNLOAD PROCESSED XML",
        data=processed_xml,
        file_name="Ingest_Results.xml",
        mime="application/xml",
        type="primary",
        use_container_width=True
    )

# --- 6. EMERGENCY RESET ---
st.sidebar.divider()
if st.sidebar.button("🔄 Clear Memory"):
    st.cache_data.clear()
    st.rerun()