
"""Master ETL execution script."""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "data_ingestion.py",
    "live_nav_fetch.py",
]

def run_script(script_name:str)->None:
    script = Path(__file__).parent / "scripts" / script_name
    if not script.exists():
        print(f"Skipped: {script_name}")
        return
    result = subprocess.run([sys.executable, str(script)])
    if result.returncode != 0:
        raise SystemExit(f"Failed: {script_name}")

def main()->None:
    for script in SCRIPTS:
        run_script(script)
    print("Pipeline completed successfully")

if __name__ == "__main__":
    main()
