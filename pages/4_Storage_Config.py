import streamlit as st
import json
import os

# --- 1. PAGE CONFIG & NAV ---
st.set_page_config(page_title="Storage Config", page_icon="⚙️", layout="wide")

nav_cols = st.columns(5)
nav_cols[0].page_link("Home.py", label="HOME HUB", icon="🏠")
nav_cols[1].page_link("pages/1_Gap_Auditor.py", label="AUDITOR", icon="🔍")
nav_cols[2].page_link("pages/2_Color_Registry.py", label="COLORS", icon="🎨")
nav_cols[3].page_link("pages/3_Condition_Guard.py", label="GUARD", icon="⚠️")
nav_cols[4].page_link("pages/4_Storage_Config.py", label="CONFIG", icon="⚙️")
st.divider()

# --- 2. LOAD DATA ---
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

# --- 3. UI SETUP ---
st.title("⚙️ Storage Condition Configuration")
st.markdown("Tag your main storage units to enforce NEW or USED purity.")

# We pull the categories from your existing Auditor Profile
if 'temp_categories' not in st.session_state:
    st.info("Please visit the Auditor page first to load your profile.")
    st.stop()

# --- 4. THE TICKBOX GRID ---
for cat in st.session_state.temp_categories:
    st.subheader(f"📂 Category: {cat['name']}")
    
    start, end = int(cat['start']), int(cat['end'])
    prefix = cat['prefix'].upper()
    
    # Create a grid for the units
    cols = st.columns(6) 
    for i, n in enumerate(range(start, end + 1)):
        unit_id = f"{prefix}{n}"
        
        with cols[i % 6]:
            # Current state (Default to USED if not set)
            current_is_new = st.session_state.storage_tags.get(unit_id, "USED") == "NEW"
            
            # The Toggle
            label = f"**{unit_id}**"
            is_new = st.checkbox(label, value=current_is_new, key=f"cfg_{unit_id}")
            
            # Update State
            st.session_state.storage_tags[unit_id] = "NEW" if is_new else "USED"
            
            # Visual Indicator
            tag_color = "#3b82f6" if is_new else "#64748b"
            tag_text = "NEW" if is_new else "USED"
            st.markdown(f"<span style='font-size:10px; color:{tag_color}; font-weight:bold;'>{tag_text}</span>", unsafe_allow_html=True)

# --- 5. SAVE ---
st.divider()
if st.button("💾 SAVE STORAGE CONFIGURATION", use_container_width=True):
    save_config(st.session_state.storage_tags)
    st.success("Storage condition tags saved successfully!")