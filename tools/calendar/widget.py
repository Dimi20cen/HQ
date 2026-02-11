def widget_html(cal_url: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <style>
        :root {{
          --bg: #f3f6f6;
          --panel: #ffffff;
          --ink: #102225;
          --muted: #5d6d71;
          --line: #d3dde0;
          --accent: #0b8c7b;
          --accent-2: #0a6f88;
          --danger: #c73b4a;
          --shadow: 0 10px 24px rgba(16, 34, 37, 0.09);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 10px;
          background:
            radial-gradient(circle at 8% 0%, rgba(11, 140, 123, 0.12), transparent 36%),
            radial-gradient(circle at 100% 100%, rgba(10, 111, 136, 0.14), transparent 36%),
            var(--bg);
          color: var(--ink);
          font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
        }}
        .card {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 9px;
          box-shadow: var(--shadow);
        }}
        .title {{
          margin: 0 0 2px;
          font-size: 13px;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          color: var(--accent-2);
        }}
        .sub {{
          margin: 0 0 8px;
          font-size: 12px;
          color: var(--muted);
        }}
        .row {{ display: flex; gap: 6px; margin-bottom: 6px; align-items: center; flex-wrap: wrap; }}
        button {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff;
          color: var(--ink);
          padding: 5px 9px;
          cursor: pointer;
          font: inherit;
          font-size: 12px;
          transition: transform .08s ease, box-shadow .12s ease, background .12s ease;
        }}
        button:hover {{ transform: translateY(-1px); box-shadow: 0 4px 10px rgba(16, 34, 37, 0.09); }}
        button.primary {{
          background: linear-gradient(135deg, var(--accent), var(--accent-2));
          border-color: transparent;
          color: #fff;
        }}
        button.warn {{ background: var(--danger); border-color: transparent; color: #fff; }}
        .status {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 6px 8px;
          font-size: 12px;
          color: var(--muted);
          background: #f8fbfb;
        }}
        .status.error {{ border-color: #efc7cd; background: #fff4f6; color: #8b2130; }}
        .status.ok {{ border-color: #b8dfd8; background: #effbf8; color: #0f6257; }}
        .events {{ margin-top: 6px; max-height: 190px; overflow: auto; border: 1px solid var(--line); border-radius: 10px; background: #fbfdfd; }}
        .event {{ padding: 7px; border-bottom: 1px solid #eaf0f2; }}
        .event:last-child {{ border-bottom: 0; }}
        .event-title {{ font-weight: 600; font-size: 13px; line-height: 1.2; }}
        .time {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
        .event-actions {{ margin-top: 5px; display: flex; gap: 6px; }}
        .form-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }}
        .field {{ display: flex; flex-direction: column; gap: 4px; }}
        .field.full {{ grid-column: 1 / span 2; }}
        label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
        input, textarea {{
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 6px 8px;
          font: inherit;
          font-size: 13px;
          background: #fff;
        }}
        input:focus, textarea:focus {{
          outline: none;
          border-color: #7ec8bc;
          box-shadow: 0 0 0 3px rgba(11, 140, 123, 0.14);
        }}
        textarea {{ min-height: 56px; resize: vertical; }}
        .toolbar {{ display: flex; gap: 6px; margin-top: 6px; align-items: center; flex-wrap: wrap; }}
        .muted {{ color: var(--muted); font-size: 12px; }}
        details {{ margin-top: 6px; }}
        summary {{ font-size: 12px; color: var(--muted); cursor: pointer; user-select: none; }}
        iframe {{ width: 100%; height: 220px; border: 0; border-radius: 10px; background: #fff; border: 1px solid var(--line); margin-top: 8px; }}
        .hidden {{ display: none !important; }}
        @media (max-width: 520px) {{
          .form-grid {{ grid-template-columns: 1fr; }}
          .field.full {{ grid-column: auto; }}
          iframe {{ height: 180px; }}
        }}
      </style>
    </head>
    <body>
      <div class=\"card\">
        <h3 class=\"title\">Calendar Control</h3>
        <p class=\"sub\">Google Calendar quick actions</p>
        <div class=\"row\">
          <button id=\"connect\" class=\"primary\">Connect Google</button>
          <button id=\"refresh\">Refresh</button>
          <button id=\"disconnect\">Disconnect</button>
        </div>
        <div id=\"status\" class=\"status\">Checking auth...</div>
        <div class=\"form-grid\">
          <div class=\"field full\">
            <label for=\"summary\">Summary</label>
            <input id=\"summary\" placeholder=\"Team sync\" />
          </div>
          <div class=\"field\">
            <label for=\"start\">Start</label>
            <input id=\"start\" type=\"datetime-local\" />
          </div>
          <div class=\"field\">
            <label for=\"end\">End</label>
            <input id=\"end\" type=\"datetime-local\" />
          </div>
          <div class=\"field full\">
            <label for=\"description\">Description</label>
            <textarea id=\"description\" placeholder=\"Optional notes\"></textarea>
          </div>
        </div>
        <div class=\"toolbar\">
          <button id=\"create\" class=\"primary\">Create</button>
          <button id=\"update\">Update Selected</button>
          <button id=\"clear\">Clear</button>
          <span id=\"selected\" class=\"muted\">No event selected.</span>
        </div>
        <div id=\"events\" class=\"events\"></div>
        <details>
          <summary>Show embedded calendar preview</summary>
          <iframe src=\"{cal_url}\" title=\"Calendar Embed\"></iframe>
        </details>
      </div>

      <script>
        let selectedEventId = null;
        const connectBtn = document.getElementById('connect');
        const disconnectBtn = document.getElementById('disconnect');
        const formGrid = document.querySelector('.form-grid');
        const toolbar = document.querySelector('.toolbar');
        const eventsRoot = document.getElementById('events');

        function setAuthUi(connected) {{
          connectBtn.classList.toggle('hidden', connected);
          disconnectBtn.classList.toggle('hidden', !connected);
          formGrid.classList.toggle('hidden', !connected);
          toolbar.classList.toggle('hidden', !connected);
          eventsRoot.classList.toggle('hidden', !connected);
        }}

        function setStatus(message, type) {{
          const el = document.getElementById('status');
          el.textContent = message;
          el.className = 'status';
          if (type) el.classList.add(type);
        }}

        async function jsonFetch(url, options) {{
          const res = await fetch(url, options || {{}});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
          return data;
        }}

        function toIsoFromLocalInput(value) {{
          if (!value) return null;
          const d = new Date(value);
          if (Number.isNaN(d.getTime())) return null;
          return d.toISOString();
        }}

        function toLocalInputValue(iso) {{
          if (!iso) return '';
          const d = new Date(iso);
          if (Number.isNaN(d.getTime())) return '';
          d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
          return d.toISOString().slice(0, 16);
        }}

        function getFormPayload() {{
          const summary = document.getElementById('summary').value.trim();
          const description = document.getElementById('description').value.trim();
          const startLocal = document.getElementById('start').value;
          const endLocal = document.getElementById('end').value;
          const startIso = toIsoFromLocalInput(startLocal);
          const endIso = toIsoFromLocalInput(endLocal);

          if (!summary) throw new Error('Summary is required.');
          if (!startIso || !endIso) throw new Error('Start and end are required.');
          if (new Date(endIso) <= new Date(startIso)) throw new Error('End must be after start.');

          return {{
            summary,
            description,
            start: {{ dateTime: startIso }},
            end: {{ dateTime: endIso }},
          }};
        }}

        function clearForm() {{
          document.getElementById('summary').value = '';
          document.getElementById('description').value = '';
          document.getElementById('start').value = '';
          document.getElementById('end').value = '';
          selectedEventId = null;
          document.getElementById('selected').textContent = 'No event selected.';
        }}

        function populateForm(event) {{
          document.getElementById('summary').value = event.summary || '';
          document.getElementById('description').value = event.description || '';
          document.getElementById('start').value = toLocalInputValue(event.start && event.start.dateTime);
          document.getElementById('end').value = toLocalInputValue(event.end && event.end.dateTime);
          selectedEventId = event.id || null;
          document.getElementById('selected').textContent = selectedEventId
            ? `Selected: ${{event.summary || '(untitled)'}}`
            : 'No event selected.';
        }}

        function renderEvents(items) {{
          const root = document.getElementById('events');
          if (!items.length) {{
            root.innerHTML = '<div class="muted">No upcoming events.</div>';
            return;
          }}

          root.innerHTML = items.map((event) => {{
            const when = (event.start && (event.start.dateTime || event.start.date)) || '(no start)';
            const title = event.summary || '(untitled)';
            const id = event.id || '';
            return `
              <div class="event">
                <div class="event-title">${{title}}</div>
                <div class="time">${{when}}</div>
                <div class="event-actions">
                  <button data-action="select" data-id="${{id}}">Edit</button>
                  <button data-action="delete" data-id="${{id}}" class="warn">Delete</button>
                </div>
              </div>
            `;
          }}).join('');

          root.querySelectorAll('button[data-action="select"]').forEach((btn) => {{
            btn.addEventListener('click', () => {{
              const id = btn.getAttribute('data-id');
              const match = items.find((e) => e.id === id);
              if (match) populateForm(match);
            }});
          }});

          root.querySelectorAll('button[data-action="delete"]').forEach((btn) => {{
            btn.addEventListener('click', async () => {{
              const id = btn.getAttribute('data-id');
              if (!id) return;
              if (!confirm('Delete this event?')) return;
              try {{
                await jsonFetch(`/events/${{encodeURIComponent(id)}}`, {{ method: 'DELETE' }});
                if (selectedEventId === id) clearForm();
                await loadStatusAndEvents();
              }} catch (err) {{
                setStatus(`Delete failed: ${{err.message}}`, 'error');
              }}
            }});
          }});
        }}

        async function loadStatusAndEvents() {{
          try {{
            const status = await jsonFetch('/auth/status');
            if (!status.connected) {{
              setAuthUi(false);
              setStatus('Not connected. Use Connect Google to enable API access.', null);
              renderEvents([]);
              return;
            }}
            setAuthUi(true);
            setStatus('Connected. Loading events...', 'ok');
            const result = await jsonFetch('/events?max_results=15');
            setStatus(`Connected. Showing ${{result.count}} upcoming events.`, 'ok');
            renderEvents(result.events || []);
          }} catch (err) {{
            setStatus(`Error: ${{err.message}}`, 'error');
            renderEvents([]);
          }}
        }}

        document.getElementById('connect').addEventListener('click', async () => {{
          setStatus('Preparing OAuth...', null);
          try {{
            const result = await jsonFetch('/auth/start');
            if (window.top && window.top !== window) {{
              window.top.location.href = result.auth_url;
            }} else {{
              window.location.href = result.auth_url;
            }}
          }} catch (err) {{
            setStatus(`Connect failed: ${{err.message}}`, 'error');
          }}
        }});

        document.getElementById('refresh').addEventListener('click', loadStatusAndEvents);

        document.getElementById('create').addEventListener('click', async () => {{
          try {{
            const payload = getFormPayload();
            await jsonFetch('/events', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify(payload),
            }});
            clearForm();
            await loadStatusAndEvents();
          }} catch (err) {{
            setStatus(`Create failed: ${{err.message}}`, 'error');
          }}
        }});

        document.getElementById('update').addEventListener('click', async () => {{
          if (!selectedEventId) {{
            setStatus('Select an event to update.', null);
            return;
          }}
          try {{
            const payload = getFormPayload();
            await jsonFetch(`/events/${{encodeURIComponent(selectedEventId)}}`, {{
              method: 'PATCH',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify(payload),
            }});
            await loadStatusAndEvents();
          }} catch (err) {{
            setStatus(`Update failed: ${{err.message}}`, 'error');
          }}
        }});

        document.getElementById('clear').addEventListener('click', clearForm);

        document.getElementById('disconnect').addEventListener('click', async () => {{
          try {{
            await jsonFetch('/auth/disconnect', {{ method: 'POST' }});
            clearForm();
            setAuthUi(false);
            await loadStatusAndEvents();
          }} catch (err) {{
            setStatus(`Disconnect failed: ${{err.message}}`, 'error');
          }}
        }});

        loadStatusAndEvents();
      </script>
    </body>
    </html>
    """


