import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
import io

# ... [Previous Imports and Helper Functions remain the same] ...

# --- PROFILE MANAGEMENT HELPERS ---
def get_profile_list():
    if not os.path.exists(PROFILE_DIR): os.makedirs(PROFILE_DIR)
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default_Store"]

def load_profile_file(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return [{"name": "New Wall", "prefix": "", "start": 1, "end": 100, "cap": 1, "is_wall": True}]

def save_profile_file(name, data):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    with open(path, "w") as f: json.dump(data, f, indent=4)

# --- APP SETUP ---
st.set_page_config(page_title="LEGO Auditor", layout="wide", page_icon="🧱")

# Initialize Session State
if 'xml_data' not in st.session_state: st.session_state.xml_data = None
if 'active_profile' not in st.session_state: st.session_state.active_profile = get_profile_list()[0]
if 'temp_categories' not in st.session_state: 
    st.session_state.temp_categories = load_profile_file(st.session_state.active_profile)

# --- SIDEBAR ---
st.sidebar.title("🧱 Settings")

# 1. Profile Selection
profile_list = get_profile_list()
selected_p = st.sidebar.selectbox("Active Profile:", profile_list, index=profile_list.index(st.session_state.active_profile) if st.session_state.active_profile in profile_list else 0)

if selected_p != st.session_state.active_profile:
    st.session_state.active_profile = selected_p
    st.session_state.temp_categories = load_profile_file(selected_p)
    st.rerun()

# 2. Upload Profile from Disk
st.sidebar.divider()
st.sidebar.write("📤 **Load Profile from Disk**")
up_prof = st.sidebar.file_uploader("Upload .json config", type="json", label_visibility="collapsed")
if up_prof:
    try:
        st.session_state.temp_categories = json.load(up_prof)
        st.session_state.active_profile = up_prof.name.replace(".json", "")
        st.sidebar.success("Profile Loaded!")
    except: st.sidebar.error("Invalid JSON")

# 3. Save/Backup
st.sidebar.divider()
if st.sidebar.button("💾 SAVE TO SERVER", use_container_width=True, type="primary"):
    save_profile_file(st.session_state.active_profile, st.session_state.temp_categories)
    st.sidebar.success("Saved to Server!")

st.sidebar.download_button(
    "📥 BACKUP TO PC",
    data=json.dumps(st.session_state.temp_categories, indent=4),
    file_name=f"{st.session_state.active_profile}.json",
    use_container_width=True
)

# ... [Rest of the Gap Auditor / Condition Guard Logic] ...