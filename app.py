import streamlit as st

st.set_page_config(page_title="LEGO Master Auditor", layout="wide")

# Global Session States
if 'xml_data' not in st.session_state:
    st.session_state.xml_data = None

st.title("🧱 LEGO Master Hub")

# Sidebar Global Upload
with st.sidebar:
    st.header("📦 Data Upload")
    uploaded_xml = st.file_uploader("Upload store.xml", type="xml")
    if uploaded_xml:
        st.session_state.xml_data = uploaded_xml.getvalue()
    
    if st.session_state.xml_data:
        st.success("XML Loaded into Memory")
        if st.button("🔄 Clear XML"):
            st.session_state.xml_data = None
            st.rerun()

st.info("Select a tool from the sidebar to begin auditing.")