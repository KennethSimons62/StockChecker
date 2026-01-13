import streamlit as st
import xml.etree.ElementTree as ET
import re
import json
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime
import io

# --- 1. APP CONFIG & CONSTANTS ---
VERSION = "2.1.0" # Incremented for BrickLink Color Update
DEVELOPER = "Kenneth Simons (Mr Brick UK)"
PROFILE_DIR = "lego_profiles"
ADMIN_PASSWORD = "p1qb55NJ????"

# Ensure the profile directory exists immediately
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# --- 2. HELPER FUNCTIONS ---

def get_profile_list():
    """Scans the profile directory for JSON files."""
    files = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return sorted(files) if files else ["Default"]

def load_profile_file(name):
    """Loads a profile from disk or returns the Master template."""
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except: pass
    # Default storage data providing a headstart
    return [
        {"name": "Drawers 1-1107", "prefix": "", "start": 1, "end": 1107, "cap": 1, "is_wall": False},
        {"name": "Boxes (B)", "prefix": "B", "start": 1, "end": 40, "cap": 30, "is_wall": False},
        {"name": "Cases (C)", "prefix": "C", "start": 1, "end": 180, "cap": 18, "is_wall": False},
        {"name": "Drawers (24 Loc)", "prefix": "D", "start": 1, "end": 38, "cap": 24, "is_wall": False},
        {"name": "Filing Cabinet", "prefix": "F", "start": 1, "end": 2, "cap": 25, "is_wall": False}
    ]

def save_profile_file(name, data):
    """Saves the current configuration to a JSON file on the server."""
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

@st.cache_data
def load_color_map():
    """Loads bricklink_colors.csv and maps BrickLink ID to BrickLink Color Name."""
    file_path = "bricklink_colors.csv"
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Using the new column names you specified
            return dict(zip(df['BrickLink ID'], df['BrickLink Color Name']))
        except Exception as e: 
            st.sidebar.error(f"Color Map Error: {e}")
            return {}
    return {}

@st.cache_data
def load_internal_catalog():
    """Loads Parts.txt and maps Part Number to its Name/Description."""
    if os.path.exists("Parts.txt"):
        try:
            df_ref = pd.read_csv("Parts.txt", sep='\t', encoding='latin1')
            return dict(zip(df_ref.iloc[:, 2].astype(str), df_ref.iloc[:, 3]))
        except: return {}
    return {}

COLOR_LOOKUP = load_color_map()
CATALOG_LOOKUP = load_internal_catalog()

# ... [The rest of your existing logic for parse_sub_ranges and holes_to_ranges remains the same] ...