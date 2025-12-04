import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from blocker_service import BlockerService

app = Flask(__name__)

# Initialize the service
BASE_DIR = Path(__file__).resolve().parent
service = BlockerService(config_path=str(BASE_DIR / "config.json"))

# Start worker thread immediately
service.start()

# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------
@app.get("/status")
def status():
    """Return current service status."""
    return jsonify(service.get_status())

@app.post("/start")
def start():
    service.start()
    return jsonify({"started": True})

@app.post("/stop")
def stop():
    service.stop()
    return jsonify({"stopped": True})

@app.post("/reload")
def reload_config():
    service.reload_config()
    return jsonify({"reloaded": True})

@app.post("/update-config")
def update_config():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400
    try:
        service.update_config(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"updated": True})

# -------------------------------------------------------------
# THE WIDGET UI (New Addition)
# -------------------------------------------------------------
@app.route("/widget")
def widget():
    # 1. Read the current config to pre-fill the form
    try:
        with open(service.core.config_path, "r") as f:
            config = json.load(f)
            # Default to the first window for the simple UI
            first_window = config.get("blocked_windows", [{}])[0]
            current_start = first_window.get("start", "09:00")
            current_end = first_window.get("end", "17:00")
            # Join processes with newlines for the text area
            current_procs = "\n".join(first_window.get("processes", []))
    except Exception:
        current_start, current_end, current_procs = "09:00", "17:00", ""

    # 2. Render the HTML Form
    html = """
    <!DOCTYPE html>
    <style>
        body {
            font-family: sans-serif;
            padding: 8px;
            margin: 0;
            font-size: 12px;
            background: #fff;
            color: #222;
        }

        .row {
            display: flex;
            gap: 6px;
            margin-bottom: 6px;
            width: 100%;
        }

        input, textarea, button {
            font-size: 12px;
            border: 1px solid #ccc;
            border-radius: 2px;
            background: #fafafa;
            padding: 4px;
            box-sizing: border-box;
        }

        .time-input {
            flex: 1;
        }

        button {
            padding: 4px 10px;
            cursor: pointer;
            white-space: nowrap;
            background: #f2f2f2;
        }
        button:hover {
            background: #e6e6e6;
        }

        textarea {
            width: 100%;
            height: 70px;
            resize: vertical;
            font-family: monospace;
        }
    </style>

    <!-- Top row: Start | End | Save -->
    <div class="row">
        <input class="time-input" id="start" value="{{ start }}" placeholder="Start (HH:MM)">
        <input class="time-input" id="end" value="{{ end }}" placeholder="End (HH:MM)">
        <button onclick="saveConfig()">Save</button>
    </div>

    <!-- Full-width processes textarea -->
    <textarea id="procs" placeholder="blocked.exe\nother.exe">{{ procs }}</textarea>

    <script>
        async function saveConfig() {
            const start = document.getElementById('start').value.trim();
            const end = document.getElementById('end').value.trim();
            const rawProcs = document.getElementById('procs').value;

            const processes = rawProcs.split('\\n')
                .map(p => p.trim())
                .filter(Boolean);

            const newConfig = {
                "check_interval_seconds": 3,
                "blocked_windows": [{
                    "start": start,
                    "end": end,
                    "processes": processes
                }]
            };

            const btn = event.target;
            const original = btn.innerText;
            btn.innerText = "Saving…";

            try {
                const res = await fetch('/update-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newConfig)
                });

                btn.innerText = res.ok ? "Saved" : "Error";
                setTimeout(() => btn.innerText = original, 800);
            } catch {
                alert("Connection error");
                btn.innerText = original;
            }
        }
    </script>
    """

    
    return render_template_string(html, start=current_start, end=current_end, procs=current_procs)


# -------------------------------------------------------------
# Server entrypoint
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Blocker service running on http://127.0.0.1:9001")
    app.run(host="127.0.0.1", port=9001)
