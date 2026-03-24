import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime

# --- 1. PAGE CONFIG & SEXY NAV ---
st.set_page_config(page_title="Condition Guard", page_icon="⚠️", layout="wide")

# Minimalist Navigation Bar (No black boxes)
nav_cols = st.columns(4)
nav_cols[0].page_link("Home.py", label="HOME HUB", icon="🏠")
nav_cols[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav_cols[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav_cols[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
st.divider()

# --- 2. ASSETS & CONFIG ---
REGISTRY_FILE = "color_registry.json"

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

@st.cache_data
def load_parts_catalog():
    if os.path.exists("Parts.txt"):
        try:
            df = pd.read_csv("Parts.txt", sep='\t', encoding='latin1', on_bad_lines='skip')
            return dict(zip(df.iloc[:, 2].astype(str), df.iloc[:, 3]))
        except: return {}
    return {}

# Load mapping for the report display
if 'color_map' not in st.session_state:
    st.session_state.color_map = load_registry()

CATALOG_LOOKUP = load_parts_catalog()

# --- 3. DATA CHECK ---
if not st.session_state.get('xml_data'):
    st.warning("⚠️ No Store Data Loaded. Please go to the HOME HUB to upload your XML.")
    st.stop()

# --- 4. THE v5.6.0 DATA ENGINE ---
try:
    root = ET.fromstring(st.session_state.xml_data)
    items = root.findall(".//ITEM")

    # The exact v5.6.0 structure: simple Remark-to-Condition mapping
    container_stats = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "conds": set(), "color_ids": set()}))
    container_contents = defaultdict(list)

    for item in items:
        rem_node = item.find("REMARKS")
        if rem_node is not None and rem_node.text:
            # v5.6.0 Logic: We treat the entire REMARKS string as the unique ID
            rem = rem_node.text.strip()
            
            cond = (item.find("CONDITION").text or "U").upper()
            qty = int(item.find("QTY").text or 0)
            cid = str(item.find("COLOR").text)
            p_id = item.find("ITEMID").text
            p_name = CATALOG_LOOKUP.get(p_id, "Unknown Part")
            
            # Store full details for the report
            container_contents[rem].append({
                "id": p_id, 
                "name": p_name, 
                "cid": cid, 
                "cond": cond, 
                "qty": qty
            })
            
            # Record condition for conflict detection (indexed at 1 for simplicity)
            container_stats[rem][1]["qty"] += qty
            container_stats[rem][1]["conds"].add(cond)

    # --- 5. THE v5.6.0 CONFLICT REPORT ---
    st.subheader("⚠️ Condition Purity Audit")
    
    # Conflict = Any single Remark ID that contains more than one condition (N and U)
    conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]

    if not conflicts:
        st.success("✅ Consistent Conditions. No NEW and USED parts are sharing the same remark location.")
    else:
        st.info(f"Found {len(conflicts)} locations with mixed conditions.")
        for c_id in sorted(conflicts):
            with st.expander(f"🔴 Conflict in {c_id}"):
                # Direct listing of parts from the original v5.6.0
                for row in container_contents[c_id]:
                    # Lookup color name from registry if available
                    c_n = st.session_state.color_map.get(row['cid'], f"Code {row['cid']}")
                    
                    # Exact output format: Qty x Name — Color (ID) [Condition]
                    st.write(f"**{row['qty']}x** {row['name']} — {c_n} ({row['cid']}) [**{row['cond']}**]")

except Exception as e:
    st.error(f"Error processing condition guard: {e}")

# --- 6. FOOTER ---
st.divider()
if st.button("🔄 Refresh Audit"):
    st.rerun()