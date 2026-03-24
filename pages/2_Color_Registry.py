import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
from collections import defaultdict

# --- 1. ASSETS & CONFIG ---
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

# --- 2. PAGE UI ---
st.header("🎨 Color Registry & Discovery")

if not st.session_state.xml_data:
    st.warning("Please upload a store.xml on the Home page to find missing colors.")
    st.stop()

# --- 3. DATA ENGINE (Color Extraction Only) ---
root = ET.fromstring(st.session_state.xml_data)
items = root.findall(".//ITEM")

pure_clues_map = defaultdict(list)
all_xml_cids = set()

for item in items:
    cid = str(item.find("COLOR").text)
    all_xml_cids.add(cid)
    
    rem_node = item.find("REMARKS")
    if rem_node is not None and rem_node.text:
        # Use the name of the part as a clue for the color
        p_id = item.find("ITEMID").text
        loc = rem_node.text.strip()
        clue = f"Part: **{p_id}** found at 📍 **{loc}**"
        if clue not in pure_clues_map[cid]:
            pure_clues_map[cid].append(clue)

# --- 4. DISCOVERY ZONE ---
unknowns = [c for c in all_xml_cids if c not in st.session_state.color_map]

if unknowns:
    st.markdown("""
        <style>
        .trainer-card { background-color: #1e1b4b; padding: 20px; border-radius: 12px; border: 2px solid #6366f1; color: white; }
        .clue-box { background: rgba(99, 102, 241, 0.1); padding: 10px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #6366f1; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
    st.subheader("🔍 Discovery Zone: Identify Missing Color IDs")
    
    target_cid = unknowns[0]
    clues = pure_clues_map.get(target_cid, ["No specific location clues found."])
    
    if st.session_state.clue_index >= len(clues): 
        st.session_state.clue_index = 0
        
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.metric("Missing ID", target_cid)
        if st.button("⏭️ NEXT CLUE"):
            st.session_state.clue_index = (st.session_state.clue_index + 1) % len(clues)
            st.rerun()
            
    with c2:
        new_name = st.text_input("Enter Color Name:", key="discovery_input")
        st.markdown(f"<div class='clue-box'>{clues[st.session_state.clue_index]}</div>", unsafe_allow_html=True)
        
    with c3:
        st.write("")
        if st.button("💾 SAVE TO REGISTRY", use_container_width=True):
            if new_name:
                st.session_state.color_map[target_cid] = new_name
                save_registry(st.session_state.color_map)
                st.session_state.clue_index = 0
                st.success(f"ID {target_cid} saved!")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.success("✅ All colors in this XML are recognized in your registry!")

# --- 5. SWATCH GALLERY ---
st.divider()
st.subheader("🎨 Registered Swatch Gallery")

search = st.text_input("🔍 Search Registry...", placeholder="Search by ID or Name")

if st.session_state.color_map:
    all_cids = sorted(st.session_state.color_map.keys(), key=lambda x: int(x) if x.isdigit() else 999)
    filtered = [c for c in all_cids if search.lower() in c or search.lower() in st.session_state.color_map[c].lower()] if search else all_cids
    
    cols = st.columns(10)
    for i, cid in enumerate(filtered):
        with cols[i % 10]:
            try: padded = f"{int(cid):03d}"
            except: padded = cid
            
            img_path = os.path.join(IMAGE_DIR, f"{padded}.png")
            if os.path.exists(img_path):
                st.image(img_path, width=70)
            else:
                st.markdown(f"<div style='color:#f87171; font-size:0.7rem; font-weight:bold;'>NO IMG<br>{cid}</div>", unsafe_allow_html=True)
            
            st.markdown(f"**{st.session_state.color_map[cid]}**")
            st.caption(f"ID: {cid}")

# --- 6. MANUAL ENTRY ---
with st.expander("⌨️ Manual Registry Entry"):
    m1, m2 = st.columns(2)
    mid = m1.text_input("Manual ID #")
    mna = m2.text_input("Manual Name")
    if st.button("Add Manually"):
        if mid and mna:
            st.session_state.color_map[str(mid)] = mna
            save_registry(st.session_state.color_map)
            st.rerun()