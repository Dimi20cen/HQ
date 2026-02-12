    const REFRESH_RATE = 2000;
    const GRID_ROW_HEIGHT = 8;
    const GRID_ROW_GAP = 20;
    const WIDGET_LAYOUT_STORAGE_KEY = 'dashboard.widgetLayout.v1';
    const WIDGET_ORDER_STORAGE_KEY = 'dashboard.widgetOrder.v1';
    const LAYOUT_SETTINGS_STORAGE_KEY = 'dashboard.layoutSettings.v1';
    const DEFAULT_SETTINGS = {
        minWidgetHeight: 120,
        maxWidgetHeightPx: 760,
        minCardWidthPx: 320,
        dragAutoScrollEdgePx: 80,
        dragAutoScrollStepPx: 24
    };

    const state = {
        showStopped: false,
        toolMap: new Map(),
        widgetLayout: loadWidgetLayout(),
        activeResize: null,
        dragSource: null,
        dragArmedCard: null,
        widgetOrder: loadWidgetOrder(),
        dragAutoScrollRaf: 0,
        dragPointer: null,
        settings: loadLayoutSettings()
    };

    const els = {
        container: document.getElementById('tools-container'),
        toggleStopped: document.getElementById('toggle-stopped'),
        settingsBtn: document.getElementById('layout-settings-btn'),
        settingsPopover: document.getElementById('layout-settings-popover'),
        settingMinHeight: document.getElementById('setting-min-height'),
        settingMaxHeight: document.getElementById('setting-max-height'),
        settingMinWidth: document.getElementById('setting-min-width'),
        settingScrollEdge: document.getElementById('setting-scroll-edge'),
        settingScrollStep: document.getElementById('setting-scroll-step'),
        settingsSave: document.getElementById('settings-save'),
        settingsReset: document.getElementById('settings-reset')
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

    function loadLayoutSettings() {
        try {
            const raw = localStorage.getItem(LAYOUT_SETTINGS_STORAGE_KEY);
            if (!raw) return { ...DEFAULT_SETTINGS };
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') return { ...DEFAULT_SETTINGS };
            return {
                minWidgetHeight: Number(parsed.minWidgetHeight) || DEFAULT_SETTINGS.minWidgetHeight,
                maxWidgetHeightPx: Number(parsed.maxWidgetHeightPx) || DEFAULT_SETTINGS.maxWidgetHeightPx,
                minCardWidthPx: Number(parsed.minCardWidthPx) || DEFAULT_SETTINGS.minCardWidthPx,
                dragAutoScrollEdgePx: Number(parsed.dragAutoScrollEdgePx) || DEFAULT_SETTINGS.dragAutoScrollEdgePx,
                dragAutoScrollStepPx: Number(parsed.dragAutoScrollStepPx) || DEFAULT_SETTINGS.dragAutoScrollStepPx
            };
        } catch {
            return { ...DEFAULT_SETTINGS };
        }
    }

    function saveLayoutSettings() {
        localStorage.setItem(LAYOUT_SETTINGS_STORAGE_KEY, JSON.stringify(state.settings));
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

    function getGridMetrics() {
        const styles = getComputedStyle(els.container);
        const columns = styles.gridTemplateColumns.split(/\s+/).filter(Boolean).length || 1;
        const colGap = parseFloat(styles.columnGap || styles.gap || '20') || 20;
        const columnWidth = (els.container.clientWidth - colGap * (columns - 1)) / columns;
        return { columns, colGap, columnWidth };
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

    function syncSettingsInputs() {
        els.settingMinHeight.value = String(state.settings.minWidgetHeight);
        els.settingMaxHeight.value = String(state.settings.maxWidgetHeightPx);
        els.settingMinWidth.value = String(state.settings.minCardWidthPx);
        els.settingScrollEdge.value = String(state.settings.dragAutoScrollEdgePx);
        els.settingScrollStep.value = String(state.settings.dragAutoScrollStepPx);
    }

    function applySettingsFromInputs() {
        const minH = clamp(Number(els.settingMinHeight.value) || DEFAULT_SETTINGS.minWidgetHeight, 80, 1000);
        const maxHRaw = clamp(Number(els.settingMaxHeight.value) || DEFAULT_SETTINGS.maxWidgetHeightPx, 120, 2000);
        const maxH = Math.max(minH, maxHRaw);
        const minW = clamp(Number(els.settingMinWidth.value) || DEFAULT_SETTINGS.minCardWidthPx, 180, 1200);
        const edge = clamp(Number(els.settingScrollEdge.value) || DEFAULT_SETTINGS.dragAutoScrollEdgePx, 20, 300);
        const step = clamp(Number(els.settingScrollStep.value) || DEFAULT_SETTINGS.dragAutoScrollStepPx, 4, 100);

        state.settings = {
            minWidgetHeight: minH,
            maxWidgetHeightPx: maxH,
            minCardWidthPx: minW,
            dragAutoScrollEdgePx: edge,
            dragAutoScrollStepPx: step
        };

        saveLayoutSettings();
        syncSettingsInputs();
        enforceCardSpanConstraints();
        enforceWidgetHeightConstraints();
        resizeAllCards();
    }

    async function loadDashboard() {
        try {
            const resp = await fetch('/tools');
            const data = await resp.json();
            const tools = applySavedOrder(data.tools || []);

            stopWidgetResize();
            els.container.innerHTML = '';
            state.toolMap.clear();

            if (tools.length === 0) {
                const empty = el('div', 'empty-state', 'No tools found.');
                els.container.appendChild(empty);
                return;
            }

            tools.forEach(tool => {
                const card = createToolCard(tool);
                els.container.appendChild(card);
            });

            requestAnimationFrame(resizeAllCards);
            requestAnimationFrame(enforceCardSpanConstraints);
            refreshAllStatuses();

        } catch (e) {
            console.error(e);
        }
    }

    function createToolCard(tool) {
        const card = el('div', `card status-${tool.status || 'stopped'}`);
        const sId = safeId(tool.name);

        card.id = `card-${sId}`;
        card.dataset.name = tool.name;

        const cardBody = el('div', 'card-body');
        const header = el('div', 'tool-header');
        const left = el('div', 'tool-header-left');
        const right = el('div', 'header-right');

        const name = el('span', 'tool-name', tool.name);
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
        btn.setAttribute('aria-label', `Toggle ${tool.name}`);
        btn.textContent = '⏻';
        btn.addEventListener('click', () => statusButtonAction(tool.name));

        const port = el('span', 'port-badge', `:${tool.port}`);

        right.appendChild(btn);
        right.appendChild(port);

        header.appendChild(left);
        header.appendChild(right);
        cardBody.appendChild(header);
        card.appendChild(cardBody);
        card.draggable = true;
        wireCardDnD(card, header);

        if (tool.has_widget) {
            const widgetBox = el('div', 'widget-container');
            widgetBox.id = `widget-box-${sId}`;
            const savedLayout = state.widgetLayout[tool.name] || {};
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

            const resizeHandle = el('button', 'widget-resize-handle');
            resizeHandle.id = `resize-handle-${sId}`;
            resizeHandle.type = 'button';
            resizeHandle.setAttribute('aria-label', `Resize ${tool.name} widget`);
            resizeHandle.addEventListener('pointerdown', event => startWidgetResize(event, tool.name));
            widgetBox.appendChild(resizeHandle);
            card.appendChild(widgetBox);
        }

        state.toolMap.set(tool.name, { card, statusDot, statusText, btn, sId });
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
        const rowSpan = Math.ceil((height + GRID_ROW_GAP) / (GRID_ROW_HEIGHT + GRID_ROW_GAP));
        card.style.gridRowEnd = `span ${rowSpan}`;
    }

    function resizeAllCards() {
        document.querySelectorAll('.card').forEach(resizeCard);
    }

    function wireCardDnD(card, header) {
        header.setAttribute('title', 'Drag to reorder');
        header.addEventListener('pointerdown', () => {
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
            const fromStatusBtn = event.target && event.target.closest('.btn-status');
            if (fromStatusBtn) {
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

    function startWidgetResize(event, name) {
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

            const deltaX = (current.lastX ?? current.startX) - current.startX;
            const desiredWidth = Math.max(200, current.startWidth + deltaX);
            const { columns, colGap, columnWidth } = getGridMetrics();
            const minSpan = getMinCardSpan(columns, colGap, columnWidth);
            const span = clamp(Math.round((desiredWidth + colGap) / (columnWidth + colGap)), minSpan, columns);
            current.card.style.gridColumnEnd = `span ${span}`;
            current.nextColSpan = span;

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
        const { columns, colGap, columnWidth } = getGridMetrics();
        const minSpan = getMinCardSpan(columns, colGap, columnWidth);
        saveWidgetLayout(resize.name, {
            height: Math.round(resize.nextHeight || resize.startHeight),
            colSpan: clamp(Math.round(resize.nextColSpan || resize.startColSpan), minSpan, columns)
        });
        state.activeResize = null;
    }

    function applyFilters() {
        state.toolMap.forEach(({ card }) => {
            const alive = card.dataset.alive === '1';
            const hidden = !state.showStopped && !alive;
            card.classList.toggle('is-hidden', hidden);
        });
        enforceCardSpanConstraints();
        requestAnimationFrame(resizeAllCards);
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
                const resizeHandle = document.getElementById(`resize-handle-${sId}`);
                const alive = !!tool.alive;

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

                if (widgetBox && iframe) {
                    if (alive) {
                        if (!iframe.src) {
                            const widgetHost = window.location.hostname;
                            iframe.src = `${window.location.protocol}//${widgetHost}:${tool.port}/widget`;
                        }
                        widgetBox.style.display = 'block';
                        if (resizeHandle) resizeHandle.style.display = 'block';
                    } else {
                        widgetBox.style.display = 'none';
                        iframe.removeAttribute('src');
                        if (resizeHandle) resizeHandle.style.display = 'none';
                    }
                }

                requestAnimationFrame(() => resizeCard(card));
            });

            applyFilters();

        } catch (e) {
            console.error('Refresh failed', e);
        }
    }

    function syncToggleState() {
        state.showStopped = els.toggleStopped.checked;
        applyFilters();
    }

    els.toggleStopped.addEventListener('change', syncToggleState);
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
    els.settingsBtn.addEventListener('click', () => {
        const open = els.settingsPopover.classList.toggle('is-open');
        if (open) syncSettingsInputs();
    });
    els.settingsSave.addEventListener('click', () => {
        applySettingsFromInputs();
        els.settingsPopover.classList.remove('is-open');
    });
    els.settingsReset.addEventListener('click', () => {
        state.settings = { ...DEFAULT_SETTINGS };
        saveLayoutSettings();
        syncSettingsInputs();
        enforceCardSpanConstraints();
        resizeAllCards();
    });
    document.addEventListener('click', event => {
        if (!els.settingsPopover.classList.contains('is-open')) return;
        const inPopover = event.target && event.target.closest('#layout-settings-popover');
        const inButton = event.target && event.target.closest('#layout-settings-btn');
        if (!inPopover && !inButton) els.settingsPopover.classList.remove('is-open');
    });
    window.addEventListener('resize', () => {
        enforceCardSpanConstraints();
        enforceWidgetHeightConstraints();
        requestAnimationFrame(resizeAllCards);
    });

    syncSettingsInputs();
    syncToggleState();
    loadDashboard();
    setInterval(refreshAllStatuses, REFRESH_RATE);
