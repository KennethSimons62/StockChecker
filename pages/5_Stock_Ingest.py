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
def analyze_vessels(xml_bytes):
    """Maps Part IDs to their 'Home Vessels' (e.g., C151) and tracks occupied holes."""
    if not xml_bytes: return {}, {}
    root = ET.fromstring(xml_bytes)
    
    family_vessels = {} # PartID -> Condition -> Set of Vessel IDs (e.g. 'C151')
    occupied_holes = {} # VesselID -> Set of Hole Numbers

    for item in root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        rem = (item.find("REMARKS").text or "").strip()
        
        if rem and rem != "**":
            # Regex captures the Vessel (C151) and ignores the specific hole for mapping
            m = re.search(r'^([A-Za-z]*\d+)(?:[-/ ]+([0-9,/-]+))?', rem)
            if m:
                vessel_id, hole_str = m.groups()
                
                # Link Part to this Vessel
                if pid not in family_vessels: family_vessels[pid] = {}
                if cond not in family_vessels[pid]: family_vessels[pid][cond] = set()
                family_vessels[pid][cond].add(vessel_id)
                
                # Track occupied holes within this Vessel
                if vessel_id not in occupied_holes: occupied_holes[vessel_id] = set()
                if hole_str:
                    for h in re.split(r'[,/-]+', hole_str):
                        if h.isdigit(): occupied_holes[vessel_id].add(int(h))

    # Serialize for cache
    clean_vessels = {k: {ck: list(cv) for ck, cv in v.items()} for k, v in family_vessels.items()}
    clean_holes = {k: list(v) for k, v in occupied_holes.items()}
    return clean_vessels, clean_holes

# --- 3. PROCESSING ---
if not st.session_state.get('xml_data'):
    st.error("⚠️ Please upload store.xml on the HOME page first.")
    st.stop()

V_LIST, H_LIST = analyze_vessels(st.session_state.xml_data)
FAMILY_VESSELS = {k: {ck: set(cv) for ck, cv in v.items()} for k, v in V_LIST.items()}
OCC_HOLES = {k: set(v) for k, v in H_LIST.items()}

st.title("📥 Vessel-First Stock Ingest")
st.markdown("Groups new parts into the same **Case/Box** where the family already lives.")

ingest_file = st.file_uploader("Upload newstock.xml", type="xml")

if ingest_file:
    new_tree = ET.parse(ingest_file)
    new_root = new_tree.getroot()
    display_data = []
    
    # Process every item in your newstock.xml
    for item in new_root.findall(".//ITEM"):
        pid = item.find("ITEMID").text
        cond = item.find("CONDITION").text.upper()
        cid = item.find("COLOR").text
        color_name = COLOR_MAP.get(str(cid), f"Color {cid}")
        
        # 1. FIND THE HOME VESSEL (e.g., C151 for part 3069)
        target_vessels = FAMILY_VESSELS.get(pid, {}).get(cond, set())
        
        suggestion = "NEW VESSEL REQ."
        found = False
        
        if target_vessels:
            # Sort vessels to prioritize Alpha-prefixes like 'C' over plain numbers
            for v_id in sorted(list(target_vessels)):
                # 2. DETERMINE CAPACITY (How many holes does a Case have?)
                unit_cap = 20 # Default if not in Config
                for cat in st.session_state.get('temp_categories', []):
                    if v_id.startswith(cat['prefix']):
                        unit_cap = cat['cap']
                        break
                
                # 3. SCAN THE ENTIRE VESSEL FOR THE NEXT EMPTY HOLE
                for h in range(1, unit_cap + 1):
                    if h not in OCC_HOLES.get(v_id, set()):
                        # Format as Vessel-Hole (e.g., C151-10)
                        suggestion = f"{v_id}-{h:02d}"
                        if v_id not in OCC_HOLES: OCC_HOLES[v_id] = set()
                        OCC_HOLES[v_id].add(h) # Lock this hole for the next item
                        found = True
                        break
                if found: break

        # 4. UPDATE THE XML REMARK FIELD
        rem_node = item.find("REMARKS")
        if rem_node is None: rem_node = ET.SubElement(item, "REMARKS")
        rem_node.text = suggestion

        display_data.append({
            "Part": pid,
            "Color": color_name,
            "Vessel Match": ", ".join(target_vessels) if target_vessels else "None",
            "Suggested Slot": suggestion
        })

    # --- 5. RENDER THE RESULTS TABLE ---
    st.subheader("📋 Ingest Suggestions")
    st.dataframe(display_data, use_container_width=True)
    
    # --- 6. DOWNLOAD BUTTON ---
    xml_out = ET.tostring(new_root, encoding='utf-8')
    st.download_button(
        label="💾 DOWNLOAD MAPPED XML",
        data=xml_out,
        file_name="Mapped_Ingest.xml",
        mime="application/xml",
        type="primary",
        use_container_width=True
    )