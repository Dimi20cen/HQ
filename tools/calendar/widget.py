def widget_html(cal_url: str) -> str:
    _ = cal_url
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <style>
        :root {
          --ink: #0b2545;
          --muted: #5d728a;
          --line: #c6d8ea;
          --bg: #f3f8ff;
          --soft: #ffffff;
          --accent: #1d6fd8;
          --accent-strong: #1557ad;
          --danger: #b4233e;
          --ok: #1f8a53;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
          color: var(--ink);
          background: transparent;
        }
        .card {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--bg);
          padding: 6px;
        }
        .top {
          display: flex;
          gap: 4px;
          align-items: center;
          flex-wrap: wrap;
        }
        .tz {
          margin-left: auto;
          font-size: 11px;
          color: var(--muted);
        }
        button {
          border: 1px solid var(--line);
          border-radius: 7px;
          background: #fff;
          color: var(--ink);
          padding: 4px 8px;
          cursor: pointer;
          font: inherit;
          font-size: 11px;
        }
        button.primary {
          background: var(--accent);
          color: #fff;
          border-color: var(--accent);
        }
        button.primary:hover { background: var(--accent-strong); border-color: var(--accent-strong); }
        button.warn {
          background: #fff;
          color: var(--danger);
          border-color: #f0c2cc;
        }
        .icon-btn {
          width: 30px;
          padding: 4px 0;
          text-align: center;
          font-size: 14px;
          line-height: 1;
        }
        .feedback {
          margin-top: 4px;
          min-height: 14px;
          font-size: 11px;
          color: var(--muted);
        }
        .feedback.ok { color: var(--ok); }
        .feedback.error { color: #8b2130; }

        .layout {
          margin-top: 6px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }
        .form-top {
          margin-top: 6px;
        }
        .panel {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #ffffff;
          padding: 4px;
        }

        .month-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 2px;
        }
        .month-name {
          margin: 0;
          font-size: 14px;
          line-height: 1;
          font-weight: 600;
        }
        .month-nav {
          display: flex;
          gap: 4px;
        }
        .month-nav button {
          width: 24px;
          height: 24px;
          border-radius: 999px;
          padding: 0;
          font-size: 16px;
          line-height: 1;
          border: 0;
          background: transparent;
          color: var(--muted);
        }
        .month-nav button:hover { background: #e7f1ff; color: var(--accent-strong); }

        .weekday-row,
        .day-grid {
          display: grid;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          gap: 2px;
        }
        .weekday {
          text-align: center;
          color: var(--muted);
          font-size: 9px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .day {
          min-height: 26px;
          border: 1px solid transparent;
          border-radius: 5px;
          background: transparent;
          padding: 2px 1px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: space-between;
          cursor: pointer;
        }
        .day:hover { background: #eef5ff; }
        .day.outside {
          color: #b0b0b0;
        }
        .day.today {
          border-color: #9fbce3;
          background: #edf4ff;
        }
        .day.active {
          border-color: var(--accent);
          background: #e1eeff;
        }
        .day-num {
          font-size: 10px;
          font-weight: 600;
        }
        .dots {
          display: flex;
          gap: 2px;
          min-height: 4px;
        }
        .dot {
          width: 3px;
          height: 3px;
          border-radius: 50%;
          background: var(--accent);
        }

        .section {
          margin-top: 6px;
          padding-top: 6px;
          border-top: 1px solid #dbe8f5;
        }
        .section-title {
          margin: 0 0 4px;
          font-size: 11px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.03em;
          font-weight: 700;
        }

        .form {
          border: 1px solid #dbe8f5;
          border-radius: 8px;
          padding: 6px;
          background: #fff;
        }
        .field { display: flex; flex-direction: column; gap: 3px; margin-bottom: 5px; }
        .field:last-child { margin-bottom: 0; }
        label {
          font-size: 10px;
          color: var(--muted);
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }
        .range-fields {
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          gap: 6px;
          align-items: end;
        }
        .to { font-size: 11px; color: var(--muted); padding-bottom: 7px; text-transform: uppercase; }
        input, textarea {
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 5px 7px;
          font: inherit;
          font-size: 12px;
          background: #fff;
        }
        textarea { min-height: 48px; resize: vertical; }
        .actions { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
        .hint { color: var(--muted); font-size: 11px; }

        .event {
          border: 1px solid #dbe8f5;
          border-radius: 8px;
          background: #fafdff;
          padding: 5px;
          margin-bottom: 5px;
        }
        .event:last-child { margin-bottom: 0; }
        .event-title { font-size: 12px; font-weight: 700; }
        .event-time { font-size: 10px; color: var(--muted); margin-top: 2px; }
        .event-actions { margin-top: 4px; display: flex; gap: 5px; }

        .hidden { display: none !important; }

        @media (max-width: 920px) {
          .layout { grid-template-columns: 1fr; }
        }
        @media (max-width: 560px) {
          .range-fields { grid-template-columns: 1fr; }
          .to { padding-bottom: 0; }
        }
      </style>
    </head>
    <body>
      <div class=\"card\">
        <div class=\"top\">
          <button id=\"create-toggle\" class=\"primary hidden\">+ Create</button>
          <button id=\"connect\" class=\"primary\">Connect Google</button>
          <button id=\"refresh\" type=\"button\" class=\"hidden icon-btn\" aria-label=\"Refresh\" title=\"Refresh\">&#8635;</button>
          <button id=\"disconnect\" type=\"button\" class=\"hidden warn\">Disconnect</button>
          <div id=\"timezone\" class=\"tz\">Timezone: -</div>
        </div>

        <div id=\"feedback\" class=\"feedback\"></div>

        <div id=\"form-top\" class=\"form-top hidden\">
          <div id=\"form\" class=\"form\">
            <h4 id=\"form-title\" class=\"section-title\">Create Entry</h4>

            <div class=\"field\">
              <label for=\"title\">Title</label>
              <input id=\"title\" placeholder=\"Meeting\" />
            </div>

            <div class=\"range-fields\">
              <div class=\"field\">
                <label for=\"start\">Start Date</label>
                <input id=\"start\" placeholder=\"YYYY-MM-DD HH:MM\" />
              </div>
              <div class=\"to\">to</div>
              <div class=\"field\">
                <label for=\"end\">End Date</label>
                <input id=\"end\" placeholder=\"YYYY-MM-DD HH:MM\" />
              </div>
            </div>

            <div class=\"field\">
              <label for=\"description\">Description (optional)</label>
              <textarea id=\"description\" placeholder=\"Optional notes\"></textarea>
            </div>

            <div class=\"actions\">
              <button id=\"save\" class=\"primary\">Create</button>
              <button id=\"clear\" type=\"button\">Clear</button>
              <button id=\"close-form\" type=\"button\">Close</button>
              <span id=\"selected\" class=\"hint\">No event selected.</span>
            </div>
          </div>
        </div>

        <div id=\"layout\" class=\"layout hidden\">
          <section class=\"panel\">
            <div class=\"month-head\">
              <h4 id=\"month-name\" class=\"month-name\">-</h4>
              <div class=\"month-nav\">
                <button id=\"prev-month\" type=\"button\" aria-label=\"Previous month\">&#8249;</button>
                <button id=\"next-month\" type=\"button\" aria-label=\"Next month\">&#8250;</button>
              </div>
            </div>

            <div class=\"weekday-row\">
              <div class=\"weekday\">S</div><div class=\"weekday\">M</div><div class=\"weekday\">T</div>
              <div class=\"weekday\">W</div><div class=\"weekday\">T</div><div class=\"weekday\">F</div><div class=\"weekday\">S</div>
            </div>
            <div id=\"calendar-root\" class=\"day-grid\"></div>
          </section>

          <section class=\"panel\">
            <div class=\"section\" style=\"margin-top:0;padding-top:0;border-top:0;\">
              <h4 id=\"entries-title\" class=\"section-title\">Entries</h4>
              <div id=\"entries\"></div>
            </div>
          </section>
        </div>
      </div>

      <script>
        let selectedEventId = null;
        let selectedDay = new Date();
        let monthAnchor = new Date(selectedDay.getFullYear(), selectedDay.getMonth(), 1);
        let monthEvents = [];
        let isFormOpen = false;
        const eventById = new Map();

        const timezoneEl = document.getElementById('timezone');
        const feedbackEl = document.getElementById('feedback');
        const connectBtn = document.getElementById('connect');
        const createToggleBtn = document.getElementById('create-toggle');
        const refreshBtn = document.getElementById('refresh');
        const disconnectBtn = document.getElementById('disconnect');
        const layoutEl = document.getElementById('layout');
        const formTopEl = document.getElementById('form-top');
        const monthNameEl = document.getElementById('month-name');
        const calendarRoot = document.getElementById('calendar-root');
        const entriesTitleEl = document.getElementById('entries-title');
        const entriesEl = document.getElementById('entries');
        const formEl = document.getElementById('form');
        const formTitleEl = document.getElementById('form-title');
        const saveBtn = document.getElementById('save');

        let feedbackTimer = null;

        function currentTimeZoneLabel() {
          try {
            const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local';
            const parts = new Intl.DateTimeFormat('en-US', {
              timeZone: zone,
              timeZoneName: 'shortOffset',
            }).formatToParts(new Date());
            const offset = parts.find((part) => part.type === 'timeZoneName')?.value || 'GMT';
            return `${zone} (${offset})`;
          } catch (e) {
            return 'Local (GMT)';
          }
        }

        function setFeedback(message, type, timeoutMs) {
          feedbackEl.textContent = message || '';
          feedbackEl.className = 'feedback';
          if (type) feedbackEl.classList.add(type);
          if (feedbackTimer) {
            clearTimeout(feedbackTimer);
            feedbackTimer = null;
          }
          if (timeoutMs) {
            feedbackTimer = setTimeout(() => {
              feedbackEl.textContent = '';
              feedbackEl.className = 'feedback';
            }, timeoutMs);
          }
        }

        function setAuthUi(connected) {
          connectBtn.classList.toggle('hidden', connected);
          createToggleBtn.classList.toggle('hidden', !connected);
          refreshBtn.classList.toggle('hidden', !connected);
          disconnectBtn.classList.toggle('hidden', !connected);
          layoutEl.classList.toggle('hidden', !connected);
          formTopEl.classList.toggle('hidden', !connected || !isFormOpen);
        }

        function setFormOpen(open) {
          isFormOpen = open;
          formTopEl.classList.toggle('hidden', !open);
          createToggleBtn.textContent = open ? 'Close' : '+ Create';
          if (!open) {
            selectedEventId = null;
            formTitleEl.textContent = 'Create Entry';
            saveBtn.textContent = 'Create';
            document.getElementById('selected').textContent = 'No event selected.';
          }
        }

        async function jsonFetch(url, options) {
          const res = await fetch(url, options || {});
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
          return data;
        }

        function localDayKey(d) {
          return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        }

        function formatDateTime(d) {
          return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        }

        function parseDateTime(value) {
          const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2})$/.exec((value || '').trim());
          if (!m) return null;
          const y = Number(m[1]);
          const mo = Number(m[2]);
          const da = Number(m[3]);
          const hh = Number(m[4]);
          const mm = Number(m[5]);
          if (hh > 23 || mm > 59) return null;
          const d = new Date(y, mo - 1, da, hh, mm, 0, 0);
          if (d.getFullYear() !== y || d.getMonth() !== mo - 1 || d.getDate() !== da || d.getHours() !== hh || d.getMinutes() !== mm) return null;
          return d;
        }

        function eventRange(event) {
          const startRaw = event.start && (event.start.dateTime || event.start.date);
          if (!startRaw) return null;
          const isAllDay = !!(event.start && event.start.date);
          const start = new Date(isAllDay ? `${startRaw}T00:00:00` : startRaw);
          if (Number.isNaN(start.getTime())) return null;

          let end;
          if (event.end && (event.end.dateTime || event.end.date)) {
            const er = event.end.dateTime || event.end.date;
            end = new Date(event.end.date ? `${er}T00:00:00` : er);
          } else {
            end = new Date(start);
          }
          if (Number.isNaN(end.getTime())) end = new Date(start);
          if (isAllDay) end = new Date(end.getTime() - 1);
          if (end < start) end = new Date(start);
          return { start, end };
        }

        function eventTouchesDay(event, day) {
          const r = eventRange(event);
          if (!r) return false;
          const ds = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 0, 0, 0, 0);
          const de = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 23, 59, 59, 999);
          return r.end >= ds && r.start <= de;
        }

        function dayDots(events, day) {
          let count = 0;
          for (const event of events) {
            if (eventTouchesDay(event, day)) {
              count += 1;
              if (count >= 3) break;
            }
          }
          return count;
        }

        function resetForm() {
          const base = new Date(selectedDay.getFullYear(), selectedDay.getMonth(), selectedDay.getDate(), 9, 0, 0, 0);
          document.getElementById('title').value = '';
          document.getElementById('start').value = formatDateTime(base);
          document.getElementById('end').value = formatDateTime(new Date(base.getTime() + 60 * 60 * 1000));
          document.getElementById('description').value = '';
          selectedEventId = null;
          formTitleEl.textContent = 'Create Entry';
          saveBtn.textContent = 'Create';
          document.getElementById('selected').textContent = 'No event selected.';
        }

        function populateForm(event) {
          const r = eventRange(event);
          document.getElementById('title').value = event.summary || '';
          document.getElementById('start').value = r ? formatDateTime(r.start) : '';
          document.getElementById('end').value = r ? formatDateTime(r.end) : '';
          document.getElementById('description').value = event.description || '';
          selectedEventId = event.id || null;
          formTitleEl.textContent = 'Edit Entry';
          saveBtn.textContent = 'Update';
          document.getElementById('selected').textContent = selectedEventId ? `Selected: ${event.summary || '(untitled)'}` : 'No event selected.';
          setFormOpen(true);
        }

        function getPayload() {
          const title = document.getElementById('title').value.trim();
          const start = parseDateTime(document.getElementById('start').value);
          const end = parseDateTime(document.getElementById('end').value);
          const description = document.getElementById('description').value.trim();
          if (!title) throw new Error('Title is required.');
          if (!start || !end) throw new Error('Use YYYY-MM-DD HH:MM (24h).');
          if (end <= start) throw new Error('End must be after start.');
          return {
            summary: title,
            description,
            start: { dateTime: start.toISOString() },
            end: { dateTime: end.toISOString() },
          };
        }

        function renderEntries() {
          const selectedKey = localDayKey(selectedDay);
          entriesTitleEl.textContent = `Entries on ${selectedKey}`;
          const list = monthEvents.filter((event) => eventTouchesDay(event, selectedDay));
          if (!list.length) {
            entriesEl.innerHTML = '<div class="hint">No entries for this day.</div>';
            return;
          }

          entriesEl.innerHTML = list.map((event) => {
            const id = event.id || '';
            const title = event.summary || '(untitled)';
            const r = eventRange(event);
            const when = r ? `${formatDateTime(r.start)} to ${formatDateTime(r.end)}` : '';
            return `
              <div class=\"event\">
                <div class=\"event-title\">${title}</div>
                <div class=\"event-time\">${when}</div>
                <div class=\"event-actions\">
                  <button data-action=\"edit\" data-id=\"${id}\">Edit</button>
                  <button data-action=\"delete\" data-id=\"${id}\" class=\"warn\">Delete</button>
                </div>
              </div>
            `;
          }).join('');

          entriesEl.querySelectorAll('button[data-action="edit"]').forEach((btn) => {
            btn.addEventListener('click', () => {
              const id = btn.getAttribute('data-id');
              const event = id ? eventById.get(id) : null;
              if (event) populateForm(event);
            });
          });

          entriesEl.querySelectorAll('button[data-action="delete"]').forEach((btn) => {
            btn.addEventListener('click', async () => {
              const id = btn.getAttribute('data-id');
              if (!id) return;
              if (!confirm('Delete this entry?')) return;
              try {
                await jsonFetch(`/events/${encodeURIComponent(id)}`, { method: 'DELETE' });
                if (selectedEventId === id) resetForm();
                await loadMonthData(false);
                setFeedback('Entry deleted.', 'ok', 2000);
              } catch (err) {
                setFeedback(`Delete failed: ${err.message}`, 'error', 3500);
              }
            });
          });
        }

        function renderCalendar() {
          monthNameEl.textContent = monthAnchor.toLocaleString(undefined, { month: 'long', year: 'numeric' });

          const y = monthAnchor.getFullYear();
          const m = monthAnchor.getMonth();
          const first = new Date(y, m, 1);
          const lead = first.getDay();
          const gridStart = new Date(y, m, 1 - first.getDay());
          const todayKey = localDayKey(new Date());
          const selectedKey = localDayKey(selectedDay);

          const totalVisibleDays = lead + new Date(y, m + 1, 0).getDate();
          const trailing = (7 - (totalVisibleDays % 7)) % 7;
          const totalCells = totalVisibleDays + trailing;
          const cells = [];
          for (let i = 0; i < totalCells; i += 1) {
            const d = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
            const key = localDayKey(d);
            const outside = d.getMonth() !== m ? ' outside' : '';
            const today = key === todayKey ? ' today' : '';
            const active = key === selectedKey ? ' active' : '';
            const count = dayDots(monthEvents, d);
            const dots = new Array(count).fill('<span class="dot"></span>').join('');
            cells.push(`
              <div class=\"day${outside}${today}${active}\" data-day=\"${key}\">
                <div class=\"day-num\">${d.getDate()}</div>
                <div class=\"dots\">${dots}</div>
              </div>
            `);
          }

          calendarRoot.innerHTML = cells.join('');

          calendarRoot.querySelectorAll('.day[data-day]').forEach((cell) => {
            cell.addEventListener('click', async () => {
              const key = cell.getAttribute('data-day');
              if (!key) return;
              const d = new Date(`${key}T00:00:00`);
              if (Number.isNaN(d.getTime())) return;

              const changedMonth = d.getMonth() !== monthAnchor.getMonth() || d.getFullYear() !== monthAnchor.getFullYear();
              selectedDay = d;
              if (changedMonth) {
                monthAnchor = new Date(d.getFullYear(), d.getMonth(), 1);
                await loadMonthData(false);
              } else {
                renderCalendar();
                renderEntries();
              }
            });
          });
        }

        async function loadMonthData(showLoadingFeedback) {
          const y = monthAnchor.getFullYear();
          const m = monthAnchor.getMonth();
          const start = new Date(y, m, 1, 0, 0, 0, 0);
          const endExclusive = new Date(y, m + 1, 1, 0, 0, 0, 0);

          if (showLoadingFeedback) setFeedback('Refreshing...', null);

          try {
            const res = await jsonFetch(`/events?max_results=250&time_min=${encodeURIComponent(start.toISOString())}&time_max=${encodeURIComponent(endExclusive.toISOString())}`);
            monthEvents = res.events || [];
            eventById.clear();
            monthEvents.forEach((e) => { if (e && e.id) eventById.set(e.id, e); });

            renderCalendar();
            renderEntries();

            if (showLoadingFeedback) setFeedback('Calendar refreshed.', 'ok', 2000);
          } catch (err) {
            if (showLoadingFeedback) setFeedback(`Refresh failed: ${err.message}`, 'error', 3500);
            else setFeedback(`Failed loading month: ${err.message}`, 'error', 3500);
          }
        }

        async function loadAuthAndData() {
          try {
            const auth = await jsonFetch('/auth/status');
            if (!auth.connected) {
              setAuthUi(false);
              setFeedback('Not connected. Use Connect Google to enable API access.', null);
              return;
            }

            setAuthUi(true);
            setFeedback('');
            await loadMonthData(false);
          } catch (err) {
            setFeedback(`Error: ${err.message}`, 'error', 3500);
          }
        }

        createToggleBtn.addEventListener('click', () => {
          const open = !isFormOpen;
          if (open && !selectedEventId) resetForm();
          setFormOpen(open);
        });

        document.getElementById('close-form').addEventListener('click', () => setFormOpen(false));
        document.getElementById('clear').addEventListener('click', resetForm);

        saveBtn.addEventListener('click', async () => {
          try {
            const payload = getPayload();
            if (selectedEventId) {
              await jsonFetch(`/events/${encodeURIComponent(selectedEventId)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
            } else {
              await jsonFetch('/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
            }
            resetForm();
            setFormOpen(false);
            await loadMonthData(false);
            setFeedback('Entry saved.', 'ok', 2000);
          } catch (err) {
            setFeedback(`Save failed: ${err.message}`, 'error', 3500);
          }
        });

        connectBtn.addEventListener('click', async () => {
          setFeedback('Preparing OAuth...');
          try {
            const result = await jsonFetch('/auth/start');
            if (window.top && window.top !== window) window.top.location.href = result.auth_url;
            else window.location.href = result.auth_url;
          } catch (err) {
            setFeedback(`Connect failed: ${err.message}`, 'error', 3500);
          }
        });

        refreshBtn.addEventListener('click', () => loadMonthData(true));

        disconnectBtn.addEventListener('click', async () => {
          try {
            await jsonFetch('/auth/disconnect', { method: 'POST' });
            setFormOpen(false);
            await loadAuthAndData();
          } catch (err) {
            setFeedback(`Disconnect failed: ${err.message}`, 'error', 3500);
          }
        });

        document.getElementById('prev-month').addEventListener('click', async () => {
          monthAnchor = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth() - 1, 1);
          selectedDay = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), 1);
          await loadMonthData(false);
        });

        document.getElementById('next-month').addEventListener('click', async () => {
          monthAnchor = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth() + 1, 1);
          selectedDay = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), 1);
          await loadMonthData(false);
        });

        timezoneEl.textContent = currentTimeZoneLabel();
        resetForm();
        loadAuthAndData();
      </script>
    </body>
    </html>
    """
