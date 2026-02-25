import sys
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

# 1. Add Project Root to Path (so we can import tools.sdk)
# This allows running: python tools/meditator/main.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from tools.sdk.base_tool import BaseTool

# 2. Initialize Tool (Loads config from tool.json)
tool = BaseTool(__file__)


# 3. Define Logic
@tool.app.get("/")
def read_root():
    return {"message": f"Hello from {tool.title}!"}


@tool.app.get("/assets/{filename}")
def get_asset(filename: str):
    assets_dir = (tool.root_dir / "assets").resolve()
    file_path = (assets_dir / filename).resolve()
    if not str(file_path).startswith(str(assets_dir)) or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path)


# 4. Define Widget
def widget_html():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{tool.title}</title>
  <style>
    :root {{
      --bg: #fdf5fb;
      --panel: #fff9fd;
      --ink: #372f56;
      --muted: #756d95;
      --line: rgba(143, 119, 171, 0.28);
      --focus: #3b9d72;
      --start-a: #f3e9f7;
      --start-b: #e9deef;
      --start-ink: #4f2140;
      --wheel-bg: #332b4e;
      --wheel-line: #4a3f68;
      --wheel-text: #ece4fa;
      --wheel-dim: #a89ac8;
      --surface-soft: #f7f9ff;
      --surface-card: #ffffff;
      --control-line: #d8c3e7;
      --timer-line: #4b3d73;
      --timer-bg: #2a2340;
      --timer-text: #f8edff;
      --success: #3b9d72;
      --item-h: 42px;
      --wheel-h: 198px;
      --wheel-pad: 78px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 10px;
      color: var(--ink);
      font-family: "Manrope", "Avenir Next", "SF Pro Text", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 100% 100%, #eff1fb 0%, transparent 44%),
        radial-gradient(circle at 0% 0%, #f7e9f2 0%, transparent 40%),
        var(--bg);
    }}
    .card {{
      width: 100%;
      margin: 0;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: none;
      padding: 14px;
      display: grid;
      gap: 12px;
    }}
    .picker-shell {{
      position: relative;
      background: var(--wheel-bg);
      border: 1px solid var(--wheel-line);
      border-radius: 16px;
      box-shadow: none;
      overflow: hidden;
      transform: translateZ(0);
    }}
    .picker-shell::before,
    .picker-shell::after {{
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      height: 42px;
      z-index: 3;
      pointer-events: none;
    }}
    .picker-shell::before {{
      top: 0;
      background: linear-gradient(180deg, rgba(32, 27, 51, 0.85), rgba(32, 27, 51, 0.1));
    }}
    .picker-shell::after {{
      bottom: 0;
      background: linear-gradient(0deg, rgba(32, 27, 51, 0.85), rgba(32, 27, 51, 0.1));
    }}
    .picker-center {{
      position: absolute;
      left: 10px;
      right: 10px;
      top: 50%;
      height: var(--item-h);
      transform: translateY(-50%);
      border-radius: 12px;
      border: 1px solid rgba(213, 195, 231, 0.28);
      background: rgba(255, 255, 255, 0.06);
      box-shadow: none;
      z-index: 2;
      pointer-events: none;
    }}
    .picker-grid {{
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      padding: 8px 10px;
    }}
    .wheel {{
      height: var(--wheel-h);
      overflow-y: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;
      scroll-snap-type: y mandatory;
      padding: var(--wheel-pad) 0;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
      cursor: grab;
      touch-action: pan-y;
    }}
    .wheel.dragging {{ cursor: grabbing; }}
    .wheel::-webkit-scrollbar {{ display: none; }}
    .wheel-item {{
      height: var(--item-h);
      scroll-snap-align: center;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      color: var(--wheel-dim);
      font-weight: 560;
      letter-spacing: 0.01em;
      transition: color 120ms ease, transform 120ms ease;
      user-select: none;
    }}
    .wheel-item .num {{
      min-width: 20px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .wheel-item .unit {{
      font-size: 0.82rem;
      opacity: 0.92;
    }}
    .wheel-item.selected {{
      color: var(--wheel-text);
      transform: scale(1.02);
      font-weight: 700;
      text-shadow: 0 0 10px rgba(173, 210, 255, 0.3);
    }}
    .row {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .controls {{
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 9px;
    }}
    .controls-row {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 10px;
    }}
    .controls-row #cancelBtn {{
      justify-self: end;
    }}
    .controls-row #startPauseBtn {{
      justify-self: start;
      min-width: 110px;
    }}
    .live-time {{
      margin: 0;
      border: 1px solid var(--timer-line);
      background: var(--timer-bg);
      color: var(--timer-text);
      border-radius: 999px;
      padding: 7px 12px;
      font-family: "Menlo", "Consolas", monospace;
      font-size: 0.92rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      min-width: 88px;
      text-align: center;
      box-shadow: none;
    }}
    button {{
      border: 0;
      border-radius: 11px;
      padding: 9px 14px;
      font-size: 0.95rem;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
    }}
    button:hover {{ transform: translateY(-1px); }}
    button:active {{ transform: translateY(0); }}
    #startPauseBtn {{
      background: var(--start-a);
      color: var(--start-ink);
      border: 1px solid var(--control-line);
      box-shadow: none;
    }}
    #startPauseBtn.running {{
      filter: none;
      background: var(--start-b);
      box-shadow: none;
    }}
    button.secondary {{
      background: var(--surface-card);
      color: var(--ink);
      border: 1px solid var(--control-line);
      box-shadow: none;
    }}
    .options {{
      border: 1px solid var(--line);
      background: var(--surface-soft);
      border-radius: 14px;
      padding: 9px;
      display: grid;
      gap: 8px;
    }}
    .music-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.97rem;
      font-weight: 600;
      color: var(--ink);
    }}
    .music-row input[type="checkbox"] {{
      width: 16px;
      height: 16px;
      accent-color: var(--focus);
    }}
    .menu-row {{
      background: var(--surface-card);
      border-radius: 12px;
      border: 1px solid var(--control-line);
      padding: 8px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      box-shadow: none;
    }}
    .menu-left {{
      font-size: 0.93rem;
      color: var(--ink);
      font-weight: 620;
    }}
    .menu-right {{
      display: inline-flex;
      align-items: center;
      gap: 0;
      border: 1px solid var(--control-line);
      border-radius: 999px;
      background: var(--surface-soft);
      padding: 6px 10px;
    }}
    .menu-right select {{
      border: 0;
      background: transparent;
      color: var(--ink);
      padding: 0;
      font-size: 0.92rem;
      font-weight: 620;
      max-width: 160px;
      text-align: right;
      appearance: none;
      -webkit-appearance: none;
      outline: none;
      cursor: pointer;
    }}
    .chev {{
      display: none;
    }}
    .status {{
      min-height: 1.2rem;
      color: var(--muted);
      font-size: 0.91rem;
      font-weight: 520;
      padding: 0 4px;
    }}
    .status.active {{
      color: var(--success);
    }}
    .locked {{
      pointer-events: none;
      opacity: 0.85;
    }}
    .noselect {{ user-select: none; }}
    @media (max-width: 520px) {{
      .row {{ gap: 8px; }}
      button {{ flex: 1; }}
      .controls-row {{
        grid-template-columns: 1fr;
      }}
      .controls-row #cancelBtn,
      .controls-row #startPauseBtn {{
        justify-self: stretch;
      }}
      .picker-grid {{ gap: 6px; }}
      .wheel-item .unit {{ font-size: 0.79rem; }}
      .live-time {{ width: 100%; margin-left: 0; }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="picker-shell" role="group" aria-label="Meditation timer selector">
      <div class="picker-center"></div>
      <div class="picker-grid">
        <div class="wheel" id="hoursWheel" aria-label="Hours"></div>
        <div class="wheel" id="minutesWheel" aria-label="Minutes"></div>
        <div class="wheel" id="secondsWheel" aria-label="Seconds"></div>
      </div>
    </div>

    <div class="controls">
      <div class="controls-row">
        <button id="startPauseBtn">Start</button>
        <div class="live-time" id="timer">15:00</div>
        <button id="cancelBtn" class="secondary">Cancel</button>
      </div>
    </div>

    <div class="options">
      <div class="music-row">
        <input type="checkbox" id="musicToggle" checked />
        <label for="musicToggle">Play music during timer</label>
      </div>
      <div class="menu-row">
        <span class="menu-left">When Timer Ends</span>
        <span class="menu-right">
          <select id="finishMode" aria-label="When timer ends">
            <option value="stop" selected>Stop Music</option>
            <option value="ring">Play Ringtone</option>
          </select>
        </span>
      </div>
    </div>

    <div class="status" id="status">Ready.</div>
  </div>

  <audio id="musicAudio" loop preload="auto">
    <source src="/assets/yoga_30min.mp3" type="audio/mpeg" />
  </audio>
  <audio id="ringAudio" preload="auto">
    <source src="/assets/ringtone.mp3" type="audio/mpeg" />
  </audio>

  <script>
    const ITEM_H = 42;

    const wheels = {{
      hours: {{ el: document.getElementById("hoursWheel"), max: 12, unit: "hours", value: 0 }},
      minutes: {{ el: document.getElementById("minutesWheel"), max: 59, unit: "min", value: 15 }},
      seconds: {{ el: document.getElementById("secondsWheel"), max: 59, unit: "sec", value: 0 }}
    }};

    const finishModeEl = document.getElementById("finishMode");
    const timerEl = document.getElementById("timer");
    const statusEl = document.getElementById("status");
    const startPauseBtn = document.getElementById("startPauseBtn");
    const cancelBtn = document.getElementById("cancelBtn");
    const musicToggle = document.getElementById("musicToggle");
    const musicAudio = document.getElementById("musicAudio");
    const ringAudio = document.getElementById("ringAudio");

    let countdown = null;
    let remainingSeconds = 15 * 60;
    let running = false;

    function syncPrimaryButton() {{
      startPauseBtn.textContent = running ? "Pause" : "Start";
      startPauseBtn.classList.toggle("running", running);
    }}

    function setStatus(text, active = false) {{
      statusEl.textContent = text;
      statusEl.classList.toggle("active", active);
    }}

    function formatTime(totalSeconds) {{
      const hours = Math.floor(totalSeconds / 3600);
      const mins = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, "0");
      const secs = (totalSeconds % 60).toString().padStart(2, "0");
      if (hours > 0) return `${{hours.toString().padStart(2, "0")}}:${{mins}}:${{secs}}`;
      return `${{mins}}:${{secs}}`;
    }}

    function updateTimerDisplay() {{
      timerEl.textContent = formatTime(remainingSeconds);
    }}

    function selectedFinishMode() {{
      return finishModeEl.value || "stop";
    }}

    function stopMusic() {{
      musicAudio.pause();
      musicAudio.currentTime = 0;
    }}

    function stopRingtone() {{
      ringAudio.pause();
      ringAudio.currentTime = 0;
    }}

    function startMusicIfEnabled() {{
      if (musicToggle.checked) {{
        musicAudio.currentTime = 0;
        musicAudio.play().catch(() => {{
          setStatus("Timer started. Audio blocked until user interaction is allowed.");
        }});
      }}
    }}

    function setWheelLocked(locked) {{
      Object.values(wheels).forEach((w) => {{
        w.el.classList.toggle("locked", locked);
      }});
    }}

    function highlightWheelSelection(wheelName) {{
      const wheel = wheels[wheelName];
      const items = wheel.el.querySelectorAll(".wheel-item");
      items.forEach((item, idx) => {{
        item.classList.toggle("selected", idx === wheel.value);
      }});
    }}

    function setWheelValue(wheelName, value, fromScroll = false) {{
      const wheel = wheels[wheelName];
      const clamped = Math.max(0, Math.min(wheel.max, value));
      wheel.value = clamped;
      highlightWheelSelection(wheelName);
      if (!fromScroll) wheel.el.scrollTo({{ top: clamped * ITEM_H, behavior: "smooth" }});
      if (!running) {{
        remainingSeconds = getSelectedDurationSeconds();
        updateTimerDisplay();
      }}
    }}

    function getSelectedDurationSeconds() {{
      return (wheels.hours.value * 3600) + (wheels.minutes.value * 60) + wheels.seconds.value;
    }}

    function buildWheel(wheelName) {{
      const wheel = wheels[wheelName];
      wheel.el.innerHTML = "";
      wheel.justDraggedUntil = 0;
      const frag = document.createDocumentFragment();
      for (let i = 0; i <= wheel.max; i += 1) {{
        const item = document.createElement("div");
        item.className = "wheel-item";
        item.innerHTML = `<span class="num">${{i}}</span><span class="unit">${{wheel.unit}}</span>`;
        item.addEventListener("click", () => {{
          if (Date.now() < wheel.justDraggedUntil) return;
          setWheelValue(wheelName, i);
        }});
        frag.appendChild(item);
      }}
      wheel.el.appendChild(frag);

      let scrollTimer = null;
      wheel.el.addEventListener("scroll", () => {{
        if (running) return;
        const idx = Math.round(wheel.el.scrollTop / ITEM_H);
        setWheelValue(wheelName, idx, true);
        window.clearTimeout(scrollTimer);
        scrollTimer = window.setTimeout(() => {{
          wheel.el.scrollTo({{ top: wheels[wheelName].value * ITEM_H, behavior: "smooth" }});
        }}, 80);
      }});

      wheel.el.addEventListener("mousedown", (ev) => {{
        if (running || ev.button !== 0) return;
        ev.preventDefault();
        const startY = ev.clientY;
        const startTop = wheel.el.scrollTop;
        let moved = false;
        wheel.el.classList.add("dragging");
        document.body.classList.add("noselect");

        const onMove = (moveEv) => {{
          const dy = moveEv.clientY - startY;
          if (Math.abs(dy) > 2) moved = true;
          wheel.el.scrollTop = startTop - dy;
        }};

        const onUp = () => {{
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
          wheel.el.classList.remove("dragging");
          document.body.classList.remove("noselect");
          if (moved) {{
            wheel.justDraggedUntil = Date.now() + 180;
            wheel.el.scrollTo({{ top: wheels[wheelName].value * ITEM_H, behavior: "smooth" }});
          }}
        }};

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      }});

      setWheelValue(wheelName, wheel.value);
      wheel.el.scrollTop = wheel.value * ITEM_H;
    }}

    function finishSession() {{
      running = false;
      clearInterval(countdown);
      countdown = null;
      stopMusic();
      setWheelLocked(false);
      syncPrimaryButton();
      if (selectedFinishMode() === "ring") {{
        ringAudio.currentTime = 0;
        ringAudio.play().catch(() => null);
        setStatus("Session complete. Ringtone played.");
      }} else {{
        setStatus("Session complete.");
      }}
    }}

    function startTimer() {{
      if (running) return;
      if (remainingSeconds <= 0) remainingSeconds = getSelectedDurationSeconds();
      if (remainingSeconds <= 0) {{
        setStatus("Pick a duration greater than 0 seconds.");
        return;
      }}
      stopRingtone();
      running = true;
      setWheelLocked(true);
      syncPrimaryButton();
      setStatus("Meditation in progress...", true);
      startMusicIfEnabled();
      countdown = setInterval(() => {{
        remainingSeconds -= 1;
        if (remainingSeconds <= 0) {{
          remainingSeconds = 0;
          updateTimerDisplay();
          finishSession();
          return;
        }}
        updateTimerDisplay();
      }}, 1000);
    }}

    function pauseTimer() {{
      if (!running) return;
      running = false;
      clearInterval(countdown);
      countdown = null;
      stopMusic();
      setWheelLocked(false);
      syncPrimaryButton();
      setStatus("Paused.");
    }}

    function cancelTimer() {{
      running = false;
      clearInterval(countdown);
      countdown = null;
      stopMusic();
      stopRingtone();
      setWheelLocked(false);
      syncPrimaryButton();
      remainingSeconds = getSelectedDurationSeconds();
      updateTimerDisplay();
      setStatus("Ready.");
    }}

    Object.keys(wheels).forEach(buildWheel);
    remainingSeconds = getSelectedDurationSeconds();
    updateTimerDisplay();
    syncPrimaryButton();

    musicToggle.addEventListener("change", () => {{
      if (!running) return;
      if (musicToggle.checked) {{
        startMusicIfEnabled();
        setStatus("Meditation in progress...", true);
      }} else {{
        stopMusic();
        setStatus("Meditation in progress (music off).", true);
      }}
    }});

    startPauseBtn.addEventListener("click", () => {{
      if (running) {{
        pauseTimer();
      }} else {{
        startTimer();
      }}
    }});
    cancelBtn.addEventListener("click", cancelTimer);
  </script>
</body>
</html>
    """


tool.add_widget_route(widget_html)

if __name__ == "__main__":
    tool.run()
