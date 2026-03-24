import streamlit as st
import os

st.set_page_config(page_title="LEGO Master Auditor", page_icon="🧱", layout="wide")

# Custom CSS for the "Clean" look
st.markdown("""
    <style>
    .main { background-color: #0f172a; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #3b82f6; }
    .css-17l2qt2 { border-radius: 15px; } /* Sidebar rounding */
    </style>
""", unsafe_allow_html=True)

st.title("🧱 LEGO Master Auditor Hub")
st.subheader("High-Volume Inventory Management")

# Global XML Upload Logic
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

# Top Row: Status Overview
col1, col2, col3 = st.columns(3)
with col1:
    status = "✅ LOADED" if st.session_state.xml_data else "❌ EMPTY"
    st.metric("Store Status", status)
with col2:
    # We can count files in profiles for a quick stat
    profile_count = len([f for f in os.listdir("lego_profiles") if f.endswith(".json")])
    st.metric("Stored Profiles", profile_count)
with col3:
    st.metric("System Version", "6.5.0 Gold")

st.divider()

# Main Action Area
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("### 📥 Load Your Inventory")
    uploaded_xml = st.file_uploader("Drop your BrickLink store.xml here", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
        st.success("Inventory synchronized across all tools!")
        st.balloons()

with c2:
    st.markdown("### 🧭 Navigation Guide")
    st.info("""
    **1. Gap Auditor** Find empty holes in Drawers & Cases.
    
    **2. Color Registry** Identify and name new Part Colors.
    
    **3. Condition Guard** Ensure N/U purity in your slots.
    """)

if st.session_state.xml_data:
    if st.button("🗑️ Unload Store Data"):
        st.session_state.xml_data = None
        st.rerun()