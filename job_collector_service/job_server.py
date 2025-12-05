import sys
import sqlite3
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 1. Enable CORS (So Chrome Extension can talk to us)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your Extension ID
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "jobs.db"

# 2. Database Setup (SQLite)
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT UNIQUE,
                date_scraped TEXT
            )
        """)

init_db()

# --- Routes ---

@app.post("/save")
async def save_job(request: Request):
    # in FastAPI, we await the json body
    data = await request.json()
    
    if not data:
        return JSONResponse({"error": "No data"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO jobs (title, company, location, url, date_scraped)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data.get('title', 'Unknown'), 
                data.get('company', 'Unknown'), 
                data.get('location', 'Unknown'), 
                data.get('url', ''), 
                data.get('date_scraped', '')
            ))
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        print(f"Saved job: {data.get('title')}")
        return {"status": "saved"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/widget", response_class=HTMLResponse)
def widget():
    """Displays the list of saved jobs in the Kolibri Dashboard"""
    
    # Fetch data
    jobs = []
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 20").fetchall()

    # Generate HTML (Simple f-string method to avoid Jinja dependency for just one file)
    cards_html = ""
    if not jobs:
        cards_html = "<div class='empty'>No jobs collected yet.<br>Use the Extension!</div>"
    
    for job in jobs:
        cards_html += f"""
        <div class="job-card">
            <div class="header">
                <a class="title" href="{job['url']}" target="_blank">{job['title']}</a>
                <span class="date">{job['date_scraped'][:10]}</span>
            </div>
            <div class="company">{job['company']}</div> 
            <div class="location">{job['location']}</div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', sans-serif; 
            padding: 10px; margin: 0; 
            font-size: 12px; color: #333;
        }}
        .empty {{ color: #999; font-style: italic; text-align: center; margin-top: 40px; }}
        .job-card {{ 
            background: #fff;
            border: 1px solid #e0e0e0; 
            border-left: 4px solid #007bff; 
            padding: 8px 10px; margin-bottom: 6px; 
            border-radius: 2px;
        }}
        .job-card:hover {{ background: #f9f9f9; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 2px; }}
        .title {{ font-weight: 600; font-size: 13px; color: #007bff; text-decoration: none; }}
        .company {{ color: #555; font-size: 11px; font-weight: 500;}}
        .location {{ color: #777; font-size: 11px; }}
        .date {{ font-size: 10px; color: #999; }}
    </style>
    <body>
        {cards_html}
    </body>
    """
    return html

if __name__ == "__main__":
    PORT = 30001
    print(f"Job Collector running on http://127.0.0.1:{PORT}")
    try:
        uvicorn.run(app, host="127.0.0.1", port=PORT)
    except OSError:
        print(f"CRITICAL: Port {PORT} is already in use!")
        sys.exit(1)
