import sys
import sqlite3
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

# 1. SETUP PATHS
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from tools.sdk.base_tool import BaseTool

# 2. INITIALIZE TOOL
tool = BaseTool(__file__)

# 3. DATABASE SETUP
DB_FILE = tool.root_dir / "jobs.db"

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

# Initialize DB immediately on startup
init_db()

# --- Routes ---

@tool.app.post("/check")
async def check_job(request: Request):
    """Checks if a URL exists in the DB and returns the data."""
    data = await request.json()
    url_to_check = data.get("url")

    if not url_to_check:
        return JSONResponse({"found": False})

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE url = ?", (url_to_check,))
            row = cursor.fetchone()

            if row:
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

@tool.app.post("/save")
async def save_job(request: Request):
    data = await request.json()
    
    if not data:
        return JSONResponse({"error": "No data"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
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
            
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            
        print(f"Saved/Updated job: {data.get('title')}")
        return {"status": "saved", "total_count": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@tool.app.post("/delete")
async def delete_job(request: Request):
    data = await request.json()
    url_to_delete = data.get("url")

    if not url_to_delete:
        return JSONResponse({"error": "No URL provided"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("DELETE FROM jobs WHERE url = ?", (url_to_delete,))
            
        print(f"Deleted job: {url_to_delete}")
        return {"status": "deleted"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Widget UI ---

def widget_generator():
    """Displays jobs in a clean, truncated list with hover-reveal"""
    jobs = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 50").fetchall()
    except Exception:
        pass # Handle DB errors gracefully in UI

    list_html = ""
    
    if not jobs:
        list_html = """<div class="empty-state">No jobs saved yet.</div>"""
    
    for job in jobs:
        date_str = job['date_scraped'][:10] if job['date_scraped'] else "-"
        
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
                --bg: #ffffff; --text-main: #222; --text-sub: #666;
                --border: #f0f0f0; --hover-bg: #f8f9fa;
            }}
            * {{ box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg); padding: 10px 30px; margin: 0 auto;
                max-width: 1200px; color: var(--text-main);
            }}
            .row {{
                display: flex; align-items: center; padding: 12px 0;
                text-decoration: none; border-bottom: 1px solid var(--border);
                color: inherit; gap: 20px; transition: background 0.15s;
            }}
            .row:hover {{ background-color: var(--hover-bg); }}
            .col-title {{ flex: 1; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }}
            .col-company {{ width: 180px; font-size: 13px; color: var(--text-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }}
            .col-loc {{ width: 140px; font-size: 12px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }}
            .col-date {{ width: 85px; font-size: 11px; color: #bbb; font-family: monospace; text-align: right; flex-shrink: 0; }}
            @media (max-width: 700px) {{ .col-loc {{ display: none; }} .col-company {{ width: 120px; }} }}
            .empty-state {{ padding: 40px; text-align: center; color: #ccc; }}
        </style>
    </head>
    <body>
        <div>{list_html}</div>
    </body>
    </html>
    """
    return html

# Register Widget
tool.add_widget_route(widget_generator)

if __name__ == "__main__":
    tool.run()
