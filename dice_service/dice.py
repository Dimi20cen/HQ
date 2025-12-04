import random
from flask import Flask, jsonify

app = Flask(__name__)

# --- The Logic ---
@app.route("/roll", methods=["POST", "GET"])
def roll_dice():
    result = random.randint(1, 6)
    return jsonify({"result": result, "message": f"You rolled a {result}!"})

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ready"})

# --- The Entry Point ---
if __name__ == "__main__":
    # We choose a safe port: 20001
    print("Dice Roller running on port 20001")
    app.run(host="127.0.0.1", port=20001)
