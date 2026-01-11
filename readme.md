🧱 LEGO Master Auditor
Version: 1.8.2

Developer: Kenneth Simons (Mr Brick UK)

A specialized inventory management and auditing tool designed for high-volume LEGO resellers. This application processes BrickLink-style XML store exports to identify storage gaps and ensure condition consistency across your inventory.

🚀 Key Features

1. Gap Auditor
   Automatically identifies "holes" in your storage system.

Smart Parsing: Scans the REMARKS field for drawer IDs and sub-locations (e.g., A001-05).

Section Mapping: Tracks fill percentages across different storage categories (Wall Drawers vs. Custom Units).

Focus Mode: Allows you to isolate specific drawers to see exactly which slots are available for new inventory.

2. Condition Guard
   Prevents the accidental mixing of "New" and "Used" parts in the same storage container.

Conflict Detection: Instantly flags any Drawer ID containing both N and U conditions.

Detailed Breakdown: Shows the exact parts, quantities, and sub-locations causing the conflict.

3. Profile Editor
   Customize the app to match your physical storage layout without touching the code.

Define prefixes (e.g., "DW", "BOX").

Set start and end ranges for auditing.

Define "Capacity" (how many holes/slots per drawer).

Toggle between standard labels and 4-digit Wall Drawer formats.

🛠️ Installation \& Setup
Prerequisites
Python 3.8+

Streamlit

Pandas

Installation
Install the required libraries:

Bash

pip install streamlit pandas
Place the following files in your project directory:

auditor.py (The main script)

store.xml (Your BrickLink store export)

parts.txt (Optional: For human-readable part names)

Running the App
Navigate to the folder in your terminal and run:

Bash

streamlit run auditor.py
📁 Required Data Structure
For the app to function correctly, ensure your folder looks like this:

Plaintext

/your-project-folder
│
├── auditor.py           # The main code
├── store.xml            # Your inventory data
├── parts.txt            # Tab-separated catalog reference
└── /lego\_profiles       # Auto-created folder for your store settings
└── Default\_Store.json
💡 How to Use
Load Data: Ensure your BrickLink inventory is exported as an XML and named store.xml.

Configure Profiles: Use the Profile Editor in the sidebar to define your drawer ranges. Click Save Profile to persist these settings.

Audit Gaps: Switch to Gap Auditor to see which drawers have empty slots for new parts.

Verify Quality: Switch to Condition Guard before a big inventory upload to ensure no Used parts have crept into New part drawers."# StockChecker"

