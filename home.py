import streamlit as st
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="LEGO Hub", page_icon="🏠", layout="wide")

# Session State for the XML data
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

# --- 2. SLEEK NAVIGATION ---
# This matches the navigation on your other pages for a seamless feel
nav1, nav2, nav3, nav4 = st.columns(4)
nav1.page_link("home.py", label="HOME HUB", icon="🏠")
nav2.page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav3.page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav4.page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav5.page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
st.divider()

# --- 3. MAIN CONTENT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🧱 Master Auditor Hub")
    st.markdown("### 📥 Sync Your Inventory")
    
    # THE RESTORED UPLOADER
    uploaded_xml = st.file_uploader(
        "Upload your BrickLink store.xml here to begin auditing:", 
        type="xml",
        help="Once uploaded, your data will be available in the Auditor, Color Registry, and Condition Guard."
    )
    
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.success("✨ Store data synchronized! Use the navigation above to start.")
        st.balloons()

with col2:
    st.markdown("### 📊 Current Status")
    if st.session_state.xml_data:
        st.info("✅ Store Data: **LOADED**")
        if st.button("🗑️ Unload Store Data"):
            st.session_state.xml_data = None
            st.rerun()
    else:
        st.warning("⚪ Store Data: **NOT LOADED**")

st.divider()

# --- 4. SYSTEM OVERVIEW ---
st.markdown("""
### 🧭 Quick Guide
* **Gap Auditor:** Define your drawer layout and find empty slots.
* **Color Registry:** Identify unknown Color IDs using location clues.
* **Condition Guard:** Check for NEW/USED mix-ups in your inventory.
""")