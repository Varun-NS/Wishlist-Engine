"""
Entry point for Streamlit Community Cloud.
Redirects execution to app.py.
"""
import runpy
import sys
import os

# Ensure scripts directory is on sys.path
scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Execute app.py in global scope
runpy.run_path(os.path.join(os.path.dirname(__file__), "app.py"), run_name="__main__")
