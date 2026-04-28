"""
run.py - Launch Audit Intelligence (Streamlit)
Usage: python run.py
Open:  http://localhost:8501
"""
import subprocess, sys, os

if __name__ == "__main__":
    print("Starting Audit Intelligence (Streamlit)...")
    print("Open browser at: http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "streamlit_app.py",
        "--server.port", "8501",
        "--server.headless", "true",
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
