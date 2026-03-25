import streamlit as st
import json
import os

# --- 1. PAGE CONFIG & NAV ---
st.set_page_config(page_title="Storage Config", page_icon="⚙️", layout="wide")

# Custom CSS for "Sexifying" the UI and increasing font sizes
st.markdown("""
    <style>
    /* Increase Checkbox Label Size (+2 points equivalent) */
    .stCheckbox label p {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    /* Increase General Text Size */
    .stMarkdown p {
        font-size: 1.1rem !important;
    }
    /* Style the Save Box at the top */
    .save-container {
        background-color: rgba(59, 130, 246, 0.1);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #3b82f6;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Navigation Bar (5 Columns)
nav = st.columns(5)
nav[0].page_link("Home.py", label="HOME", icon="🏠")
nav[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")

st.divider()

# --- 2. DATA LOAD/SAVE ---
CONFIG_FILE = "storage_conditions.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

if 'storage_tags' not in st.session_state:
    st.session_state.storage_tags = load_config()

# --- 3. TOP SAVE BOX ---
with st.container():
    st.markdown('<div class="save-container">', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("💾 Master Save Control")
        st.write("Changes are stored in memory until you hit Save. **Save regularly!**")
    with c2:
        if st.button("💾 SAVE ALL CHANGES", use_container_width=True, type="primary"):
            save_config(st.session_state.storage_tags)
            st.success("Configuration Secured!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 4. CATEGORY ACCORDIONS ---
if 'temp_categories' not in st.session_state:
    st.error("No storage profile found. Please visit the Auditor page first.")
    st.stop()

st.title("⚙️ Storage Condition Manager")

for cat in st.session_state.temp_categories:
    # Each category gets its own expander to keep the page clean
    with st.expander(f"📁 Edit {cat['name']} ({cat['prefix']}{cat['start']} - {cat['prefix']}{cat['end']})"):
        st.info(f"Toggle the switch to set unit as **NEW** (Checked) or **USED** (Unchecked).")
        
        start, end = int(cat['start']), int(cat['end'])
        prefix = str(cat['prefix']).upper().strip()
        
        # Grid layout for checkboxes
        cols = st.columns(6) 
        for i, n in enumerate(range(start, end + 1)):
            unit_id = f"{prefix}{n}"
            
            with cols[i % 6]:
                # Get current state from session
                current_val = st.session_state.storage_tags.get(unit_id, "USED") == "NEW"
                
                # Checkbox with larger font (via CSS above)
                is_new = st.checkbox(f"{unit_id}", value=current_val, key=f"cfg_{unit_id}")
                
                # Update session state immediately on click
                st.session_state.storage_tags[unit_id] = "NEW" if is_new else "USED"
                
                # Visual Indicator text
                status_color = "#3b82f6" if is_new else "#94a3b8"
                status_text = "NEW" if is_new else "USED"
                st.markdown(f"<span style='color:{status_color}; font-size: 0.8rem; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)

# --- 5. FOOTER SAVE ---
st.divider()
if st.button("💾 FINAL SAVE", key="bottom_save"):
    save_config(st.session_state.storage_tags)
    st.success("All settings saved to storage_conditions.json")