import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict

st.header("⚠️ Condition Guard (v5.6.0 Logic)")

if not st.session_state.xml_data:
    st.warning("Please upload an XML file on the Home page first.")
    st.stop()

# Re-run the exact 5.6.0 Engine for this page
root = ET.fromstring(st.session_state.xml_data)
items = root.findall(".//ITEM")

container_stats = defaultdict(lambda: defaultdict(lambda: {"conds": set()}))
container_contents = defaultdict(list)

for item in items:
    rem = (item.find("REMARKS").text or "").strip()
    if rem:
        # v5.6.0 Logic: treat the remark as the unique ID
        cond = (item.find("CONDITION").text or "U").upper()
        container_contents[rem].append({
            "name": item.find("ITEMID").text, # Simple name for speed
            "qty": item.find("QTY").text,
            "cond": cond
        })
        container_stats[rem][1]["conds"].add(cond)

# 5.6.0 Conflict Detection
conflicts = [d for d, hs in container_stats.items() if any(len(h["conds"]) > 1 for h in hs.values())]

if not conflicts:
    st.success("✅ Consistent Conditions.")
else:
    for c_id in sorted(conflicts):
        with st.expander(f"🔴 Conflict in {c_id}"):
            for row in container_contents[c_id]:
                st.write(f"**{row['qty']}x** {row['name']} — [**{row['cond']}**]")