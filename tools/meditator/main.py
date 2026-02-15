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
      --bg: #f4f0e8;
      --panel: #f9f4ec;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #e7dcca;
      --wheel-bg: #12151c;
      --wheel-line: #2a2f3d;
      --wheel-text: #e5e7eb;
      --wheel-dim: #7b8290;
      --item-h: 40px;
      --wheel-h: 184px;
      --wheel-pad: 72px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      color: var(--ink);
      background: var(--bg);
      padding: 8px;
    }}
    .card {{
      width: 100%;
      margin: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 24px rgba(80, 60, 20, 0.06);
      padding: 14px;
    }}
    .picker-shell {{
      position: relative;
      background: linear-gradient(180deg, #1a1d26 0%, #12151c 100%);
      border: 1px solid #2a2f3d;
      border-radius: 14px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07);
      overflow: hidden;
      margin-bottom: 12px;
    }}
    .picker-center {{
      position: absolute;
      left: 8px;
      right: 8px;
      top: 50%;
      height: var(--item-h);
      transform: translateY(-50%);
      border-radius: 10px;
      background: linear-gradient(90deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
      border: 1px solid rgba(255, 255, 255, 0.09);
      pointer-events: none;
      z-index: 2;
    }}
    .picker-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      padding: 6px 8px;
      position: relative;
      z-index: 1;
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
    .wheel::-webkit-scrollbar {{
      display: none;
    }}
    .wheel-item {{
      height: var(--item-h);
      scroll-snap-align: center;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      color: var(--wheel-dim);
      font-weight: 600;
      transition: color 120ms ease, transform 120ms ease;
      user-select: none;
    }}
    .wheel-item .num {{
      min-width: 16px;
      text-align: right;
    }}
    .wheel-item .unit {{
      font-size: 0.84rem;
    }}
    .wheel-item.selected {{
      color: var(--wheel-text);
      transform: scale(1.03);
      font-weight: 700;
    }}
    .row {{
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .live-time {{
      margin-left: auto;
      background: #10141b;
      border: 1px solid #2a2f3d;
      color: #e5e7eb;
      border-radius: 999px;
      padding: 6px 10px;
      font-family: "Courier New", monospace;
      font-size: 0.9rem;
    }}
    button {{
      border: none;
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 0.95rem;
      cursor: pointer;
      background: linear-gradient(180deg, #fbbf24, #f59e0b);
      color: #422006;
      font-weight: 700;
    }}
    button.secondary {{
      background: #fff;
      border: 1px solid var(--line);
      color: var(--ink);
      font-weight: 600;
    }}
    .options {{
      border-top: 1px dashed var(--line);
      padding-top: 10px;
      margin-top: 2px;
    }}
    .options label {{
      font-weight: 600;
    }}
    .menu-row {{
      margin-top: 4px;
      background: linear-gradient(90deg, #14151a 0%, #1d2028 100%);
      border-radius: 10px;
      border: 1px solid #242834;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #f3f4f6;
      gap: 10px;
    }}
    .menu-left {{
      font-size: 0.93rem;
      color: #e5e7eb;
    }}
    .menu-right {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .menu-right select {{
      border: none;
      background: transparent;
      color: #f3f4f6;
      padding: 0;
      font-size: 0.92rem;
      max-width: 140px;
      text-align: right;
      appearance: none;
      -webkit-appearance: none;
    }}
    .chev {{
      color: #9ca3af;
      font-weight: 700;
    }}
    .status {{
      min-height: 1.2rem;
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .locked {{
      pointer-events: none;
      opacity: 0.85;
    }}
    .noselect {{
      user-select: none;
    }}
    @media (max-width: 520px) {{
      .row {{ gap: 8px; }}
      button {{ flex: 1; }}
      .picker-grid {{ gap: 6px; }}
      .wheel-item .unit {{ font-size: 0.8rem; }}
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

    <div class="row">
      <button id="startBtn">Start</button>
      <button id="pauseBtn" class="secondary">Pause</button>
      <button id="resetBtn" class="secondary">Reset</button>
      <div class="live-time" id="timer">15:00</div>
    </div>

    <div class="options">
      <div class="row">
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
          <span class="chev">›</span>
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
    const ITEM_H = 40;

    const wheels = {{
      hours: {{ el: document.getElementById("hoursWheel"), max: 12, unit: "hours", value: 0 }},
      minutes: {{ el: document.getElementById("minutesWheel"), max: 59, unit: "min", value: 15 }},
      seconds: {{ el: document.getElementById("secondsWheel"), max: 59, unit: "sec", value: 0 }}
    }};

    const finishModeEl = document.getElementById("finishMode");
    const timerEl = document.getElementById("timer");
    const statusEl = document.getElementById("status");
    const startBtn = document.getElementById("startBtn");
    const pauseBtn = document.getElementById("pauseBtn");
    const resetBtn = document.getElementById("resetBtn");
    const musicToggle = document.getElementById("musicToggle");
    const musicAudio = document.getElementById("musicAudio");
    const ringAudio = document.getElementById("ringAudio");

    let countdown = null;
    let remainingSeconds = 15 * 60;
    let running = false;

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
          statusEl.textContent = "Timer started. Audio blocked until user interaction is allowed.";
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
      if (selectedFinishMode() === "ring") {{
        ringAudio.currentTime = 0;
        ringAudio.play().catch(() => null);
        statusEl.textContent = "Session complete. Ringtone played.";
      }} else {{
        statusEl.textContent = "Session complete.";
      }}
    }}

    function startTimer() {{
      if (running) return;
      if (remainingSeconds <= 0) remainingSeconds = getSelectedDurationSeconds();
      if (remainingSeconds <= 0) {{
        statusEl.textContent = "Pick a duration greater than 0 seconds.";
        return;
      }}
      stopRingtone();
      running = true;
      setWheelLocked(true);
      statusEl.textContent = "Meditation in progress...";
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
      statusEl.textContent = "Paused.";
    }}

    function resetTimer() {{
      running = false;
      clearInterval(countdown);
      countdown = null;
      stopMusic();
      stopRingtone();
      setWheelLocked(false);
      remainingSeconds = getSelectedDurationSeconds();
      updateTimerDisplay();
      statusEl.textContent = "Reset.";
    }}

    Object.keys(wheels).forEach(buildWheel);
    remainingSeconds = getSelectedDurationSeconds();
    updateTimerDisplay();

    musicToggle.addEventListener("change", () => {{
      if (!running) return;
      if (musicToggle.checked) {{
        startMusicIfEnabled();
        statusEl.textContent = "Meditation in progress...";
      }} else {{
        stopMusic();
        statusEl.textContent = "Meditation in progress (music off).";
      }}
    }});

    startBtn.addEventListener("click", startTimer);
    pauseBtn.addEventListener("click", pauseTimer);
    resetBtn.addEventListener("click", resetTimer);
  </script>
</body>
</html>
    """


tool.add_widget_route(widget_html)

if __name__ == "__main__":
    tool.run()
