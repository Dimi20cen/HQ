import sys
import os
import json
import argparse
from pathlib import Path

TOOLS_DIR = Path("tools")

# Template for main.py
# Note: We add sys.path hacks so you can run 'python main.py' directly
MAIN_TEMPLATE = """import sys
from pathlib import Path

# 1. Add Project Root to Path (so we can import tools.sdk)
# This allows running: python tools/{folder}/main.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from tools.sdk.base_tool import BaseTool

# 2. Initialize Tool (Loads config from tool.json)
tool = BaseTool(__file__)

# 3. Define Logic
@tool.app.get("/")
def read_root():
    return {{"message": f"Hello from {{tool.title}}!"}}

# 4. Define Widget
def widget_html():
    return f\"\"\"
    <!DOCTYPE html>
    <div style="padding:10px; font-family: sans-serif;">
        <h3>{{tool.title}}</h3>
        <p>Running on port {{tool.port}}</p>
    </div>
    \"\"\"

tool.add_widget_route(widget_html)

if __name__ == "__main__":
    tool.run()
"""

def create_tool(name, port):
    folder_name = name.lower().replace(" ", "_")
    tool_dir = TOOLS_DIR / folder_name

    if tool_dir.exists():
        print(f"❌ Error: Tool '{folder_name}' already exists.")
        return

    print(f"🔨 Creating tool '{name}'...")
    tool_dir.mkdir(parents=True)

    # 1. Create tool.json (The Manifest)
    manifest = {
        "key": folder_name,
        "name": folder_name,
        "title": name,
        "version": "1.0.0",
        "port": int(port),
        "entry_point": "main.py",
        "auto_start": True,
        "has_widget": True
    }

    with open(tool_dir / "tool.json", "w") as f:
        json.dump(manifest, f, indent=4)

    # 2. Create main.py
    with open(tool_dir / "main.py", "w") as f:
        f.write(MAIN_TEMPLATE.format(folder=folder_name))

    # 3. Create requirements.txt (Empty)
    (tool_dir / "requirements.txt").touch()

    print(f"✅ Success! Created tools/{folder_name}")
    print(f"👉 Run it: python tools/{folder_name}/main.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new Kolibri Tool")
    parser.add_argument("name", help="Name of the tool (e.g., 'Notes App')")
    parser.add_argument("--port", type=int, required=True, help="Port to run on")
    
    args = parser.parse_args()
    create_tool(args.name, args.port)
