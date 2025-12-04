from pathlib import Path
from flask import Flask, request, jsonify
from blocker_service import BlockerService

app = Flask(__name__)

# Initialize the service
BASE_DIR = Path(__file__).resolve().parent
service = BlockerService(config_path=str(BASE_DIR / "config.json"))

# Start worker thread immediately (your requirement)
service.start()


# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------
@app.route("/widget")
def widget():
    # This HTML is what will appear INSIDE the card on the dashboard
    return """
    <style>
        body { font-family: sans-serif; padding: 10px; margin: 0; background: #fff; }
        button { width: 100%; padding: 8px; margin-top: 5px; cursor: pointer; }
        .row { display: flex; justify-content: space-between; font-size: 12px; color: #666; }
    </style>
    
    <div class="row">
        <span>Status: <strong>Active</strong></span>
        <span>Next check: 3s</span>
    </div>
    
    <button onclick="fetch('/start', {method:'POST'})">▶ Start Blocking</button>
    <button onclick="fetch('/stop', {method:'POST'})">⏸ Stop Blocking</button>
    <button onclick="fetch('/reload', {method:'POST'})">🔄 Reload Config</button>
    """

@app.get("/status")
def status():
    """Return current service status."""
    return jsonify(service.get_status())


@app.post("/start")
def start():
    """Start worker thread if not already running."""
    result = service.start()
    return jsonify({"started": result})


@app.post("/stop")
def stop():
    """Stop the worker thread."""
    result = service.stop()
    return jsonify({"stopped": result})


@app.post("/reload")
def reload_config():
    """Reload config.json into memory."""
    result = service.reload_config()
    return jsonify({"reloaded": result})


@app.post("/update-config")
def update_config():
    """
    Replace config.json with the provided body, then reload it.
    Expects JSON matching the config schema.
    """
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Invalid or missing JSON"}), 400

    try:
        service.update_config(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"updated": True})


# -------------------------------------------------------------
# Server entrypoint
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Blocker service running on http://127.0.0.1:9001")
    app.run(host="127.0.0.1", port=9001)
