#!/usr/bin/env python3
"""
Stale dashboard stub - do not run.
================================================================================
This root-level Streamlit dashboard is an older fork, kept only as a pointer.

KNOWN ISSUE: it displayed a mislabeled "Approval Rate" that was computed as the
origination==application share rather than the LAR-derived approval rate, and it
lacks the current Explore / Disparities / Trends views. Do not rely on its
numbers.

To run the analysis or a current dashboard locally, use the code under
`Technical/src/` and follow README.md (set DATA_ROOT / OUTPUT_ROOT, then
`streamlit run`).
"""
import sys

_MSG = (
    "This root HMDA dashboard is a stale fork and is not maintained "
    "(it showed a mislabeled approval rate).\n"
    "See README.md to run the current analysis/dashboard locally."
)

try:
    import streamlit as st  # noqa: F401
    st.set_page_config(page_title="HMDA dashboard - moved", page_icon="warning")
    st.error("This dashboard is no longer maintained here.")
    st.markdown(
        "This root copy is a stale fork (it showed a mislabeled approval rate "
        "and lacks the Explore / Disparities / Trends views) and is kept only "
        "as a pointer. See **README.md** to run the current dashboard locally."
    )
except Exception:
    print(_MSG, file=sys.stderr)

if __name__ == "__main__":
    print(_MSG, file=sys.stderr)
    sys.exit(0)
