#!/usr/bin/env bash
# ~/projects/aquaLog/run_streamlit.sh

# Change to your project directory
cd /home/ubuntu/projects/aquaLog

# Activate the venv (adjust path if different)
source .venv/bin/activate

# Launch Streamlit
exec streamlit run main.py --server.port 8501 --server.headless true
