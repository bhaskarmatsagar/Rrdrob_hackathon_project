"""Root entrypoint for REDROB Recruit Intelligence Streamlit Application.

Delegates execution to Hack2Skill_hackothorn-main/app.py while ensuring proper
path resolution and working directory settings.
"""

import os
import sys
from pathlib import Path

# Add the repository directory to sys.path
repo_root = Path(__file__).resolve().parent / "Hack2Skill_hackothorn-main"
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Change working directory so all relative paths resolve consistently
os.chdir(str(repo_root))

# Run the application
app_file = repo_root / "app.py"
with open(app_file, "r", encoding="utf-8") as f:
    code = f.read()

exec(code, {"__name__": "__main__", "__file__": str(app_file)})
