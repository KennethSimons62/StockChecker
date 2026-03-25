import streamlit as st
import xml.etree.ElementTree as ET
import json
import os
from collections import defaultdict

# --- 1. PAGE CONFIG & NAV ---
st.set_page_config(page_title="Color Registry", page_icon="🎨", layout="wide")

# Persistent Navigation Bar
nav_cols = st.columns(5)
nav_cols[0].page_link("Home.py", label="HOME HUB", icon="🏠")
nav_cols[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav_cols[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav_cols[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav_cols[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
st.divider()

# --- 2. ASSETS & DIRECTORIES ---
REGISTRY_FILE = "color_registry.json"
IMAGE_DIR = "color_images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_registry(data):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=4)

if 'color_map' not in st.session_state:
    st.session_state.color_map = load_registry()

if 'clue_index' not in st.session_state:
    st.session_state.clue_index = 0

if 'reset_key' not in st.session_state:
    st.session_state.reset_key = 0

def trigger_reset():
    st.session_state.reset_key += 1

# --- 3. DATA ENGINE ---
if not st.session_state.get('xml_data'):
    st.warning("🎨 No Store Data Loaded. Please go to the HOME HUB to upload your XML.")
    st.stop()

# Parse XML for colors and clues
root = ET.fromstring(st.session_state.xml_data)
items = root.findall(".//ITEM")
pure_clues_map = defaultdict(list)
all_xml_cids = set()

for item in items:
    cid = str(item.find("COLOR").text)
    all_xml_cids.add(cid)
    rem_node = item.find("REMARKS")
    if rem_node is not None and rem_node.text:
        rem_text = rem_node.text.strip()
        p_id = item.find("ITEMID").text
        # Logic: Find parts that are the ONLY item in their slot to provide "Pure Clues"
        clue = f"Part **{p_id}** found at 📍 **{rem_text}**"
        if clue not in pure_clues_map[cid]:
            pure_clues_map[cid].append(clue)

# --- 4. DISCOVERY ZONE ---
unknowns = [c for c in all_xml_cids if c not in st.session_state.color_map]

if unknowns:
    st.markdown("""
        <style>
        .trainer-card { background-color: #1e1b4b; padding: 25px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 20px; color: white; }
        .clue-box { background: rgba(99, 102, 241, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #6366f1; margin-top: 10px; color: #a5b4fc; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
    st.subheader("🔍 Discovery Zone")
    
    target_cid = unknowns[0]
    clues = pure_clues_map.get(target_cid, ["No specific location clues found for this ID."])
    
    if st.session_state.clue_index >= len(clues): 
        st.session_state.clue_index = 0
        
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.metric("Missing ID", target_cid)
        if st.button("⏭️ NEXT CLUE"):
            st.session_state.clue_index = (st.session_state.clue_index + 1) % len(clues)
            st.rerun()
            
    with c2:
        train_name = st.text_input("Enter Color Name:", key=f"train_input_{st.session_state.reset_key}")
        st.markdown(f"<div class='clue-box'>{clues[st.session_state.clue_index]}</div>", unsafe_allow_html=True)
        
    with c3:
        st.write("")
        if st.button("💾 SAVE TO REGISTRY", use_container_width=True):
            if train_name:
                st.session_state.color_map[target_cid] = train_name
                save_registry(st.session_state.color_map)
                st.session_state.clue_index = 0
                trigger_reset()
                st.success(f"ID {target_cid} saved!")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.success("✅ All color IDs in this store file are already in your registry!")

# --- 5. SWATCH GALLERY ---
st.divider()
st.subheader("🎨 Registered Swatch Gallery")
search = st.text_input("🔍 Search Registry...", placeholder="Search by ID or Name")

if st.session_state.color_map:
    # Sort IDs numerically
    sorted_cids = sorted(st.session_state.color_map.keys(), key=lambda x: int(x) if x.isdigit() else 999)
    
    # Filter based on search
    filtered = [c for c in sorted_cids if search.lower() in c or search.lower() in st.session_state.color_map[c].lower()] if search else sorted_cids
    
    cols = st.columns(10)
    for i, cid in enumerate(filtered):
        with cols[i % 10]:
            # Image padding logic (e.g. ID 1 becomes 001.png)
            try: padded = f"{int(cid):03d}"
            except: padded = cid
            
            img_path = os.path.join(IMAGE_DIR, f"{padded}.png")
            if os.path.exists(img_path):
                st.image(img_path, width=70)
            else:
                st.markdown(f"<div style='text-align:center; color:#f87171; font-size:0.6rem; font-weight:bold;'>NO IMG<br>{cid}</div>", unsafe_allow_html=True)
            
            st.markdown(f"**{st.session_state.color_map[cid]}**")
            st.caption(f"ID: {cid}")

# --- 6. MANUAL ENTRY ---
with st.expander("⌨️ Manual Registry Entry"):
    m1, m2 = st.columns(2)
    mid = m1.text_input("Manual ID #", key="manual_id")
    mna = m2.text_input("Manual Color Name", key="manual_name")
    if st.button("Add to Registry"):
        if mid and mna:
            st.session_state.color_map[str(mid)] = mna
            save_registry(st.session_state.color_map)
            st.success(f"Added {mna}!")
            st.rerun()