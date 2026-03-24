import streamlit as st

st.set_page_config(page_title="LEGO Hub", page_icon="🧱", layout="wide")

# CSS to hide the "horrible" default borders and refine the look
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    .stAlert { background-color: transparent !important; border: 1px solid #3b82f6 !important; }
    hr { margin: 1em 0px !important; }
    </style>
""", unsafe_allow_html=True)

# --- CLEAN HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🧱 LEGO Master Auditor")
with c2:
    if st.session_state.get('xml_data'):
        st.markdown("### ✅ STORE LOADED")
    else:
        st.markdown("### ⚪ NO STORE DATA")

st.divider()

# --- THE NAV BAR (Sleek Page Links) ---
nav1, nav2, nav3, nav4 = st.columns(4)
nav1.page_link("app.py", label="HOME", icon="🏠")
nav2.page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav3.page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav4.page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")

st.divider()

# Simple Upload Area
st.markdown("### 📤 Sync Store Data")
uploaded_xml = st.file_uploader("Drop store.xml to update all tools", type="xml", label_visibility="collapsed")
if uploaded_xml:
    st.session_state.xml_data = uploaded_xml.getvalue()
    st.success("Synchronized!")