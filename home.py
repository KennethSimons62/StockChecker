import streamlit as st
import os
import json

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="LEGO Hub", page_icon="🏠", layout="wide")

# Session State for the XML data
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

# --- 2. UPDATED NAVIGATION BAR (6 COLUMNS) ---
# We are expanding to 6 columns to fit the new Config page
nav = st.columns(6)
nav[0].page_link("Home.py", label="HOME", icon="🏠")
nav[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
nav[5].page_link("pages/5_Stock_Ingest.py", label="INGEST", icon="📥")
st.divider()

# --- 3. MAIN CONTENT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🧱 Master Auditor Hub")
    st.markdown("### 📥 Sync Your Inventory")
    
    uploaded_xml = st.file_uploader(
        "Upload your BrickLink store.xml here:", 
        type="xml",
        label_visibility="collapsed"
    )
    
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.success("✨ Store data synchronized across all tools!")
        st.balloons()

with col2:
    st.markdown("### 📊 Status")
    if st.session_state.xml_data:
        st.info("✅ XML: **LOADED**")
    else:
        st.warning("⚪ XML: **EMPTY**")
    
    # Check if Storage Config exists
    if os.path.exists("storage_conditions.json"):
        st.info("⚙️ Storage Map: **ACTIVE**")
    else:
        st.error("⚙️ Storage Map: **MISSING**")

st.divider()

# --- 4. QUICK GUIDE ---
st.markdown("""
### 🧭 Tool Overview
* **Gap Auditor:** Find empty slots in your drawers.
* **Color Registry:** Identify unknown colors via location clues.
* **Condition Guard:** Detect NEW/USED mixed inventory.
* **Storage Config:** Define your NEW vs USED storage zones.
""")