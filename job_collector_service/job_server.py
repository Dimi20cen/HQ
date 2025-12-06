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
                date_scraped TEXT,
                description TEXT
            )
        """)

init_db()

# --- Routes ---
@app.post("/check")
async def check_job(request: Request):
    """Checks if a URL exists in the DB and returns the data."""
    data = await request.json()
    url_to_check = data.get("url")

    if not url_to_check:
        return JSONResponse({"found": False})

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row  # This allows accessing columns by name
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE url = ?", (url_to_check,))
            row = cursor.fetchone()

            if row:
                # Convert the DB row to a standard dictionary
                return {
                    "found": True,
                    "data": {
                        "title": row["title"],
                        "company": row["company"],
                        "location": row["location"],
                        "url": row["url"],
                        "date_scraped": row["date_scraped"],
                        "description": row["description"]
                    }
                }
            else:
                return {"found": False}
    except Exception as e:
        print(f"Error checking job: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/save")
async def save_job(request: Request):
    data = await request.json()
    
    if not data:
        return JSONResponse({"error": "No data"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            # CHANGED: Replaced "INSERT OR IGNORE" with "INSERT ... ON CONFLICT ... DO UPDATE"
            conn.execute("""
                INSERT INTO jobs (title, company, location, url, date_scraped, description)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    location=excluded.location,
                    date_scraped=excluded.date_scraped,
                    description=excluded.description
            """, (
                data.get('title', 'Unknown'),
                data.get('company', 'Unknown'),
                data.get('location', 'Unknown'),
                data.get('url', ''),
                data.get('date_scraped', ''),
                data.get('description', '')
            ))
            
            # Note: We can't rely on rowcount for upserts in the same way, 
            # but we can grab the total count still.
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            
        print(f"Saved/Updated job: {data.get('title')}")
        return {"status": "saved", "total_count": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/widget", response_class=HTMLResponse)
def widget():
    """Displays jobs in a clean, truncated list with hover-reveal"""
    
    jobs = []
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 50").fetchall()

    list_html = ""
    
    if not jobs:
        list_html = """
        <div class="empty-state">
            No jobs saved yet.
        </div>
        """
    
    for job in jobs:
        date_str = job['date_scraped'][:10] if job['date_scraped'] else "-"
        
        # We add title="..." to the HTML elements so hovering reveals the full text
        list_html += f"""
        <a class="row" href="{job['url']}" target="_blank">
            <div class="col-title" title="{job['title']}">{job['title']}</div>
            <div class="col-company" title="{job['company']}">{job['company']}</div>
            <div class="col-loc" title="{job['location']}">{job['location']}</div>
            <div class="col-date">{date_str}</div>
        </a>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            :root {{
                --bg: #ffffff;
                --text-main: #222;
                --text-sub: #666;
                --border: #f0f0f0;
                --hover-bg: #f8f9fa;
                --accent-bar: #333;
            }}
            
            * {{ box-sizing: border-box; }}
            
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: var(--bg);
                padding: 10px 30px; 
                margin: 0 auto;
                max-width: 1200px;
                color: var(--text-main);
            }}

            h4 {{
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #aaa;
                margin-bottom: 15px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }}

            /* THE ROW CONTAINER */
            .row {{
                display: flex;
                align-items: center;
                padding: 12px 0;
                text-decoration: none;
                border-bottom: 1px solid var(--border);
                transition: all 0.15s ease;
                color: inherit;
                gap: 20px; /* Space between columns */
            }}

            .row:hover {{
                background-color: var(--hover-bg);
                padding-left: 10px;
                padding-right: 10px;
                margin-left: -10px;
                margin-right: -10px;
                border-radius: 4px;
            }}

            /* --- COLUMNS --- */

            /* 1. Title: Takes all remaining space, truncates if needed */
            .col-title {{
                flex: 1; 
                font-weight: 600;
                font-size: 14px;
                color: var(--text-main);
                
                /* Truncation Magic */
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                min-width: 0; /* Critical for flex truncation */
            }}

            /* 2. Company: Fixed visual weight, truncates */
            .col-company {{
                width: 180px;
                font-size: 13px;
                color: var(--text-sub);
                
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex-shrink: 0; /* Don't shrink below 180px */
            }}

            /* 3. Location: Fixed visual weight, truncates */
            .col-loc {{
                width: 140px;
                font-size: 12px;
                color: #999;
                
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex-shrink: 0; 
            }}
            
            /* 4. Date: Fixed width, never truncates */
            .col-date {{
                width: 85px;
                font-size: 11px;
                color: #bbb;
                font-family: monospace;
                text-align: right;
                flex-shrink: 0;
            }}

            /* RESPONSIVE: Hide Location on small screens */
            @media (max-width: 700px) {{
                .col-loc {{ display: none; }}
                .col-company {{ width: 120px; }}
            }}
            
            .empty-state {{ padding: 40px; text-align: center; color: #ccc; }}
        </style>
    </head>
    <body>
        <div>
            {list_html}
        </div>
    </body>
    </html>
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
