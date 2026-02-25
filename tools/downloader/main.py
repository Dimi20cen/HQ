import sys
import os
import platform
import subprocess
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root so BaseTool can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from tools.sdk.base_tool import BaseTool
from downloader_core import DownloaderCore

tool = BaseTool(__file__)
core = DownloaderCore(PROJECT_ROOT)

tool.app.mount("/files", StaticFiles(directory=core.shared_dir), name="files")

# ---------------------------
# API Routes
# ---------------------------
@tool.app.get("/list")
def list_files():
    return core.list_files()

@tool.app.post("/start")
async def start_download(request: Request):
    data = await request.json()
    url = data.get("url")
    mode = data.get("mode", "video")
    use_login = data.get("use_login", False)

    if not url:
        return JSONResponse({"error": "Missing 'url'"}, status_code=400)

    job_id = core.start_download(url, mode, use_login)
    return {"job_id": job_id, "status": "started"}

@tool.app.post("/cancel/{job_id}")
def cancel_job(job_id: str):
    success = core.cancel_download(job_id)
    return {"success": success}

@tool.app.get("/status/{job_id}")
def get_status(job_id: str):
    status = core.get_job_status(job_id)
    if not status:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return status

@tool.app.post("/open_folder")
def open_folder():
    """Opens the shared/downloads folder in the OS file explorer."""
    path = str(core.shared_dir)
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux
            subprocess.Popen(["xdg-open", path])
        return {"status": "opened"}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------
