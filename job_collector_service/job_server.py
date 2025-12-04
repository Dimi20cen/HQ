import sqlite3
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS so the Chrome Extension can talk to us
CORS(app)

DB_FILE = "jobs.db"

def init_db():
    # Automatically creates file if it doesn't exist
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                date_scraped TEXT
            )
        """)

init_db()

@app.route("/save", methods=["POST"])
def save_job():
    data = request.json
    if not data: return jsonify({"error": "No data"}), 400

    # ZERO race conditions here. SQLite handles the locking.
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO jobs (title, company, location, url, date_scraped)
            VALUES (?, ?, ?, ?, ?)
        """, (data.get('title'), data.get('company'), data.get('location'), 
              data.get('url'), data.get('date_scraped')))
    
    return jsonify({"status": "saved"})

@app.route("/widget")
def widget():
    with sqlite3.connect(DB_FILE) as conn:
        # Get row factory to access columns by name (like a dict)
        conn.row_factory = sqlite3.Row 
        jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 20").fetchall()
    
    html = """
    <!DOCTYPE html>
    <style>
        /* Widget Reset */
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', sans-serif; 
            padding: 10px; 
            margin: 0; 
            font-size: 12px; 
            color: #333;
        }
        
        .empty { 
            color: #999; 
            font-style: italic; 
            text-align: center; 
            margin-top: 40px; 
        }

        .job-card { 
            background: #fff;
            border: 1px solid #e0e0e0; 
            border-left: 4px solid #007bff; 
            padding: 8px 10px; 
            margin-bottom: 6px; 
            border-radius: 2px;
            transition: background 0.1s;
        }
        .job-card:hover { background: #f9f9f9; }

        .header { display: flex; justify-content: space-between; margin-bottom: 2px; }
        .title { font-weight: 600; font-size: 13px; color: #007bff; text-decoration: none; }
        .title:hover { text-decoration: underline; }
        .date { font-size: 10px; color: #999; }
        
        .company { color: #555; font-size: 11px; font-weight: 500;}
        .location { color: #777; font-size: 11px; }
    </style>

    {% if not jobs %}
        <div class="empty">
            No jobs collected yet.<br>
            Use the "Job JSONifier" Chrome Extension!
        </div>
    {% endif %}

    {% for job in jobs[:20] %}
    <div class="job-card">
        <div class="header">
            <a class="title" href="{{ job.url }}" target="_blank">{{ job.title }}</a>
            <span class="date">{{ job.date_scraped[:10] }}</span>
        </div>
        <div class="company">{{ job.company }}</div> 
        <div class="location">{{ job.location }}</div>
    </div>
    {% endfor %}
    """
    return render_template_string(html, jobs=jobs)

if __name__ == "__main__":
    port = 30001
    print(f"Job Collector running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port)
