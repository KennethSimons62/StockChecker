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

# --- 2. DATA LOADERS (No Cache for Debugging) ---
def get_store_data():
    if not st.session_state.get('xml_data'):
        return None
    root = ET.fromstring(st.session_state.xml_data)
    
    # Map: PartID -> Set of Vessels (e.g., '3069' -> {'C151', 'C102'})
    family_map = {}
    # Map: Vessel -> Set of occupied holes
    occupied = {}

    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem and rem != "**":
            # Strip suffix: C151-01 -> C151
            vessel = re.split(r'[-/ ]+', rem)[0]
            
            if pid not in family_map: family_map[pid] = set()
            family_map[pid].add(vessel)
            
            # Track holes
            if vessel not in occupied: occupied[vessel] = set()
            hole_match = re.search(r'(\d+)$', rem)
            if hole_match:
                occupied[vessel].add(int(hole_match.group(1)))
    return family_map, occupied

# --- 3. EXECUTION ---
st.title("📥 Vessel-First Stock Ingest")

store_info = get_store_data()

if not store_info:
    st.error("❌ ERROR: No Store XML found. Please upload your store.xml on the HOME page.")
    st.stop()

FAMILY_MAP, OCCUPIED_HOLES = store_info

# Quick Debug Check
if st.checkbox("🔍 Debug: View 3069 Store Data"):
    st.write("Vessels associated with 3069 in your store:", FAMILY_MAP.get("3069", "NOT FOUND"))

ingest_file = st.file_uploader("Upload newstock.xml", type="xml")

if ingest_file:
    new_root = ET.fromstring(ingest_file.getvalue())
    results = []
    
    for item in new_root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cid = item.find("COLOR").text
        
        # Search for Home Vessel
        vessels = FAMILY_MAP.get(pid, set())
        suggestion = "NEW VESSEL REQ."
        
        if vessels:
            # Try the first vessel found (e.g., C151)
            target_vessel = sorted(list(vessels))[0]
            
            # Find next empty hole (1-20)
            for h in range(1, 21):
                if h not in OCCUPIED_HOLES.get(target_vessel, set()):
                    suggestion = f"{target_vessel}-{h:02d}"
                    OCCUPIED_HOLES[target_vessel].add(h) # Soft-lock
                    break
        
        # Update XML
        rem_node = item.find("REMARKS")
        if rem_node is None: rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion
        
        results.append({"Part": pid, "Color ID": cid, "Found In": ", ".join(vessels), "Suggested": suggestion})

    st.dataframe(results, use_container_width=True)
    
    st.download_button("💾 DOWNLOAD XML", data=ET.tostring(new_root), file_name="Mapped_Stock.xml")