# Widget
# ---------------------------
def widget_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --bg: #fdf5fb;
                --surface: #fff9fd;
                --surface-soft: #f7f9ff;
                --text: #372f56;
                --muted: #756d95;
                --border: rgba(143, 119, 171, 0.28);
                --control-icon: #755f98;
                --status-running: #3b9d72;
                --status-stopped: #b66a91;
                --status-info: #7d8cc3;
                --status-info-strong: #6f7eb2;
            }
            body { font-family: "Manrope", "Space Grotesk", "Segoe UI", sans-serif; padding: 20px; background: var(--bg); margin: 0; color: var(--text); }
            .container { max-width: 600px; margin: 0 auto; }

            /* INPUT AREA */
            .input-row { 
                display: flex; gap: 10px; margin-bottom: 20px;
                align-items: flex-start; /* Aligns input and button group to the top */
            }
            .input-wrapper {
                flex: 1; display: flex; 
                box-shadow: none;
                border-radius: 8px; border: 1px solid var(--border); overflow: hidden;
                height: 42px; /* Fixed height to match button roughly */
                background: var(--surface);
            }
            input {
                flex: 1; padding: 12px 15px; border: none; outline: none; font-size: 14px;
                background: transparent; color: var(--text);
            }
            select { 
                padding: 0 15px; border: none; border-left: 1px solid var(--border);
                background: var(--surface-soft); font-size: 13px; color: var(--muted); outline: none; cursor: pointer; font-weight: 500;
            }
            
            /* BUTTON GROUP (Right Side) */
            .action-group {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 6px;
            }

            button#btn-main { 
                height: 42px;
                padding: 0 20px; background: var(--surface-soft); color: var(--text); border: 1px solid var(--border);
                border-radius: 8px; font-weight: 600; cursor: pointer; 
                box-shadow: none; transition: transform 0.1s, background 0.12s ease;
            }
            button#btn-main:hover { background: #f0ebf7; }
            button#btn-main:active { transform: translateY(2px); }

            /* LOGIN TOGGLE */
            .login-wrapper {
                display: flex; align-items: center; gap: 5px; 
                font-size: 11px; color: var(--muted); font-weight: 500;
                padding-right: 2px;
            }
            .login-wrapper input { padding: 0; margin: 0; cursor: pointer; flex: 0; }
            .login-wrapper label { cursor: pointer; }

            /* JOBS CONTAINER */
            #jobs-container { display: flex; flex-direction: column; gap: 10px; }

            /* INDIVIDUAL JOB CARD */
            .job-card {
                background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
                padding: 12px; box-shadow: none;
                animation: slideDown 0.3s ease-out;
            }
            @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

            .job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
            .job-title { font-size: 13px; font-weight: 600; color: var(--text); max-width: 70%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .job-meta { font-size: 11px; color: var(--muted); }
            
            .progress-track { width: 100%; height: 6px; background: #ebe6f1; border-radius: 3px; overflow: hidden; margin-bottom: 8px; }
            .progress-fill { height: 100%; background: var(--status-info); width: 0%; transition: width 0.5s ease; }
            
            .job-actions { display: flex; justify-content: flex-end; gap: 15px; align-items: center; }
            
            button.btn-sm { background: none; border: none; font-size: 12px; cursor: pointer; padding: 0; }
            .btn-cancel { color: var(--status-stopped); }
            
            /* Success State Actions */
            .success-actions { display: none; gap: 10px; align-items: center; }
            .btn-folder { color: var(--control-icon); font-weight: 500; display: flex; align-items: center; gap: 4px; padding: 4px 8px; background: #f3ebf7; border-radius: 4px; }
            .btn-folder:hover { background: #eadcf2; }
            .saved-text { color: var(--status-running); font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 4px; }

        </style>
    </head>
    <body>
        <div class="container">
            
            <div class="input-row">
                <div class="input-wrapper">
                    <input id="url" placeholder="Paste YouTube/Video Link..." autocomplete="off" />
                    <select id="mode">
                        <option value="video">Video</option>
                        <option value="audio">Audio</option>
                    </select>
                </div>
                
                <div class="action-group">
                    <button id="btn-main" onclick="spawnJob()">Add</button>
                    
                    <div class="login-wrapper">
                        <input type="checkbox" id="use-login">
                        <label for="use-login" title="Uses your local Chrome session for access">Login</label>
                    </div>
                </div>
            </div>

            <div id="jobs-container"></div>
        </div>

        <script>
            async function spawnJob() {
                const urlInput = document.getElementById("url");
                const modeInput = document.getElementById("mode");
                const loginInput = document.getElementById("use-login");

                const url = urlInput.value;
                const mode = modeInput.value;
                const use_login = loginInput.checked;

                if(!url) return;

                const cardId = "card-" + Date.now();
                createJobCard(cardId, url);
                
                urlInput.value = "";
                
                try {
                    const res = await fetch("/start", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({url, mode, use_login})
                    });
                    const data = await res.json();
                    
                    if(data.job_id) {
                        trackJob(data.job_id, cardId);
                    } else {
                        markError(cardId, data.error || "Failed to start");
                    }
                } catch(e) {
                    markError(cardId, "Network Error");
                }
            }

            function createJobCard(cardId, initialUrl) {
                const container = document.getElementById("jobs-container");
                const div = document.createElement("div");
                div.className = "job-card";
                div.id = cardId;
                div.innerHTML = `
                    <div class="job-header">
                        <span class="job-title">Initializing...</span>
                        <span class="job-meta">0%</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="job-actions">
                        <button class="btn-sm btn-cancel" onclick="requestCancel('${cardId}')">Cancel</button>
                        
                        <div class="success-actions">
                            <span class="saved-text">✔ Saved</span>
                            <button class="btn-sm btn-folder" onclick="openFolder()">📂 Open Folder</button>
                        </div>
                    </div>
                `;
                container.prepend(div);
            }

            function trackJob(jobId, cardId) {
                const card = document.getElementById(cardId);
                card.dataset.jobId = jobId; 

                const interval = setInterval(async () => {
                    try {
                        const res = await fetch(`/status/${jobId}`);
                        if(!res.ok) return; 
                        const data = await res.json();

                        updateCard(card, data, interval);

                    } catch(e) {
                        console.error(e);
                    }
                }, 1000);
            }

            function updateCard(card, data, interval) {
                const titleEl = card.querySelector(".job-title");
                const metaEl = card.querySelector(".job-meta");
                const fillEl = card.querySelector(".progress-fill");
                const cancelBtn = card.querySelector(".btn-cancel");
                const successActions = card.querySelector(".success-actions");

                titleEl.innerText = data.title || "Processing...";
                
                const currentW = parseFloat(fillEl.style.width) || 0;
                if (data.progress > currentW) fillEl.style.width = data.progress + "%";
                metaEl.innerText = Math.round(data.progress) + "%";

                if (["completed", "error", "cancelled"].includes(data.status)) {
                    clearInterval(interval);
                    
                    if (data.status === "completed") {
                        fillEl.style.width = "100%";
                        fillEl.style.background = "var(--status-running)";
                        metaEl.innerText = "";
                        
                        // Switch Actions
                        cancelBtn.style.display = "none";
                        successActions.style.display = "flex";
                    } else if (data.status === "error") {
                        fillEl.style.background = "var(--status-stopped)";
                        metaEl.innerText = "Error";
                        titleEl.innerText = data.error;
                    }
                    else if (data.status === "cancelled") {
                        card.style.opacity = "0.5";
                        titleEl.innerText = "Cancelled";
                    }
                }
            }

            async function openFolder() {
                // Calls the Python backend to open the OS file explorer
                await fetch("/open_folder", { method: "POST" });
            }

            async function requestCancel(cardId) {
                const card = document.getElementById(cardId);
                const jobId = card.dataset.jobId;
                if(jobId) {
                    await fetch(`/cancel/${jobId}`, { method: 'POST' });
                    card.querySelector(".job-title").innerText = "Cancelling...";
                } else {
                    card.remove();
                }
            }

            function markError(cardId, msg) {
                const card = document.getElementById(cardId);
                card.querySelector(".progress-fill").style.background = "var(--status-stopped)";
                card.querySelector(".job-title").innerText = msg;
            }
        </script>
    </body>
    </html>
    """

tool.add_widget_route(widget_html)

if __name__ == "__main__":
    tool.run()
