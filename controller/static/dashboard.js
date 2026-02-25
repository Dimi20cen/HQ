    const REFRESH_RATE = 2000;
    const JOB_ACTIVITY_DAYS = 14;
    const JOB_ACTIVITY_REFRESH_RATE = 60000;
    const JOB_ACTIVITY_COLLAPSED_STORAGE_KEY = 'dashboard.jobActivityCollapsed.v1';
    const WIDGET_LAYOUT_STORAGE_KEY = 'dashboard.widgetLayout.v1';
    const WIDGET_ORDER_STORAGE_KEY = 'dashboard.widgetOrder.v1';
    const HIDDEN_TOOLS_STORAGE_KEY = 'dashboard.hiddenTools.v1';
    const DEFAULT_SETTINGS = {
        minWidgetHeight: 120,
        maxWidgetHeightPx: 760,
        minCardWidthPx: 320,
        dragAutoScrollEdgePx: 80,
        dragAutoScrollStepPx: 24
    };

    const state = {
        toolMap: new Map(),
        widgetLayout: loadWidgetLayout(),
        activeResize: null,
        dragSource: null,
        dragArmedCard: null,
        widgetOrder: loadWidgetOrder(),
        hiddenTools: loadHiddenTools(),
        hiddenToolsMenuOpen: false,
        reorderModeOpen: false,
        appsRowMenuOpenFor: null,
        dragAutoScrollRaf: 0,
        dragPointer: null,
        settings: { ...DEFAULT_SETTINGS },
        statusRefreshPromise: null,
        jobActivityCollapsed: loadJobActivityCollapsed()
    };
    const CATEGORY_ORDER = { display: 0, hybrid: 1, background: 2 };

    const els = {
        jobActivityBoard: document.getElementById('job-activity-board'),
        jobActivityToggle: document.getElementById('job-activity-toggle'),
        jobActivityGrid: document.getElementById('job-activity-grid'),
        jobActivityWeekdays: document.getElementById('job-activity-weekdays'),
        jobActivityTotal: document.getElementById('job-activity-total'),
        reorderModeBtn: document.getElementById('reorder-mode-btn'),
        reorderPanel: document.getElementById('reorder-panel'),
        appsMenuBtn: document.getElementById('apps-menu-btn'),
        hiddenToolsMenu: document.getElementById('hidden-tools-menu'),
        container: document.getElementById('tools-container')
    };

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    function safeId(name) {
        return name.replace(/[^a-zA-Z0-9_-]+/g, '_');
    }

    function normalizeCategory(value) {
        const category = typeof value === 'string' ? value.trim().toLowerCase() : '';
        if (category === 'display' || category === 'background' || category === 'hybrid') return category;
        return 'display';
    }

    function categoryLabel(category) {
        if (category === 'background') return 'Background';
        if (category === 'hybrid') return 'Hybrid';
        return 'Display';
    }

    function toToolViewModel(rawTool) {
        const id = String(rawTool?.name || '').trim();
        const title = String(rawTool?.title || id).trim() || id;
        const normalizedStatus = typeof rawTool?.status === 'string'
            ? rawTool.status.trim().toLowerCase()
            : 'unknown';
        return {
            id,
            name: id,
            title,
            category: normalizeCategory(rawTool?.category),
            status: normalizedStatus,
            autoStart: !!rawTool?.auto_start
        };
    }

    function sortToolsByCategory(tools) {
        return [...tools].sort((a, b) => {
            const ac = CATEGORY_ORDER[normalizeCategory(a?.category)] ?? 0;
            const bc = CATEGORY_ORDER[normalizeCategory(b?.category)] ?? 0;
            if (ac !== bc) return ac - bc;
            return String(a?.title || a?.name || '').localeCompare(String(b?.title || b?.name || ''));
        });
    }

    function loadWidgetLayout() {
        try {
            const raw = localStorage.getItem(WIDGET_LAYOUT_STORAGE_KEY);
            if (!raw) return {};
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch {
            return {};
        }
    }

    function saveWidgetLayout(name, patch) {
        if (!name || !patch || typeof patch !== 'object') return;
        const prev = state.widgetLayout[name] || {};
        const next = { ...prev, ...patch };
        state.widgetLayout[name] = next;
        localStorage.setItem(WIDGET_LAYOUT_STORAGE_KEY, JSON.stringify(state.widgetLayout));
    }

    function loadWidgetOrder() {
        try {
            const raw = localStorage.getItem(WIDGET_ORDER_STORAGE_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    function loadHiddenTools() {
        try {
            const raw = localStorage.getItem(HIDDEN_TOOLS_STORAGE_KEY);
            if (!raw) return new Set();
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return new Set();
            return new Set(parsed.filter(name => typeof name === 'string' && name.length > 0));
        } catch {
            return new Set();
        }
    }

    function loadJobActivityCollapsed() {
        try {
            return localStorage.getItem(JOB_ACTIVITY_COLLAPSED_STORAGE_KEY) === '1';
        } catch {
            return false;
        }
    }

    function saveJobActivityCollapsed() {
        try {
            localStorage.setItem(
                JOB_ACTIVITY_COLLAPSED_STORAGE_KEY,
                state.jobActivityCollapsed ? '1' : '0'
            );
        } catch {}
    }

    function saveHiddenTools() {
        localStorage.setItem(HIDDEN_TOOLS_STORAGE_KEY, JSON.stringify(Array.from(state.hiddenTools)));
    }

    function saveWidgetOrder() {
        const names = Array.from(els.container.querySelectorAll('.card'))
            .map(card => card.dataset.name)
            .filter(Boolean);
        state.widgetOrder = names;
        localStorage.setItem(WIDGET_ORDER_STORAGE_KEY, JSON.stringify(names));
    }

    function applySavedOrder(tools) {
        if (!Array.isArray(tools) || tools.length < 2 || state.widgetOrder.length === 0) return tools;
        const orderIndex = new Map(state.widgetOrder.map((name, idx) => [name, idx]));
        return [...tools].sort((a, b) => {
            const ai = orderIndex.has(a.name) ? orderIndex.get(a.name) : Number.MAX_SAFE_INTEGER;
            const bi = orderIndex.has(b.name) ? orderIndex.get(b.name) : Number.MAX_SAFE_INTEGER;
            if (ai !== bi) return ai - bi;
            return 0;
        });
    }

    function getMaxWidgetHeight() {
        const min = state.settings.minWidgetHeight;
        const viewportCap = Math.floor(window.innerHeight * 0.85);
        const userMax = Math.max(min, state.settings.maxWidgetHeightPx);
        return Math.max(min, Math.min(userMax, viewportCap));
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function parseIsoDate(value) {
        if (!value || typeof value !== 'string') return null;
        const parsed = new Date(`${value}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function toIsoDate(value) {
        const y = value.getFullYear();
        const m = String(value.getMonth() + 1).padStart(2, '0');
        const d = String(value.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    function addDays(value, days) {
        const next = new Date(value);
        next.setDate(next.getDate() + days);
        return next;
    }

    function formatLongDate(value) {
        return value.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    function weekdayInitial(value) {
        return value.toLocaleDateString(undefined, { weekday: 'short' }).charAt(0);
    }

    function contributionLevel(count, maxCount) {
        if (!count || count <= 0) return 0;
        if (!maxCount || maxCount <= 1) return 4;
        return clamp(Math.ceil((count / maxCount) * 4), 1, 4);
    }

    function renderJobActivityBoard(payload) {
        if (!els.jobActivityBoard || !els.jobActivityGrid) return;
        const totalEl = els.jobActivityTotal;
        const weekdaysEl = els.jobActivityWeekdays;

        const end = parseIsoDate(payload?.range_end) || new Date();
        const start = parseIsoDate(payload?.range_start) || addDays(end, -(JOB_ACTIVITY_DAYS - 1));
        const rawDays = Array.isArray(payload?.days) ? payload.days : [];
        const countMap = new Map();
        rawDays.forEach(item => {
            if (!item || typeof item.date !== 'string') return;
            const nextCount = Number(item.count || 0);
            countMap.set(item.date, nextCount > 0 ? nextCount : 0);
        });

        const totalDays = Math.max(1, Math.round((end - start) / 86400000) + 1);
        const cellDays = totalDays;
        const maxCount = Math.max(0, Number(payload?.max_count || 0));
        let totalApplied = 0;

        els.jobActivityGrid.innerHTML = '';
        if (weekdaysEl) weekdaysEl.innerHTML = '';

        if (weekdaysEl) {
            const labelDays = Math.min(7, cellDays);
            for (let i = 0; i < labelDays; i++) {
                const current = addDays(start, i);
                weekdaysEl.appendChild(el('span', '', weekdayInitial(current)));
            }
        }

        for (let i = 0; i < cellDays; i++) {
            const current = addDays(start, i);
            const dateKey = toIsoDate(current);
            const count = countMap.get(dateKey) || 0;
            const level = contributionLevel(count, maxCount);
            const cell = el('span', `job-activity-cell level-${level}`);
            totalApplied += count;
            cell.title = `${count} application${count === 1 ? '' : 's'} on ${formatLongDate(current)}`;
            els.jobActivityGrid.appendChild(cell);
        }

        if (totalEl) {
            totalEl.textContent = `${totalApplied} total`;
        }
        els.jobActivityGrid.setAttribute(
            'aria-label',
            `${totalApplied} job applications in the last ${totalDays} days`
        );
    }

    function setJobActivityCollapsed(collapsed) {
        state.jobActivityCollapsed = !!collapsed;
        if (els.jobActivityBoard) {
            els.jobActivityBoard.classList.toggle('is-collapsed', state.jobActivityCollapsed);
        }
        if (els.jobActivityToggle) {
            els.jobActivityToggle.setAttribute('aria-expanded', state.jobActivityCollapsed ? 'false' : 'true');
            els.jobActivityToggle.setAttribute(
                'aria-label',
                state.jobActivityCollapsed
                    ? 'Expand job applications panel'
                    : 'Collapse job applications panel'
            );
        }
        saveJobActivityCollapsed();
    }

    async function loadJobActivity() {
        if (!els.jobActivityBoard) return;
        try {
            const resp = await fetch(`/dashboard/job-applications?days=${JOB_ACTIVITY_DAYS}`);
            if (!resp.ok) throw new Error('failed');
            const data = await resp.json();
            renderJobActivityBoard(data || {});
        } catch (error) {
            if (els.jobActivityTotal) {
                els.jobActivityTotal.textContent = '';
            }
            if (els.jobActivityGrid) {
                els.jobActivityGrid.innerHTML = '';
            }
            if (els.jobActivityWeekdays) {
                els.jobActivityWeekdays.innerHTML = '';
            }
            console.error('Failed to load job activity', error);
        }
    }

    function canUseDragReorder() {
        return !window.matchMedia('(pointer: coarse)').matches;
    }

    function openToolPage(name) {
        const url = `/proxy/${encodeURIComponent(name)}/widget`;
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    function getCurrentCardOrder() {
        return Array.from(els.container.querySelectorAll('.card'))
            .map(card => card.dataset.name)
            .filter(Boolean);
    }

    function applyCardOrder(order) {
        if (!Array.isArray(order) || order.length === 0) return;
        const frag = document.createDocumentFragment();
        order.forEach(name => {
            const entry = state.toolMap.get(name);
            if (entry && entry.card) frag.appendChild(entry.card);
        });
        els.container.appendChild(frag);
        saveWidgetOrder();
        requestAnimationFrame(resizeAllCards);
    }

    function getGridMetrics() {
        const styles = getComputedStyle(els.container);
        const columns = styles.gridTemplateColumns.split(/\s+/).filter(Boolean).length || 1;
        const colGap = parseFloat(styles.columnGap || styles.gap || '20') || 20;
        const columnWidth = (els.container.clientWidth - colGap * (columns - 1)) / columns;
        return { columns, colGap, columnWidth };
    }

    function getGridRowMetrics() {
        const styles = getComputedStyle(els.container);
        const rowHeight = parseFloat(styles.gridAutoRows || '8') || 8;
        const rowGap = parseFloat(styles.rowGap || styles.gap || '14') || 14;
        return { rowHeight, rowGap };
    }

    function getMinCardSpan(columns, colGap, columnWidth) {
        const minWidth = Math.max(200, state.settings.minCardWidthPx);
        return clamp(Math.ceil((minWidth + colGap) / (columnWidth + colGap)), 1, columns);
    }

    function getCurrentCardColSpan(card) {
        const match = (card.style.gridColumnEnd || '').match(/span\s+(\d+)/);
        return match ? Math.max(1, Number(match[1])) : 1;
    }

    function enforceCardSpanConstraints() {
        const { columns, colGap, columnWidth } = getGridMetrics();
        const minSpan = getMinCardSpan(columns, colGap, columnWidth);

        state.toolMap.forEach((entry, name) => {
            const { card } = entry;
            if (card.classList.contains('is-hidden')) return;
            const currentSpan = getCurrentCardColSpan(card);
            const constrained = clamp(currentSpan, minSpan, columns);
            if (constrained !== currentSpan) {
                card.style.gridColumnEnd = `span ${constrained}`;
                saveWidgetLayout(name, { colSpan: constrained });
            }
        });
    }

    function enforceWidgetHeightConstraints() {
        const maxHeight = getMaxWidgetHeight();
        const minHeight = state.settings.minWidgetHeight;
        state.toolMap.forEach((entry, name) => {
            const widgetBox = document.getElementById(`widget-box-${entry.sId}`);
            if (!widgetBox || widgetBox.style.display === 'none') return;
            const current = widgetBox.getBoundingClientRect().height;
            const constrained = clamp(current, minHeight, maxHeight);
            if (Math.round(current) !== Math.round(constrained)) {
                widgetBox.style.height = `${constrained}px`;
                saveWidgetLayout(name, { height: Math.round(constrained) });
            }
        });
    }

    async function loadDashboard() {
        try {
            const resp = await fetch('/tools');
            const data = await resp.json();
            const rawTools = applySavedOrder(sortToolsByCategory(data.tools || []));
            const tools = rawTools.map(toToolViewModel).filter(tool => !!tool.id);

            stopWidgetResize();
            els.container.innerHTML = '';
            state.toolMap.clear();

            if (tools.length === 0) {
                renderHiddenToolsMenu();
                const empty = el('div', 'empty-state', 'No tools found.');
                els.container.appendChild(empty);
                return;
            }

            tools.forEach(tool => {
                const card = createToolCard(tool);
                els.container.appendChild(card);
            });

            renderHiddenToolsMenu();
            requestAnimationFrame(resizeAllCards);
            requestAnimationFrame(enforceCardSpanConstraints);
            refreshAllStatuses();

        } catch (e) {
            console.error(e);
        }
    }

    function createToolCard(tool) {
        const card = el('div', `card status-${tool.status || 'stopped'}`);
        const sId = safeId(tool.id);
        card.style.setProperty('--enter-index', state.toolMap.size);

        card.id = `card-${sId}`;
        card.dataset.name = tool.id;
        card.dataset.category = tool.category;

        const cardBody = el('div', 'card-body');
        const header = el('div', 'tool-header');
        const left = el('div', 'tool-header-left');
        const right = el('div', 'header-right');

        const name = el('span', 'tool-name', tool.title);
        const statusLine = el('div', 'status-line');
        const statusDot = el('span', 'status-dot');
        const statusText = el('span', 'status-text', 'Checking...');

        statusLine.appendChild(statusDot);
        statusLine.appendChild(statusText);
        left.appendChild(name);
        left.appendChild(statusLine);

        const btn = el('button', 'btn-status btn-yellow');
        btn.id = `btn-${sId}`;
        btn.disabled = true;
        btn.type = 'button';
        btn.setAttribute('aria-label', `Toggle ${tool.title}`);
        btn.textContent = '⏻';
        btn.addEventListener('click', () => statusButtonAction(tool.id));

        const openBtn = el('button', 'tool-open-btn');
        openBtn.type = 'button';
        openBtn.setAttribute('aria-label', `Open ${tool.title}`);
        openBtn.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M14 5h5v5M10 14L19 5M19 13v6H5V5h6" />
            </svg>
        `;
        openBtn.addEventListener('click', event => {
            event.stopPropagation();
            openToolPage(tool.id);
        });

        const settingsBtn = el('button', 'tool-settings-btn');
        settingsBtn.type = 'button';
        settingsBtn.setAttribute('aria-label', `Open ${tool.title} settings`);
        settingsBtn.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 7h9M15 7h5M9 7v0M4 17h5M11 17h9M15 17v0M13 7a2 2 0 1 0-4 0a2 2 0 0 0 4 0m4 10a2 2 0 1 0-4 0a2 2 0 0 0 4 0" />
            </svg>
        `;
        const settingsMenu = el('div', 'tool-settings-menu');
        const visibilityAction = el('button', 'tool-settings-item');
        visibilityAction.type = 'button';
        const autoStartAction = el('button', 'tool-settings-item');
        autoStartAction.type = 'button';
        settingsMenu.appendChild(visibilityAction);
        settingsMenu.appendChild(autoStartAction);

        settingsBtn.addEventListener('click', event => {
            event.stopPropagation();
            const open = !settingsMenu.classList.contains('is-open');
            setHiddenToolsMenuOpen(false);
            closeAllToolMenus(card);
            settingsMenu.classList.toggle('is-open', open);
            card.classList.toggle('has-open-menu', open);
        });
        visibilityAction.addEventListener('click', event => {
            event.stopPropagation();
            const hidden = !card.classList.contains('is-hidden');
            setToolHidden(tool.id, hidden);
            settingsMenu.classList.remove('is-open');
        });
        autoStartAction.addEventListener('click', async event => {
            event.stopPropagation();
            const entry = state.toolMap.get(tool.id);
            if (!entry) return;
            await setToolAutoStart(tool.id, !entry.autoStart);
            settingsMenu.classList.remove('is-open');
        });

        right.appendChild(btn);
        right.appendChild(openBtn);
        right.appendChild(settingsBtn);

        header.appendChild(left);
        header.appendChild(right);
        cardBody.appendChild(header);
        card.appendChild(cardBody);
        card.appendChild(settingsMenu);
        card.draggable = canUseDragReorder();
        wireCardDnD(card, header);

        const widgetBox = el('div', 'widget-container');
        widgetBox.id = `widget-box-${sId}`;
        const savedLayout = state.widgetLayout[tool.id] || {};
        const savedHeight = savedLayout.height;
        if (Number.isFinite(savedHeight)) {
            const h = clamp(savedHeight, state.settings.minWidgetHeight, getMaxWidgetHeight());
            widgetBox.style.height = `${h}px`;
        }
        const savedColSpan = savedLayout.colSpan;
        if (Number.isFinite(savedColSpan) && savedColSpan >= 1) {
            const { columns, colGap, columnWidth } = getGridMetrics();
            const minSpan = getMinCardSpan(columns, colGap, columnWidth);
            card.style.gridColumnEnd = `span ${clamp(Math.floor(savedColSpan), minSpan, columns)}`;
        }
        const iframe = el('iframe');
        iframe.id = `iframe-${sId}`;
        widgetBox.appendChild(iframe);

        const resizeHandle = el('button', 'widget-resize-handle widget-resize-control');
        resizeHandle.id = `resize-handle-${sId}`;
        resizeHandle.type = 'button';
        resizeHandle.setAttribute('aria-label', `Resize ${tool.title} widget`);
        resizeHandle.setAttribute('title', 'Drag this corner to resize');
        resizeHandle.addEventListener('pointerdown', event => startWidgetResize(event, tool.id, 'corner'));

        const resizeEdgeBottom = el('button', 'widget-resize-edge widget-resize-edge-bottom widget-resize-control');
        resizeEdgeBottom.type = 'button';
        resizeEdgeBottom.setAttribute('aria-label', `Resize ${tool.title} widget height`);
        resizeEdgeBottom.setAttribute('title', 'Drag bottom edge to resize');
        resizeEdgeBottom.addEventListener('pointerdown', event => startWidgetResize(event, tool.id, 'bottom'));

        widgetBox.appendChild(resizeEdgeBottom);
        widgetBox.appendChild(resizeHandle);
        card.appendChild(widgetBox);

        state.toolMap.set(tool.id, {
            card,
            statusDot,
            statusText,
            btn,
            sId,
            view: tool,
            settingsMenu,
            visibilityAction,
            autoStartAction,
            autoStart: !!tool.autoStart,
            statusKnown: tool.status === 'running' || tool.status === 'stopped',
            alive: tool.status === 'running',
            pendingAction: false
        });
        if (state.hiddenTools.has(tool.id)) {
            card.classList.add('is-hidden');
        }
        syncToolMenuActions(tool.id);
        return card;
    }

    function resizeCard(card) {
        if (!card || card.classList.contains('is-hidden')) return;
        const body = card.querySelector('.card-body');
        const widget = card.querySelector('.widget-container');
        let height = 0;

        if (body) height += body.scrollHeight;
        if (widget && widget.style.display !== 'none') height += widget.scrollHeight;

        height += 12;
        const { rowHeight, rowGap } = getGridRowMetrics();
        const rowSpan = Math.ceil((height + rowGap) / (rowHeight + rowGap));
        card.style.gridRowEnd = `span ${rowSpan}`;
    }

    function resizeAllCards() {
        document.querySelectorAll('.card').forEach(resizeCard);
    }

    function wireCardDnD(card, header) {
        if (canUseDragReorder()) {
            header.setAttribute('title', 'Drag to reorder');
        } else {
            header.removeAttribute('title');
        }
        header.addEventListener('pointerdown', event => {
            const fromControl = event.target && event.target.closest('.btn-status, .tool-open-btn, .tool-settings-btn, .tool-settings-menu');
            if (fromControl) return;
            state.dragArmedCard = card;
        });
        header.addEventListener('pointerup', () => {
            if (state.dragArmedCard === card) state.dragArmedCard = null;
        });
        header.addEventListener('pointercancel', () => {
            if (state.dragArmedCard === card) state.dragArmedCard = null;
        });

        card.addEventListener('dragstart', event => {
            if (!event.dataTransfer) return;
            if (state.activeResize) {
                event.preventDefault();
                return;
            }
            if (state.dragArmedCard !== card) {
                event.preventDefault();
                return;
            }
            const fromControl = event.target && event.target.closest('.btn-status, .tool-open-btn, .tool-settings-btn, .tool-settings-menu');
            if (fromControl) {
                event.preventDefault();
                return;
            }
            state.dragSource = card;
            card.classList.add('is-dragging');
            state.dragPointer = null;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', card.dataset.name || '');
        });

        card.addEventListener('dragend', () => {
            if (state.dragSource) {
                state.dragSource.classList.remove('is-dragging');
            }
            state.dragSource = null;
            if (state.dragArmedCard === card) state.dragArmedCard = null;
            stopDragAutoScroll();
            saveWidgetOrder();
            requestAnimationFrame(resizeAllCards);
        });
    }

    function findDropTarget(clientX, clientY) {
        const hovered = document.elementFromPoint(clientX, clientY);
        const target = hovered ? hovered.closest('.card') : null;
        if (!target || target.classList.contains('is-hidden') || target === state.dragSource) return null;
        return target;
    }

    function determineInsertBefore(target, clientX, clientY) {
        const targetRect = target.getBoundingClientRect();
        if (!state.dragSource) return true;
        const sourceRect = state.dragSource.getBoundingClientRect();
        const sameRow = Math.abs(sourceRect.top - targetRect.top) < (targetRect.height * 0.35);

        if (sameRow) {
            return clientX < targetRect.left + targetRect.width / 2;
        }
        return clientY < targetRect.top + targetRect.height / 2;
    }

    function runDragAutoScroll() {
        if (!state.dragSource || !state.dragPointer) {
            state.dragAutoScrollRaf = 0;
            return;
        }

        const y = state.dragPointer.y;
        const topZone = state.settings.dragAutoScrollEdgePx;
        const bottomZone = window.innerHeight - state.settings.dragAutoScrollEdgePx;

        if (y < topZone) {
            window.scrollBy(0, -state.settings.dragAutoScrollStepPx);
        } else if (y > bottomZone) {
            window.scrollBy(0, state.settings.dragAutoScrollStepPx);
        }

        state.dragAutoScrollRaf = requestAnimationFrame(runDragAutoScroll);
    }

    function startDragAutoScroll(clientX, clientY) {
        state.dragPointer = { x: clientX, y: clientY };
        if (state.dragAutoScrollRaf) return;
        state.dragAutoScrollRaf = requestAnimationFrame(runDragAutoScroll);
    }

    function stopDragAutoScroll() {
        if (state.dragAutoScrollRaf) cancelAnimationFrame(state.dragAutoScrollRaf);
        state.dragAutoScrollRaf = 0;
        state.dragPointer = null;
    }

    function startWidgetResize(event, name, mode = 'corner') {
        if (event.button !== 0) return;
        stopWidgetResize();

        const entry = state.toolMap.get(name);
        if (!entry) return;

        const { card, sId } = entry;
        const widgetBox = document.getElementById(`widget-box-${sId}`);
        if (!widgetBox || widgetBox.style.display === 'none') return;

        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);

        state.activeResize = {
            name,
            card,
            widgetBox,
            handle: event.currentTarget,
            mode,
            startY: event.clientY,
            startX: event.clientX,
            startHeight: widgetBox.getBoundingClientRect().height,
            startWidth: card.getBoundingClientRect().width,
            startColSpan: getCurrentCardColSpan(card),
            pointerId: event.pointerId,
            nextHeight: widgetBox.getBoundingClientRect().height,
            nextColSpan: getCurrentCardColSpan(card),
            rafId: 0
        };

        card.classList.add('is-resizing');
        document.body.classList.add('is-resizing');
        document.body.classList.toggle('is-resizing-bottom', mode === 'bottom');
        document.body.classList.toggle('is-resizing-corner', mode !== 'bottom');
    }

    function onWidgetResizeMove(event) {
        const resize = state.activeResize;
        if (!resize) return;
        if (event.pointerId !== resize.pointerId) return;
        event.preventDefault();

        resize.lastX = event.clientX;
        resize.lastY = event.clientY;
        if (resize.rafId) return;
        resize.rafId = requestAnimationFrame(() => {
            const current = state.activeResize;
            if (!current) return;
            current.rafId = 0;

            const deltaY = (current.lastY ?? current.startY) - current.startY;
            const maxHeight = getMaxWidgetHeight();
            const nextHeight = clamp(current.startHeight + deltaY, state.settings.minWidgetHeight, maxHeight);
            current.widgetBox.style.height = `${nextHeight}px`;
            current.nextHeight = nextHeight;

            if (current.mode !== 'bottom') {
                const deltaX = (current.lastX ?? current.startX) - current.startX;
                const desiredWidth = Math.max(200, current.startWidth + deltaX);
                const { columns, colGap, columnWidth } = getGridMetrics();
                const minSpan = getMinCardSpan(columns, colGap, columnWidth);
                const span = clamp(Math.round((desiredWidth + colGap) / (columnWidth + colGap)), minSpan, columns);
                current.card.style.gridColumnEnd = `span ${span}`;
                current.nextColSpan = span;
            }

            resizeCard(current.card);
        });
    }

    function stopWidgetResize(event) {
        const resize = state.activeResize;
        if (!resize) return;
        if (event && event.pointerId !== resize.pointerId) return;

        if (resize.rafId) cancelAnimationFrame(resize.rafId);
        if (resize.handle && resize.handle.hasPointerCapture(resize.pointerId)) {
            resize.handle.releasePointerCapture(resize.pointerId);
        }

        resize.card.classList.remove('is-resizing');
        document.body.classList.remove('is-resizing');
        document.body.classList.remove('is-resizing-bottom', 'is-resizing-corner');
        const { columns, colGap, columnWidth } = getGridMetrics();
        const minSpan = getMinCardSpan(columns, colGap, columnWidth);
        saveWidgetLayout(resize.name, {
            height: Math.round(resize.nextHeight || resize.startHeight),
            colSpan: clamp(Math.round(resize.nextColSpan || resize.startColSpan), minSpan, columns)
        });
        state.activeResize = null;
    }

    function syncVisibilityAction(name) {
        const entry = state.toolMap.get(name);
        if (!entry || !entry.visibilityAction) return;
        const hidden = entry.card.classList.contains('is-hidden');
        entry.visibilityAction.textContent = hidden ? 'Show' : 'Hide';
    }

    function syncToolMenuActions(name) {
        const entry = state.toolMap.get(name);
        if (!entry) return;
        syncVisibilityAction(name);
        if (entry.autoStartAction) {
            entry.autoStartAction.textContent = entry.autoStart ? 'Disable Auto Start' : 'Enable Auto Start';
            entry.autoStartAction.disabled = !!entry.pendingAction;
        }
    }

    function closeAllToolMenus(exceptCard = null) {
        state.toolMap.forEach(({ card, settingsMenu }) => {
            if (!settingsMenu) return;
            if (exceptCard && card === exceptCard) return;
            settingsMenu.classList.remove('is-open');
            card.classList.remove('has-open-menu');
        });
    }

    function setToolHidden(name, hidden) {
        const entry = state.toolMap.get(name);
        if (!entry) return;

        entry.card.classList.toggle('is-hidden', hidden);
        if (hidden) {
            state.hiddenTools.add(name);
        } else {
            state.hiddenTools.delete(name);
        }

        saveHiddenTools();
        syncToolMenuActions(name);
        renderHiddenToolsMenu();
        enforceCardSpanConstraints();
        requestAnimationFrame(resizeAllCards);
    }

    async function setToolAutoStart(name, enabled) {
        const entry = state.toolMap.get(name);
        if (!entry || entry.pendingAction) return;
        entry.pendingAction = true;
        syncToolMenuActions(name);
        try {
            const resp = await fetch(`/tools/${encodeURIComponent(name)}/auto-start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            if (!resp.ok) throw new Error('save failed');
            entry.autoStart = enabled;
            syncToolMenuActions(name);
            renderHiddenToolsMenu();
        } catch {
            alert('Failed to update Auto Start');
        } finally {
            entry.pendingAction = false;
            syncToolMenuActions(name);
        }
    }

    async function toggleToolRunning(name) {
        const entry = state.toolMap.get(name);
        if (!entry || entry.pendingAction) return;
        entry.pendingAction = true;
        syncToolMenuActions(name);
        try {
            const action = entry.alive ? 'kill' : 'launch';
            const resp = await fetch(`/tools/${encodeURIComponent(name)}/${action}`, { method: 'POST' });
            if (!resp.ok) throw new Error('request failed');
            setTimeout(refreshAllStatuses, 400);
        } catch {
            alert('Failed to update running state');
        } finally {
            entry.pendingAction = false;
            syncToolMenuActions(name);
            renderHiddenToolsMenu();
        }
    }

    function setHiddenToolsMenuOpen(open) {
        if (!els.hiddenToolsMenu || !els.appsMenuBtn) return;
        state.hiddenToolsMenuOpen = !!open;
        if (!state.hiddenToolsMenuOpen) {
            state.appsRowMenuOpenFor = null;
            renderHiddenToolsMenu();
        }
        els.hiddenToolsMenu.hidden = !state.hiddenToolsMenuOpen;
        els.appsMenuBtn.setAttribute('aria-expanded', state.hiddenToolsMenuOpen ? 'true' : 'false');
    }

    function setReorderModeOpen(open) {
        if (!els.reorderPanel || !els.reorderModeBtn) return;
        state.reorderModeOpen = !!open;
        els.reorderPanel.hidden = !state.reorderModeOpen;
        els.reorderModeBtn.setAttribute('aria-expanded', state.reorderModeOpen ? 'true' : 'false');
        if (state.reorderModeOpen) {
            renderReorderPanel();
        }
    }

    function renderReorderPanel() {
        if (!els.reorderPanel) return;
        const names = getCurrentCardOrder();
        els.reorderPanel.innerHTML = '';

        const title = el('div', 'reorder-title', 'Reorder Tools');
        const list = el('div', 'reorder-list');
        names.forEach((name, index) => {
            const row = el('div', 'reorder-row');
            const entry = state.toolMap.get(name);
            const label = el('div', 'reorder-name', entry?.view?.title || name);
            const controls = el('div', 'reorder-controls');
            const upBtn = el('button', 'reorder-move-btn', '↑');
            upBtn.type = 'button';
            upBtn.setAttribute('aria-label', `Move ${name} up`);
            upBtn.disabled = index === 0;
            upBtn.addEventListener('click', event => {
                event.stopPropagation();
                moveToolInOrder(name, -1);
            });

            const downBtn = el('button', 'reorder-move-btn', '↓');
            downBtn.type = 'button';
            downBtn.setAttribute('aria-label', `Move ${name} down`);
            downBtn.disabled = index === names.length - 1;
            downBtn.addEventListener('click', event => {
                event.stopPropagation();
                moveToolInOrder(name, 1);
            });

            controls.appendChild(upBtn);
            controls.appendChild(downBtn);
            row.appendChild(label);
            row.appendChild(controls);
            list.appendChild(row);
        });

        const footer = el('div', 'reorder-panel-footer');
        const doneBtn = el('button', 'reorder-done-btn', 'Done');
        doneBtn.type = 'button';
        doneBtn.addEventListener('click', event => {
            event.stopPropagation();
            setReorderModeOpen(false);
        });
        footer.appendChild(doneBtn);

        els.reorderPanel.appendChild(title);
        els.reorderPanel.appendChild(list);
        els.reorderPanel.appendChild(footer);
    }

    function moveToolInOrder(name, direction) {
        const order = getCurrentCardOrder();
        const from = order.indexOf(name);
        if (from === -1) return;
        const to = clamp(from + direction, 0, order.length - 1);
        if (from === to) return;
        const [moved] = order.splice(from, 1);
        order.splice(to, 0, moved);
        applyCardOrder(order);
        if (state.reorderModeOpen) renderReorderPanel();
    }

    function closeAppsRowMenus() {
        state.appsRowMenuOpenFor = null;
        if (state.hiddenToolsMenuOpen) renderHiddenToolsMenu();
    }

    function renderHiddenToolsMenu() {
        if (!els.hiddenToolsMenu) return;
        const knownTools = new Set(state.toolMap.keys());
        state.hiddenTools.forEach(name => {
            if (!knownTools.has(name)) state.hiddenTools.delete(name);
        });
        saveHiddenTools();

        const toolNames = Array.from(knownTools).sort((a, b) => {
            const aEntry = state.toolMap.get(a);
            const bEntry = state.toolMap.get(b);
            const ac = CATEGORY_ORDER[aEntry?.view?.category] ?? 0;
            const bc = CATEGORY_ORDER[bEntry?.view?.category] ?? 0;
            if (ac !== bc) return ac - bc;
            return (aEntry?.view?.title || a).localeCompare(bEntry?.view?.title || b);
        });
        els.hiddenToolsMenu.innerHTML = '';

        if (toolNames.length === 0) {
            els.hiddenToolsMenu.appendChild(el('div', 'hidden-tools-empty', 'No apps'));
            return;
        }

        let currentCategory = '';
        toolNames.forEach(name => {
            const row = el('div', 'apps-menu-row');
            const entry = state.toolMap.get(name);
            const view = entry?.view;
            const category = view?.category || 'display';
            if (category !== currentCategory) {
                currentCategory = category;
                els.hiddenToolsMenu.appendChild(el('div', 'hidden-tools-label', categoryLabel(category)));
            }
            const nameLabel = el('button', 'apps-menu-name', view?.title || name);
            const rowActions = el('div', 'apps-row-actions');
            const hidden = state.hiddenTools.has(name);
            const autoStart = !!(entry && entry.autoStart);
            const statusKnown = !!(entry && entry.statusKnown);
            const alive = !!(entry && entry.alive);
            const pendingAction = !!(entry && entry.pendingAction);
            nameLabel.type = 'button';
            nameLabel.setAttribute(
                'aria-label',
                `${hidden ? 'Show' : 'Hide'} ${name} on dashboard`
            );
            nameLabel.addEventListener('click', event => {
                event.stopPropagation();
                setToolHidden(name, !hidden);
                state.appsRowMenuOpenFor = null;
                renderHiddenToolsMenu();
            });
            if (statusKnown) {
                if (!alive) {
                    row.classList.add('is-stopped-app');
                } else if (hidden) {
                    row.classList.add('is-running-hidden-app');
                } else {
                    row.classList.add('is-running-visible-app');
                }
            }

            const settingsBtn = el('button', 'apps-row-settings-btn');
            settingsBtn.type = 'button';
            settingsBtn.setAttribute('aria-label', `Open ${name} visibility settings`);
            settingsBtn.innerHTML = `
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 7h9M15 7h5M9 7v0M4 17h5M11 17h9M15 17v0M13 7a2 2 0 1 0-4 0a2 2 0 0 0 4 0m4 10a2 2 0 1 0-4 0a2 2 0 0 0 4 0" />
                </svg>
            `;
            const openBtn = el('button', 'apps-row-open-btn');
            openBtn.type = 'button';
            openBtn.setAttribute('aria-label', `Open ${name}`);
            openBtn.innerHTML = `
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M14 5h5v5M10 14L19 5M19 13v6H5V5h6" />
                </svg>
            `;
            openBtn.addEventListener('click', event => {
                event.stopPropagation();
                openToolPage(name);
            });
            const powerBtn = el('button', 'apps-row-power-btn');
            powerBtn.type = 'button';
            powerBtn.setAttribute('aria-label', statusKnown ? `${alive ? 'Stop' : 'Start'} ${name}` : `Checking ${name} status`);
            powerBtn.textContent = '⏻';
            powerBtn.classList.toggle('is-running', statusKnown && alive);
            powerBtn.classList.toggle('is-stopped', statusKnown && !alive);
            powerBtn.disabled = pendingAction || !statusKnown;
            powerBtn.addEventListener('click', async event => {
                event.stopPropagation();
                await toggleToolRunning(name);
                renderHiddenToolsMenu();
            });

            const rowMenu = el('div', 'apps-row-menu');
            if (state.appsRowMenuOpenFor === name) rowMenu.classList.add('is-open');

            const toggleBtn = el(
                'button',
                'apps-row-menu-item',
                hidden ? 'Show' : 'Hide'
            );
            toggleBtn.type = 'button';
            toggleBtn.addEventListener('click', event => {
                event.stopPropagation();
                setToolHidden(name, !hidden);
                state.appsRowMenuOpenFor = null;
                renderHiddenToolsMenu();
            });
            rowMenu.appendChild(toggleBtn);

            const autoStartBtn = el(
                'button',
                'apps-row-menu-item',
                autoStart ? 'Disable Auto Start' : 'Enable Auto Start'
            );
            autoStartBtn.type = 'button';
            autoStartBtn.disabled = pendingAction;
            autoStartBtn.addEventListener('click', async event => {
                event.stopPropagation();
                await setToolAutoStart(name, !autoStart);
                state.appsRowMenuOpenFor = null;
                renderHiddenToolsMenu();
            });
            rowMenu.appendChild(autoStartBtn);

            settingsBtn.addEventListener('click', event => {
                event.stopPropagation();
                state.appsRowMenuOpenFor = state.appsRowMenuOpenFor === name ? null : name;
                renderHiddenToolsMenu();
            });

            rowActions.appendChild(openBtn);
            rowActions.appendChild(settingsBtn);
            rowActions.appendChild(powerBtn);
            row.appendChild(nameLabel);
            row.appendChild(rowActions);
            row.appendChild(rowMenu);
            els.hiddenToolsMenu.appendChild(row);
        });
    }

    async function statusButtonAction(name) {
        const entry = state.toolMap.get(name);
        if (!entry) return;

        const { btn } = entry;
        const action = btn.dataset.action;

        if (!action) return;

        btn.className = 'btn-status btn-yellow';
        btn.disabled = true;

        try {
            await fetch(`/tools/${name}/${action}`, { method: 'POST' });
        } catch {
            alert('Command failed');
        }

        setTimeout(refreshAllStatuses, 1000);
    }

    async function refreshAllStatuses() {
        if (state.statusRefreshPromise) return state.statusRefreshPromise;
        state.statusRefreshPromise = (async () => {
        try {
            const resp = await fetch('/tools/status-all');
            const data = await resp.json();
            const tools = data.tools || [];

            tools.forEach(tool => {
                const entry = state.toolMap.get(tool.name);
                if (!entry) return;

                const { card, statusDot, statusText, btn, sId } = entry;
                const widgetBox = document.getElementById(`widget-box-${sId}`);
                const iframe = document.getElementById(`iframe-${sId}`);
                const resizeControls = widgetBox ? widgetBox.querySelectorAll('.widget-resize-control') : [];
                const alive = !!tool.alive;
                entry.statusKnown = true;
                entry.alive = alive;

                card.dataset.alive = alive ? '1' : '0';
                card.classList.toggle('status-running', alive);
                card.classList.toggle('status-stopped', !alive);

                statusDot.classList.toggle('running', alive);
                statusDot.classList.toggle('stopped', !alive);

                statusText.textContent = alive
                    ? `Running (PID: ${tool.pid})`
                    : 'Stopped';

                btn.disabled = false;
                btn.dataset.action = alive ? 'kill' : 'launch';
                btn.className = alive ? 'btn-status btn-green' : 'btn-status btn-red';
                syncToolMenuActions(tool.name);

                if (widgetBox && iframe) {
                    if (alive) {
                        if (!iframe.src) {
                            iframe.src = `/proxy/${encodeURIComponent(tool.name)}/widget`;
                        }
                        widgetBox.style.display = 'block';
                        resizeControls.forEach(node => {
                            node.style.display = 'block';
                        });
                    } else {
                        widgetBox.style.display = 'none';
                        iframe.removeAttribute('src');
                        resizeControls.forEach(node => {
                            node.style.display = 'none';
                        });
                    }
                }

                requestAnimationFrame(() => resizeCard(card));
            });

            enforceCardSpanConstraints();
            requestAnimationFrame(resizeAllCards);
            if (state.hiddenToolsMenuOpen) renderHiddenToolsMenu();
            if (state.reorderModeOpen) renderReorderPanel();

        } catch (e) {
            console.error('Refresh failed', e);
        }
        })();

        try {
            await state.statusRefreshPromise;
        } finally {
            state.statusRefreshPromise = null;
        }
    }

    els.container.addEventListener('dragover', event => {
        if (!state.dragSource) return;
        event.preventDefault();
        startDragAutoScroll(event.clientX, event.clientY);
        const target = findDropTarget(event.clientX, event.clientY);
        if (!target) return;

        const before = determineInsertBefore(target, event.clientX, event.clientY);
        if (before) {
            els.container.insertBefore(state.dragSource, target);
        } else {
            els.container.insertBefore(state.dragSource, target.nextElementSibling);
        }
        requestAnimationFrame(resizeAllCards);
    });

    els.container.addEventListener('drop', event => {
        if (!state.dragSource) return;
        event.preventDefault();
        stopDragAutoScroll();
        saveWidgetOrder();
    });
    document.addEventListener('pointermove', onWidgetResizeMove);
    document.addEventListener('pointerup', stopWidgetResize);
    document.addEventListener('pointercancel', stopWidgetResize);
    if (els.appsMenuBtn) {
        els.appsMenuBtn.addEventListener('click', event => {
            event.stopPropagation();
            closeAllToolMenus();
            setReorderModeOpen(false);
            setHiddenToolsMenuOpen(!state.hiddenToolsMenuOpen);
        });
    }
    if (els.reorderModeBtn) {
        els.reorderModeBtn.addEventListener('click', event => {
            event.stopPropagation();
            closeAllToolMenus();
            setHiddenToolsMenuOpen(false);
            setReorderModeOpen(!state.reorderModeOpen);
        });
    }
    if (els.jobActivityToggle) {
        els.jobActivityToggle.addEventListener('click', event => {
            event.stopPropagation();
            setJobActivityCollapsed(!state.jobActivityCollapsed);
        });
    }
    document.addEventListener('click', event => {
        const inMenu = event.target && event.target.closest('.tool-settings-menu');
        const inButton = event.target && event.target.closest('.tool-settings-btn');
        const inHiddenToolsMenu = event.target && event.target.closest('#hidden-tools-menu');
        const inAppsBtn = event.target && event.target.closest('#apps-menu-btn');
        const inReorderPanel = event.target && event.target.closest('#reorder-panel');
        const inReorderBtn = event.target && event.target.closest('#reorder-mode-btn');
        if (!inMenu && !inButton) closeAllToolMenus();
        if (!inHiddenToolsMenu && !inAppsBtn) {
            setHiddenToolsMenuOpen(false);
        } else if (!event.target.closest('.apps-row-settings-btn, .apps-row-menu')) {
            closeAppsRowMenus();
        }
        if (!inReorderPanel && !inReorderBtn) {
            setReorderModeOpen(false);
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            closeAllToolMenus();
            setHiddenToolsMenuOpen(false);
            setReorderModeOpen(false);
        }
    });
    window.addEventListener('resize', () => {
        enforceCardSpanConstraints();
        enforceWidgetHeightConstraints();
        requestAnimationFrame(resizeAllCards);
    });

    setJobActivityCollapsed(state.jobActivityCollapsed);
    loadDashboard();
    loadJobActivity();
    setInterval(refreshAllStatuses, REFRESH_RATE);
    setInterval(loadJobActivity, JOB_ACTIVITY_REFRESH_RATE);
