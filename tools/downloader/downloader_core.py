import os
import threading
import uuid
import time
import json
import logging
import queue
import random
import yt_dlp
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from http.cookiejar import MozillaCookieJar

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
KNOWN_PROVIDERS = ("youtube.com", "youtu.be", "vimeo.com")

logging.basicConfig(
    filename='downloader.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DownloaderCore:
    def __init__(self, project_root):
        # 1. SETUP LOGGER FIRST
        self.logger = logging.getLogger("DownloaderCore")
        
        self.project_root = Path(project_root)
        self.shared_dir = self.project_root / "shared" / "downloads"
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.shared_dir / "history.json"
        
        self.jobs = {}
        self.lock = threading.Lock()
        
        # SAFETY QUEUE
        self.download_queue = queue.Queue()
        
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.processor_thread.start()
        
        self._run_janitor()

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def list_files(self):
        files = []
        if self.shared_dir.exists():
            with os.scandir(self.shared_dir) as entries:
                for f in entries:
                    if f.is_file() and not f.name.startswith(".") and f.name != "history.json" and not f.name.endswith(".txt"):
                        files.append({
                            "name": f.name,
                            "size": f.stat().st_size,
                            "created": f.stat().st_ctime
                        })
        return sorted(files, key=lambda x: x['created'], reverse=True)

    def get_history(self):
        if not self.history_file.exists(): return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []

    def start_download(self, url: str, mode: str = "video", use_login: bool = False):
        try:
            clean_url = self._validate_url(url)
        except ValueError as e:
            return {"error": str(e)}

        job_id = str(uuid.uuid4())
        
        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "url": clean_url,
                "mode": mode,
                "use_login": use_login,
                "status": "pending",
                "progress": 0,
                "title": "Queued...",
                "filename": None,
                "error": None
            }

        self.download_queue.put((job_id, clean_url, mode, use_login))
        self.logger.info(f"Job queued: {job_id} for {clean_url}")
        return job_id

    def cancel_download(self, job_id):
        with self.lock:
            if job_id in self.jobs and self.jobs[job_id]['status'] in ['pending', 'downloading']:
                self.jobs[job_id]['status'] = 'cancelling'
                return True
        return False

    def get_job_status(self, job_id):
        with self.lock:
            return self.jobs.get(job_id, {}).copy()

    # ---------------------------------------------------------
    # Internal: Processor Loop
    # ---------------------------------------------------------
    def _processor_loop(self):
        self.logger.info("Background Processor Started")
        while True:
            try:
                job_id, url, mode, use_login = self.download_queue.get()

                if self._check_cancel(job_id):
                    self.download_queue.task_done()
                    continue

                self.logger.info(f"Processor launching job: {job_id}")
                try:
                    t = threading.Thread(
                        target=self._worker_entrypoint, 
                        args=(job_id, url, mode, use_login), 
                        daemon=True
                    )
                    t.start()
                except Exception as e:
                    self.logger.error(f"Failed to spawn worker for {job_id}: {e}")
                    self._update_job(job_id, status="error", error="System Resource Error")

                self.download_queue.task_done()
                
                # Throttle
                if use_login:
                     time.sleep(random.uniform(5.0, 7.0))
                else:
                    delay = random.uniform(2.0, 5.0)
                    time.sleep(delay)

            except Exception as e:
                self.logger.error(f"FATAL ERROR in Processor Loop: {e}")
                time.sleep(1)

    # ---------------------------------------------------------
    # Internal: Janitor & Utilities
    # ---------------------------------------------------------
    def _run_janitor(self):
        try:
            now = time.time()
            for f in self.shared_dir.glob("cookies_*.txt"):
                try: os.remove(f)
                except: pass
            for f in self.shared_dir.glob("*.part"):
                if now - f.stat().st_mtime > 86400:
                    try: os.remove(f)
                    except: pass
        except: pass

    def _validate_url(self, url):
        if not url: raise ValueError("URL is empty")
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'): raise ValueError("URL must start with http/https")
        if not parsed.netloc: raise ValueError("Invalid domain")
        return url

    def _append_history(self, record):
        with self.lock:
            history = []
            if self.history_file.exists():
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except: pass
            record['timestamp'] = datetime.now().isoformat()
            history.insert(0, record)
            history = history[:100]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)

    # ---------------------------------------------------------
    # Worker Logic
    # ---------------------------------------------------------
    def _worker_entrypoint(self, job_id, url, mode, use_login):
        self._update_job(job_id, status="downloading", title="Initializing...")
        
        cookie_path = self.shared_dir / f"cookies_{job_id}.txt"
        target_url = url
        needs_cleanup = False
        scanned_title = None  # <--- NEW: Store page title

        try:
            if self._check_cancel(job_id): return

            # PHASE 1: COOKIE EXTRACTION (The Bridge)
            if use_login:
                self.logger.info(f"Job {job_id}: Extracting Firefox cookies...")
                self._update_job(job_id, title="Bridging Browser Session...")
                try:
                    subprocess.run(
                        [
                            "yt-dlp", "--cookies-from-browser", "firefox", 
                            "--cookies", str(cookie_path),
                            "--skip-download", "https://www.youtube.com" 
                        ],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30
                    )
                    if cookie_path.exists():
                        self.logger.info("Cookies extracted successfully.")
                        needs_cleanup = True
                    else:
                        raise Exception("Cookie extraction failed")
                except Exception as e:
                    self.logger.error(f"Cookie Dump Failed: {e}")
                    raise Exception("Could not access Firefox cookies. Is it installed?")

            # PHASE 2: INTELLIGENCE SCANNING
            # We assume generic/authenticated sites need the scanner
            is_generic_site = not self._is_direct_provider(url)
            
            if is_generic_site:
                self._update_job(job_id, title="Scanning authenticated page...")
                
                # --- UPDATED: Unpack URL and TITLE ---
                target_url, scanned_title = self._resolve_generic_url(url, job_id, cookie_path if use_login else None)
                
                self.logger.info(f"Scanner result: {target_url} (Title: {scanned_title})")
            else:
                self.logger.info(f"Direct provider detected: {url}")

            if self._check_cancel(job_id): return

            # PHASE 3: DOWNLOAD ENGINE
            self._update_job(job_id, title="Processing download...")
            
            final_cookie_path = cookie_path if cookie_path.exists() else None
            
            self._execute_yt_dlp(
                job_id, 
                target_url, 
                mode, 
                cookie_path=final_cookie_path,
                custom_title=scanned_title # <--- PASS THE TITLE
            )

        except Exception as e:
            error_msg = str(e)
            
            # 1. Catch Cancellation
            if "Download cancelled" in error_msg:
                self._update_job(job_id, status="cancelled", progress=0)
                self.logger.info(f"Job {job_id} cancelled successfully.")
            
            # 2. Catch Chrome Lock (NEW)
            elif "Could not copy Chrome cookie database" in error_msg:
                self._update_job(job_id, status="error", error="Chrome is locked! Please close browser.")
                self.logger.error(f"Job {job_id} failed: Chrome file locked.")
            
            # 3. Generic Error
            else:
                clean_error = error_msg.split(";")[0].replace("ERROR:", "").strip()
                self._update_job(job_id, status="error", error=clean_error)
                self.logger.error(f"Job {job_id} failed: {clean_error}")
        
        finally:
            if needs_cleanup and cookie_path.exists():
                try: os.remove(cookie_path)
                except: pass

    # ---------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------
    def _check_cancel(self, job_id):
        with self.lock:
            status = self.jobs.get(job_id, {}).get('status')
            if status == 'cancelling':
                self.jobs[job_id]['status'] = 'cancelled'
                return True
        return False

    def _is_direct_provider(self, url):
        return any(provider in url for provider in KNOWN_PROVIDERS)

    def _resolve_generic_url(self, url, job_id, auth_cookie_path=None):
        final_url = url
        page_title = None
        found_embeds = []
        found_streams = []

        run_headless = (auth_cookie_path is None)

        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(channel="chrome", headless=run_headless)
                except Exception as e:
                    self.logger.warning(f"RIP: System Chrome not found ({e}). Falling back to bundled Chromium.\n You have issue, you don't have Chromiun installed. \n You can install it using `playwright install chromium`")
                    browser = p.chromium.launch(headless=run_headless)

                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=USER_AGENT
                )
                # Stealth Injection: Hide the automation flag
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                if auth_cookie_path and auth_cookie_path.exists():
                    try:
                        cj = MozillaCookieJar(auth_cookie_path)
                        cj.load(ignore_discard=True, ignore_expires=True)
                        playwright_cookies = []
                        for c in cj:
                            playwright_cookies.append({
                                "name": c.name, "value": c.value, "domain": c.domain,
                                "path": c.path, "secure": c.secure, "expires": c.expires
                            })
                        context.add_cookies(playwright_cookies)
                    except: pass

                page = context.new_page()

                def handle_request(req):
                    u = req.url
                    if "youtube.com/embed/" in u or "player.vimeo.com/video/" in u:
                        found_embeds.append(u)
                    elif ".m3u8" in u or ".mpd" in u or "manifest" in u:
                        if "doubleclick" not in u and "googlead" not in u:
                            found_streams.append(u)

                page.on("request", handle_request)
                
                self.logger.info(f"Playwright navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                time.sleep(random.uniform(2.0, 3.0)) 

                for _ in range(3):
                    if self._check_cancel(job_id): 
                        browser.close()
                        raise Exception("Download cancelled")
                    page.mouse.wheel(0, random.randint(200, 500))
                    time.sleep(1.0)

                # --- NEW: GRAB TITLE ---
                try:
                    page_title = page.title().strip()
                except: 
                    page_title = "video_download"

                # PRIORITY LOGIC
                if found_embeds:
                    final_url = found_embeds[0]
                elif found_streams:
                    final_url = found_streams[0]
                else:
                    frame = page.query_selector('iframe[src*="youtube.com"], iframe[src*="youtu.be"], iframe[src*="vimeo.com"]')
                    if frame:
                        final_url = frame.get_attribute("src")
                    else:
                        video = page.query_selector('video source')
                        if video:
                            src = video.get_attribute('src')
                            if src and not src.startswith("blob:"):
                                final_url = src

                browser.close()
        except Exception as e:
            if "Download cancelled" in str(e): raise e
            self.logger.warning(f"Playwright warning: {e}")
        
        return final_url, page_title # <--- RETURN TUPLE

    def _execute_yt_dlp(self, job_id, url, mode, cookie_path=None, custom_title=None):
        ydl_opts = {
            "quiet": True,
            "noprogress": True,
            "progress_hooks": [lambda d: self._progress_hook(job_id, d)],
            "outtmpl": str(self.shared_dir / "%(title)s.%(ext)s"),
            "windowsfilenames": True, 
            "http_headers": {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
            }
        }

        if cookie_path:
            ydl_opts["cookiefile"] = str(cookie_path)

        if mode == "audio":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
        else:
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # --- FIX: OVERWRITE BAD TITLES ---
            detected_title = info.get('title', 'video')
            
            # If the engine returns a lazy name (manifest/master) AND we have a better one:
            bad_names = ['manifest', 'index', 'master', 'playlist', 'video', 'stream']
            
            if custom_title and (detected_title.lower() in bad_names or not detected_title):
                self.logger.info(f"Overwriting bad title '{detected_title}' with '{custom_title}'")
                info['title'] = custom_title  # Inject the web page title
                
                # We must re-configure the output template to ensure it uses the new title
                # We can't just change 'outtmpl' here easily, but modifying info['title']
                # usually works if we call prepare_filename again.
            
            title = info['title']
            self._update_job(job_id, title=title)

            temp_filename = ydl.prepare_filename(info)
            fpath = Path(temp_filename)

            if mode == "audio": fpath = fpath.with_suffix(".mp3")
            else: fpath = fpath.with_suffix(".mp4")

            if fpath.stem.strip() == "_" or not fpath.stem.strip():
                new_name = f"video_{job_id}{fpath.suffix}"
                fpath = fpath.with_name(new_name)
                ydl.params['outtmpl']['default'] = str(fpath)

            if fpath.exists():
                self._update_job(job_id, status="completed", progress=100, filename=fpath.name)
                return 

            if self._check_cancel(job_id): raise Exception("Download cancelled")
            
            # Trick: yt-dlp might re-fetch info on download(), so we pass the specific URL 
            # OR we try to force the output template if we are worried.
            # But usually modifying info is hard for the subsequent download call.
            # SAFER: Force the output template to the known good path we just calculated.
            ydl.params['outtmpl']['default'] = str(fpath)
            
            ydl.download([url])
            
            self._update_job(job_id, status="completed", progress=100, filename=fpath.name)
            self._append_history({
                "job_id": job_id,
                "title": title,
                "filename": fpath.name,
                "original_url": url,
                "mode": mode
            })

    def _save_cookies(self, cookies, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in cookies:
                exp = c.get('expires', time.time() + 31536000)
                f.write(f"{c.get('domain', '')}\t{'TRUE' if c.get('domain', '').startswith('.') else 'FALSE'}\t{c.get('path', '/')}\t{'TRUE' if c.get('secure', False) else 'FALSE'}\t{int(exp)}\t{c.get('name', '')}\t{c.get('value', '')}\n")

    def _update_job(self, job_id, **kwargs):
        with self.lock:
            if job_id in self.jobs: self.jobs[job_id].update(kwargs)

    def _progress_hook(self, job_id, d):
        with self.lock:
            if self.jobs.get(job_id, {}).get('status') == 'cancelling': raise Exception("Download cancelled")
        if d['status'] == 'downloading':
            try: self._update_job(job_id, progress=float(d.get('_percent_str', '0%').replace('%','')))
            except: pass
        elif d['status'] == 'finished':
            self._update_job(job_id, progress=100)