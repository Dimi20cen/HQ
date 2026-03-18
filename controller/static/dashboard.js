    const REFRESH_RATE = 2000;
    const PROJECT_REFRESH_RATE = 45000;
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
        hosts: [],
        projects: [],
        openProjectConfigs: new Set(),
        openProjectRows: new Set(),
        nextProjectDraftId: 1,
        widgetLayout: loadWidgetLayout(),
        activeResize: null,
        dragSource: null,
        dragArmedCard: null,
        widgetOrder: loadWidgetOrder(),
        hiddenTools: loadHiddenTools(),
        hiddenToolsMenuOpen: false,
        reorderModeOpen: false,
        activePanelId: null,
        lastPanelTrigger: null,
        appsRowMenuOpenFor: null,
        dragAutoScrollRaf: 0,
        dragPointer: null,
        settings: { ...DEFAULT_SETTINGS },
        statusRefreshPromise: null
    };
    const CATEGORY_ORDER = { display: 0, hybrid: 1, background: 2 };

    const els = {
        cmdStrip: document.getElementById('cmd-strip'),
        reorderModeBtn: document.getElementById('reorder-mode-btn'),
        reorderPanel: document.getElementById('reorder-panel'),
        hiddenToolsMenu: document.getElementById('hidden-tools-menu'),
        container: document.getElementById('tools-container'),
        hostsList: document.getElementById('hosts-list'),
        hostsEmpty: document.getElementById('hosts-empty'),
        hostsFeedback: document.getElementById('hosts-feedback'),
        projectsList: document.getElementById('projects-list'),
        projectsEmpty: document.getElementById('projects-empty'),
        projectsFeedback: document.getElementById('projects-feedback'),
        projectsResult: document.getElementById('projects-result'),
        projectAddBtn: document.getElementById('project-add-btn'),
        projectExportBtn: document.getElementById('project-export-btn'),
        projectPublishBtn: document.getElementById('project-publish-btn'),
        panelBackdrop: document.getElementById('panel-backdrop'),
        panelProjects: document.getElementById('panel-projects'),
        panelProjectsClose: document.getElementById('panel-projects-close'),
        panelHosts: document.getElementById('panel-hosts'),
        panelHostsClose: document.getElementById('panel-hosts-close'),
        pillTools: document.getElementById('pill-tools'),
        pillToolsCount: document.getElementById('pill-tools-count'),
        pillProjects: document.getElementById('pill-projects'),
        pillProjectsCount: document.getElementById('pill-projects-count'),
        pillHosts: document.getElementById('pill-hosts'),
        pillHostsCount: document.getElementById('pill-hosts-count'),
        mainStage: document.getElementById('main-stage')
    };

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    async function readJsonResponse(resp) {
        const raw = await resp.text();
        if (!raw) return {};
        try {
            return JSON.parse(raw);
        } catch {
            return {
                detail: raw,
                stderr: raw
            };
        }
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

    function emptyProjectDraft() {
        return {
            draft_key: `draft-${state.nextProjectDraftId++}`,
            slug: '',
            title: '',
            public_summary: '',
            public_mode: 'hidden',
            primary_url: '',
            repo_url: '',
            sort_order: (state.projects.length + 1) * 10,
            linked_tools: [],
            depends_on: [],
            private_url: '',
            deployment_host: '',
            deployment_location: '',
            runtime_path: '',
            health_public_url: '',
            health_private_url: '',
            deploy_command: '',
            start_command: '',
            restart_command: '',
            stop_command: '',
            logs_command: '',
            health_snapshot: null,
            dependency_snapshot: { summary: 'none', items: [] },
            ops_summary: 'unconfigured',
            action_result: null,
            updated_at: ''
        };
    }

    function normalizeProjectRecord(rawProject) {
        return {
            draft_key: String(rawProject?.draft_key || '').trim(),
            slug: String(rawProject?.slug || '').trim(),
            title: String(rawProject?.title || '').trim(),
            public_summary: String(rawProject?.public_summary || '').trim(),
            public_mode: String(rawProject?.public_mode || 'hidden').trim() || 'hidden',
            primary_url: String(rawProject?.primary_url || '').trim(),
            repo_url: String(rawProject?.repo_url || '').trim(),
            sort_order: Number.isFinite(Number(rawProject?.sort_order)) ? Number(rawProject.sort_order) : 0,
            linked_tools: Array.isArray(rawProject?.linked_tools) ? rawProject.linked_tools : [],
            depends_on: Array.isArray(rawProject?.depends_on) ? rawProject.depends_on : [],
            private_url: String(rawProject?.private_url || '').trim(),
            deployment_host: String(rawProject?.deployment_host || '').trim(),
            deployment_location: String(rawProject?.deployment_location || '').trim(),
            runtime_path: String(rawProject?.runtime_path || '').trim(),
            health_public_url: String(rawProject?.health_public_url || '').trim(),
            health_private_url: String(rawProject?.health_private_url || '').trim(),
            deploy_command: String(rawProject?.deploy_command || '').trim(),
            start_command: String(rawProject?.start_command || '').trim(),
            restart_command: String(rawProject?.restart_command || '').trim(),
            stop_command: String(rawProject?.stop_command || '').trim(),
            logs_command: String(rawProject?.logs_command || '').trim(),
            host: rawProject?.host || null,
            host_snapshot: rawProject?.host_snapshot || null,
            health_snapshot: rawProject?.health_snapshot || null,
            dependency_snapshot: rawProject?.dependency_snapshot || { summary: 'none', items: [] },
            ops_summary: String(rawProject?.ops_summary || rawProject?.health_snapshot?.summary || 'unconfigured'),
            action_result: rawProject?.action_result || null,
            updated_at: String(rawProject?.updated_at || '').trim()
        };
    }

    function normalizeHostRecord(rawHost) {
        return {
            slug: String(rawHost?.slug || '').trim(),
            title: String(rawHost?.title || rawHost?.slug || '').trim(),
            transport: String(rawHost?.transport || 'none').trim() || 'none',
            runner_url: String(rawHost?.runner_url || '').trim(),
            runner_socket_path: String(rawHost?.runner_socket_path || '').trim(),
            token_env_var: String(rawHost?.token_env_var || '').trim(),
            location: String(rawHost?.location || '').trim(),
            notes: String(rawHost?.notes || '').trim(),
            runner_snapshot: rawHost?.runner_snapshot || null,
            updated_at: String(rawHost?.updated_at || '').trim()
        };
    }

    function getHostRecord(slug) {
        const target = String(slug || '').trim();
        if (!target) return null;
        return state.hosts.find(host => host.slug === target) || null;
    }

    function setProjectsFeedback(message, tone = '') {
        if (!els.projectsFeedback) return;
        els.projectsFeedback.textContent = message || '';
        els.projectsFeedback.classList.remove('is-error', 'is-success');
        if (tone === 'error') els.projectsFeedback.classList.add('is-error');
        if (tone === 'success') els.projectsFeedback.classList.add('is-success');
    }

    function renderProjectsResult(result, tone = 'success') {
        if (!els.projectsResult) return;
        if (!result) {
            els.projectsResult.hidden = true;
            els.projectsResult.innerHTML = '';
            return;
        }

        els.projectsResult.hidden = false;
        els.projectsResult.innerHTML = '';

        const panel = el(
            'div',
            `project-action-result ${tone === 'error' ? 'is-error' : 'is-success'}`
        );
        const header = el('div', 'project-action-result-header');
        header.appendChild(
            el(
                'div',
                'project-action-result-title',
                result.no_changes ? 'Portfolio already up to date' : 'Portfolio publish result'
            )
        );
        if (result.commit_sha) {
            header.appendChild(el('div', 'project-action-result-time', result.commit_sha.slice(0, 12)));
        }
        panel.appendChild(header);

        const body = el('div', 'project-action-result-body');
        [
            result.detail,
            result.repo_path ? `Repo: ${result.repo_path}` : '',
            result.branch ? `Branch: ${result.branch}` : '',
            result.export_relpath ? `File: ${result.export_relpath}` : '',
            result.origin_url ? `Remote: ${result.origin_url}` : '',
            result.hq_export_path ? `HQ export: ${result.hq_export_path}` : '',
            result.commit_message ? `Commit: ${result.commit_message}` : '',
            result.commit_sha ? `Commit SHA: ${result.commit_sha}` : ''
        ]
            .filter(Boolean)
            .forEach(line => body.appendChild(el('div', 'project-action-result-line', line)));

        const stdout = String(result.stdout || '').trim();
        const stderr = String(result.stderr || '').trim();
        if (stdout) {
            const block = el('div', 'project-action-result-block');
            block.appendChild(el('span', 'project-action-result-block-label', 'Stdout'));
            const pre = document.createElement('pre');
            pre.textContent = stdout;
            block.appendChild(pre);
            body.appendChild(block);
        }
        if (stderr) {
            const block = el('div', 'project-action-result-block');
            block.appendChild(el('span', 'project-action-result-block-label', 'Stderr'));
            const pre = document.createElement('pre');
            pre.textContent = stderr;
            block.appendChild(pre);
            body.appendChild(block);
        }

        panel.appendChild(body);
        els.projectsResult.appendChild(panel);
    }

    function hasDirtyProjectEditors() {
        return !!document.querySelector('.project-dirty-badge.is-visible');
    }

    function projectModeLabel(mode) {
        if (mode === 'demo') return 'Demo';
        if (mode === 'full') return 'Full';
        if (mode === 'source') return 'Source';
        return 'Hidden';
    }

    function projectHealthLabel(summary) {
        if (summary === 'healthy') return 'Healthy';
        if (summary === 'degraded') return 'Degraded';
        if (summary === 'down') return 'Down';
        if (summary === 'unknown') return 'Checking';
        if (summary === 'none') return 'No deps';
        return 'Unconfigured';
    }

    function projectHealthClass(summary) {
        if (summary === 'healthy') return 'is-healthy';
        if (summary === 'degraded') return 'is-degraded';
        if (summary === 'down') return 'is-down';
        if (summary === 'unknown') return 'is-unknown';
        return 'is-unconfigured';
    }

    function projectScanFacts(project) {
        return [
            projectModeLabel(project.public_mode),
            project.deployment_host || 'No host',
            formatCheckedAt(project.health_snapshot?.checked_at)
        ];
    }

    function setHostsFeedback(message, tone = '') {
        if (!els.hostsFeedback) return;
        els.hostsFeedback.textContent = message || '';
        els.hostsFeedback.classList.remove('is-error', 'is-success');
        if (tone === 'error') els.hostsFeedback.classList.add('is-error');
        if (tone === 'success') els.hostsFeedback.classList.add('is-success');
    }

    function runnerHealthLine(host) {
        const snapshot = host?.runner_snapshot;
        if (!snapshot) return 'Runner: not checked yet';
        const detail = String(snapshot.detail || '').trim();
        if (snapshot.status === 'unconfigured') return 'Runner: unconfigured';
        if (snapshot.status === 'unknown') return 'Runner: checking';
        if (snapshot.status === 'healthy') return `Runner: healthy${detail ? ` (${detail})` : ''}`;
        return `Runner: down${detail ? ` (${detail})` : ''}`;
    }

    // ── Panel management ────────────────────────────────────────────────────

    function getActivePanelElement() {
        if (state.activePanelId === 'projects') return els.panelProjects;
        if (state.activePanelId === 'hosts') return els.panelHosts;
        return null;
    }

    function getPanelFocusableElements(panelEl) {
        if (!panelEl) return [];
        return Array.from(panelEl.querySelectorAll(
            'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )).filter(node => !node.hidden && node.offsetParent !== null);
    }

    function focusPanelPrimaryControl(panelEl) {
        const focusables = getPanelFocusableElements(panelEl);
        const preferred = focusables.find(node => node.classList.contains('side-panel-close'));
        (preferred || focusables[0] || panelEl)?.focus();
    }

    function setPanelModalState(isOpen) {
        document.body.classList.toggle('panel-modal-open', !!isOpen);
        [els.cmdStrip, els.mainStage].forEach(node => {
            if (!node) return;
            node.toggleAttribute('inert', !!isOpen);
            node.setAttribute('aria-hidden', isOpen ? 'true' : 'false');
        });
    }

    function setPanelVisibility(panelEl, isOpen) {
        if (!panelEl) return;
        panelEl.hidden = !isOpen;
        panelEl.toggleAttribute('inert', !isOpen);
        panelEl.classList.toggle('is-open', !!isOpen);
        panelEl.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
    }

    function openPanel(id, triggerEl = null) {
        const panelEl = id === 'projects' ? els.panelProjects : els.panelHosts;
        const otherEl = id === 'projects' ? els.panelHosts : els.panelProjects;
        if (!panelEl) return;
        if (state.activePanelId === id) {
            closePanel();
            return;
        }
        closeAllToolMenus();
        closeAppsRowMenus();
        setHiddenToolsMenuOpen(false);
        setReorderModeOpen(false);
        if (otherEl) {
            setPanelVisibility(otherEl, false);
        }
        state.lastPanelTrigger = triggerEl || document.activeElement || null;
        state.activePanelId = id;
        setPanelVisibility(panelEl, true);
        if (els.panelBackdrop) els.panelBackdrop.classList.add('is-open');
        setPanelModalState(true);
        updatePillActiveStates();
        requestAnimationFrame(() => focusPanelPrimaryControl(panelEl));
    }

    function closePanel() {
        if (!state.activePanelId) return;
        const panelEl = getActivePanelElement();
        if (panelEl) {
            setPanelVisibility(panelEl, false);
        }
        if (els.panelBackdrop) els.panelBackdrop.classList.remove('is-open');
        state.activePanelId = null;
        setPanelModalState(false);
        updatePillActiveStates();
        if (state.lastPanelTrigger && typeof state.lastPanelTrigger.focus === 'function' && state.lastPanelTrigger.isConnected) {
            state.lastPanelTrigger.focus();
        }
        state.lastPanelTrigger = null;
    }

    function updatePillActiveStates() {
        if (els.pillProjects) {
            const active = state.activePanelId === 'projects';
            els.pillProjects.classList.toggle('is-active', active);
            els.pillProjects.setAttribute('aria-expanded', String(active));
        }
        if (els.pillHosts) {
            const active = state.activePanelId === 'hosts';
            els.pillHosts.classList.toggle('is-active', active);
            els.pillHosts.setAttribute('aria-expanded', String(active));
        }
    }

    function aggregateStatusHealth(statuses) {
        if (!statuses.length) return 'unknown';
        if (statuses.every(s => s === 'healthy')) return 'healthy';
        if (statuses.some(s => s === 'down')) return 'down';
        if (statuses.some(s => s === 'degraded')) return 'degraded';
        if (statuses.every(s => s === 'unconfigured')) return 'unconfigured';
        return 'unknown';
    }

    function pillHealthClass(health) {
        if (health === 'healthy') return ' pill-healthy';
        if (health === 'down') return ' pill-stopped';
        if (health === 'degraded') return ' pill-degraded';
        return '';
    }

    function updateStatusPills() {
        const toolsList = Array.from(state.toolMap.values());
        const runningTools = toolsList.filter(t => t.alive).length;
        const totalTools = toolsList.length;
        if (els.pillToolsCount) {
            els.pillToolsCount.textContent = totalTools > 0 ? `${runningTools}/${totalTools}` : '0';
        }
        if (els.pillTools) {
            const healthy = totalTools > 0 && runningTools === totalTools;
            const partial = runningTools > 0 && runningTools < totalTools;
            els.pillTools.className = 'cmd-pill cmd-pill-action' + (
                healthy ? ' pill-healthy' :
                partial ? ' pill-degraded' :
                totalTools > 0 ? ' pill-stopped' : ''
            );
        }

        const projectsCount = state.projects.length;
        if (els.pillProjectsCount) {
            els.pillProjectsCount.textContent = String(projectsCount);
        }
        const projStatuses = state.projects.map(p => p.ops_summary || 'unknown');
        const projHealth = aggregateStatusHealth(projStatuses);
        if (els.pillProjects) {
            els.pillProjects.className = 'cmd-pill cmd-pill-action' + pillHealthClass(projHealth) +
                (state.activePanelId === 'projects' ? ' is-active' : '');
        }

        const hostsCount = state.hosts.length;
        if (els.pillHostsCount) {
            els.pillHostsCount.textContent = String(hostsCount);
        }
        const hostStatuses = state.hosts.map(h => h.runner_snapshot?.status || 'unknown');
        const hostsHealth = aggregateStatusHealth(hostStatuses);
        if (els.pillHosts) {
            els.pillHosts.className = 'cmd-pill cmd-pill-action' + pillHealthClass(hostsHealth) +
                (state.activePanelId === 'hosts' ? ' is-active' : '');
        }
    }

    // ── Compact project rows (panel-first) ──────────────────────────────────

    function captureOpenProjectRows() {
        if (!els.projectsList) return;
        const openKeys = new Set();
        els.projectsList.querySelectorAll('.project-row.is-expanded').forEach(row => {
            const key = row.dataset.rowKey;
            if (key) openKeys.add(key);
        });
        state.openProjectRows = openKeys;
    }

    function createProjectRow(project) {
        const wrapper = document.createElement('div');
        wrapper.className = 'project-row';
        const key = projectEditorKey(project);
        wrapper.dataset.rowKey = key;

        const rowBtn = document.createElement('button');
        rowBtn.className = 'project-row-header';
        rowBtn.type = 'button';

        const heading = el('span', 'project-row-heading');
        const titleSpan = el('span', 'project-row-title', project.title || '—');
        const summary = el('span', 'project-row-summary');
        projectScanFacts(project).forEach(fact => {
            summary.appendChild(el('span', 'project-row-fact', fact));
        });
        heading.appendChild(titleSpan);
        heading.appendChild(summary);
        const healthChip = el(
            'span',
            `project-health-chip ${projectHealthClass(project.ops_summary)}`,
            projectHealthLabel(project.ops_summary)
        );
        const chevron = el('span', 'project-row-chevron', '›');
        rowBtn.appendChild(heading);
        rowBtn.appendChild(healthChip);
        rowBtn.appendChild(chevron);

        const detail = document.createElement('div');
        detail.className = 'project-row-detail';

        const isExpanded = state.openProjectRows.has(key);
        if (isExpanded) {
            wrapper.classList.add('is-expanded');
            rowBtn.setAttribute('aria-expanded', 'true');
            detail.appendChild(createProjectEditor(project));
        } else {
            rowBtn.setAttribute('aria-expanded', 'false');
        }

        wrapper.appendChild(rowBtn);
        wrapper.appendChild(detail);

        rowBtn.addEventListener('click', () => {
            const nowExpanded = !wrapper.classList.contains('is-expanded');
            wrapper.classList.toggle('is-expanded', nowExpanded);
            rowBtn.setAttribute('aria-expanded', String(nowExpanded));
            if (nowExpanded) {
                state.openProjectRows.add(key);
            } else {
                state.openProjectRows.delete(key);
            }
            if (nowExpanded && !detail.firstChild) {
                detail.appendChild(createProjectEditor(project));
            }
        });

        return wrapper;
    }

    function renderHosts() {
        if (!els.hostsList || !els.hostsEmpty) return;
        els.hostsList.innerHTML = '';
        const hosts = [...state.hosts].sort((a, b) => a.title.localeCompare(b.title));
        els.hostsEmpty.hidden = hosts.length > 0;
        hosts.forEach(host => {
            const card = el('article', 'host-card');
            const header = el('div', 'host-card-header');
            const titleWrap = el('div', 'host-card-title');
            titleWrap.appendChild(el('strong', '', host.title || host.slug));
            titleWrap.appendChild(el('span', '', host.slug ? `/${host.slug}` : 'Unknown host'));
            header.appendChild(titleWrap);
            header.appendChild(
                el(
                    'span',
                    `project-health-chip ${projectHealthClass(host.runner_snapshot?.status)}`,
                    projectHealthLabel(host.runner_snapshot?.status)
                )
            );
            card.appendChild(header);

            if (host.notes) {
                card.appendChild(el('p', 'host-card-copy', host.notes));
            }

            const meta = el('div', 'host-card-meta');
            [
                host.transport ? `Transport: ${host.transport}` : '',
                host.location ? `Where: ${host.location}` : '',
                host.runner_snapshot?.endpoint ? `Endpoint: ${host.runner_snapshot.endpoint}` : ''
            ].filter(Boolean).forEach(line => meta.appendChild(el('span', 'host-card-fact', line)));
            if (meta.childNodes.length) {
                card.appendChild(meta);
            }

            const health = el('div', 'host-card-health');
            health.appendChild(el('div', 'host-card-health-line', runnerHealthLine(host)));
            health.appendChild(
                el(
                    'div',
                    'host-card-health-line',
                    `Last checked: ${formatCheckedAt(host.runner_snapshot?.checked_at)}`
                )
            );
            card.appendChild(health);
            els.hostsList.appendChild(card);
        });
        updateStatusPills();
    }

    function projectSurfaceHealthLine(label, snapshot) {
        if (!snapshot) return `${label}: not checked yet`;
        const check = snapshot.checks?.[label];
        if (!check) return `${label}: unavailable`;
        if (check.status === 'unconfigured') return `${label}: unconfigured`;
        if (check.status === 'unknown') return `${label}: not checked yet`;
        if (check.status === 'healthy') return `${label}: healthy (${check.detail})`;
        return `${label}: down${check.detail ? ` (${check.detail})` : ''}`;
    }

    function projectActionLabel(action) {
        if (action === 'open') return 'Open';
        if (action === 'deploy') return 'Deploy';
        if (action === 'logs') return 'Logs';
        if (action === 'restart') return 'Restart';
        if (action === 'start') return 'Start';
        return 'Stop';
    }

    function projectFeedbackMessage(project) {
        if (project.action_result?.ok) {
            return `${projectActionLabel(project.action_result.action)} finished successfully.`;
        }
        if (project.action_result && !project.action_result.ok) {
            return project.action_result.detail || `${projectActionLabel(project.action_result.action)} failed.`;
        }
        return '';
    }

    function renderProjects() {
        if (!els.projectsList || !els.projectsEmpty) return;
        captureOpenProjectConfigs();
        captureOpenProjectRows();
        els.projectsList.innerHTML = '';
        const projects = [...state.projects].sort((a, b) => {
            if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
            return a.title.localeCompare(b.title);
        });
        els.projectsEmpty.hidden = projects.length > 0;
        projects.forEach(project => {
            els.projectsList.appendChild(createProjectRow(project));
        });
        updateStatusPills();
    }

    function projectEditorKey(project) {
        return String(project?.slug || project?.draft_key || '').trim();
    }

    function captureOpenProjectConfigs() {
        if (!els.projectsList) return;
        const openKeys = new Set();
        els.projectsList.querySelectorAll('.project-section-details').forEach(details => {
            if (!details.open) return;
            const key = String(details.dataset.projectKey || '').trim();
            if (key) openKeys.add(key);
        });
        state.openProjectConfigs = openKeys;
    }

    function createProjectField(labelText, name, type = 'text', value = '', full = false) {
        const field = el('div', `project-field${full ? ' is-full' : ''}`);
        const label = el('label', '', labelText);
        label.htmlFor = name;
        let control;
        if (type === 'textarea') {
            control = el('textarea');
            control.value = value;
        } else if (type === 'select') {
            control = el('select');
        } else {
            control = el('input');
            control.type = type;
            control.value = value;
        }
        control.id = name;
        control.name = name;
        field.appendChild(label);
        field.appendChild(control);
        return { field, control };
    }

    function createProjectSection(projectKey, sectionId, title, defaultOpen = false) {
        const details = document.createElement('details');
        details.className = 'project-section-details';
        details.dataset.projectKey = `${projectKey}:${sectionId}`;
        details.open = state.openProjectConfigs.has(`${projectKey}:${sectionId}`) || defaultOpen;
        details.addEventListener('toggle', () => {
            if (details.open) {
                state.openProjectConfigs.add(`${projectKey}:${sectionId}`);
            } else {
                state.openProjectConfigs.delete(`${projectKey}:${sectionId}`);
            }
        });
        const summary = el('summary', 'project-section-summary');
        summary.appendChild(el('span', 'project-section-title', title));
        details.appendChild(summary);
        const section = el('section', 'project-section');
        const grid = el('div', 'project-editor-grid');
        section.appendChild(grid);
        details.appendChild(section);
        return { details, grid };
    }

    function normalizeProjectPayload(payload) {
        return {
            slug: String(payload?.slug || '').trim(),
            title: String(payload?.title || '').trim(),
            public_summary: String(payload?.public_summary || '').trim(),
            public_mode: String(payload?.public_mode || 'hidden').trim() || 'hidden',
            sort_order: String(payload?.sort_order ?? '').trim(),
            primary_url: String(payload?.primary_url || '').trim(),
            repo_url: String(payload?.repo_url || '').trim(),
            depends_on: Array.isArray(payload?.depends_on)
                ? payload.depends_on.map(item => String(item || '').trim()).filter(Boolean)
                : [],
            private_url: String(payload?.private_url || '').trim(),
            deployment_host: String(payload?.deployment_host || '').trim(),
            deployment_location: String(payload?.deployment_location || '').trim(),
            runtime_path: String(payload?.runtime_path || '').trim(),
            health_public_url: String(payload?.health_public_url || '').trim(),
            health_private_url: String(payload?.health_private_url || '').trim(),
            deploy_command: String(payload?.deploy_command || '').trim(),
            start_command: String(payload?.start_command || '').trim(),
            restart_command: String(payload?.restart_command || '').trim(),
            stop_command: String(payload?.stop_command || '').trim(),
            logs_command: String(payload?.logs_command || '').trim()
        };
    }

    function projectOpenUrl(payload) {
        const privateUrl = String(payload?.private_url || '').trim();
        if (privateUrl) return privateUrl;
        return String(payload?.primary_url || '').trim();
    }

    function formatCheckedAt(value) {
        if (!value) return 'not checked yet';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour12: false,
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function dependencyLine(project) {
        const items = Array.isArray(project.dependency_snapshot?.items) ? project.dependency_snapshot.items : [];
        if (!items.length) return 'No declared dependencies';
        return items.map(item => `${item.title} (${projectHealthLabel(item.status).toLowerCase()})`).join(' • ');
    }

    function projectStatusSummary(project, hostSummary, hostSnapshot) {
        return [
            `Project ${projectHealthLabel(project.health_snapshot?.summary)}`,
            project.deployment_host
                ? `${project.deployment_host} runner ${projectHealthLabel(hostSummary)}${hostSnapshot?.detail ? ` (${hostSnapshot.detail})` : ''}`
                : 'No deployment host configured',
            `Dependencies: ${dependencyLine(project)}`,
            `Last checked ${formatCheckedAt(project.health_snapshot?.checked_at)}`
        ];
    }

    function createProjectEditor(project) {
        const article = el('article', 'project-editor project-card');
        article.dataset.slug = project.slug;
        const fieldKey = projectEditorKey(project) || `draft-${state.nextProjectDraftId++}`;
        const dirtyBadge = el('span', 'project-dirty-badge', 'Save required');
        const hostRecord = project.host || getHostRecord(project.deployment_host);

        const slugField = createProjectField('Slug', `project-slug-${fieldKey}`, 'text', project.slug);
        slugField.control.disabled = !!project.slug;
        const titleField = createProjectField('Title', `project-title-${fieldKey}`, 'text', project.title);
        const summaryField = createProjectField('Public Summary', `project-summary-${fieldKey}`, 'textarea', project.public_summary, true);
        const modeField = createProjectField('Public Mode', `project-mode-${fieldKey}`, 'select', '', false);
        ['hidden', 'demo', 'full', 'source'].forEach(mode => {
            const option = document.createElement('option');
            option.value = mode;
            option.textContent = projectModeLabel(mode);
            option.selected = project.public_mode === mode;
            modeField.control.appendChild(option);
        });
        const sortField = createProjectField('Sort Order', `project-order-${fieldKey}`, 'number', String(project.sort_order));
        const primaryField = createProjectField('Primary URL', `project-primary-${fieldKey}`, 'url', project.primary_url, true);
        const repoField = createProjectField('Repo URL', `project-repo-${fieldKey}`, 'url', project.repo_url);
        const privateField = createProjectField('Private URL', `project-private-${fieldKey}`, 'url', project.private_url, true);
        const hostField = createProjectField('Deployment Host', `project-host-${fieldKey}`, 'select', '', false);
        const hostOptions = [{ value: '', label: 'Select host' }];
        state.hosts.forEach(host => {
            hostOptions.push({ value: host.slug, label: host.title || host.slug });
        });
        if (project.deployment_host && !hostOptions.some(option => option.value === project.deployment_host)) {
            hostOptions.push({ value: project.deployment_host, label: project.deployment_host });
        }
        hostOptions.forEach(optionConfig => {
            const option = document.createElement('option');
            option.value = optionConfig.value;
            option.textContent = optionConfig.label;
            option.selected = project.deployment_host === optionConfig.value;
            hostField.control.appendChild(option);
        });
        const locationField = createProjectField('Deployment Location', `project-location-${fieldKey}`, 'text', project.deployment_location);
        const runtimeField = createProjectField('Runtime Path', `project-runtime-${fieldKey}`, 'text', project.runtime_path, true);
        const healthPublicField = createProjectField('Public Health URL', `project-health-public-${fieldKey}`, 'url', project.health_public_url, true);
        const healthPrivateField = createProjectField('Private Health URL', `project-health-private-${fieldKey}`, 'url', project.health_private_url, true);
        const deployField = createProjectField('Deploy Command', `project-deploy-${fieldKey}`, 'text', project.deploy_command, true);
        const startField = createProjectField('Start Command', `project-start-${fieldKey}`, 'text', project.start_command, true);
        const restartField = createProjectField('Restart Command', `project-restart-${fieldKey}`, 'text', project.restart_command, true);
        const stopField = createProjectField('Stop Command', `project-stop-${fieldKey}`, 'text', project.stop_command, true);
        const logsField = createProjectField('Logs Command', `project-logs-${fieldKey}`, 'text', project.logs_command, true);
        const dependsOnField = createProjectField(
            'Dependencies',
            `project-depends-on-${fieldKey}`,
            'text',
            (project.depends_on || []).join(', '),
            true
        );
        const currentPayload = () => ({
            slug: slugField.control.value,
            title: titleField.control.value,
            public_summary: summaryField.control.value,
            public_mode: modeField.control.value,
            sort_order: sortField.control.value,
            primary_url: primaryField.control.value,
            repo_url: repoField.control.value,
            linked_tools: project.linked_tools || [],
            depends_on: dependsOnField.control.value
                .split(',')
                .map(value => value.trim())
                .filter(Boolean),
            private_url: privateField.control.value,
            deployment_host: hostField.control.value,
            deployment_location: locationField.control.value,
            runtime_path: runtimeField.control.value,
            health_public_url: healthPublicField.control.value,
            health_private_url: healthPrivateField.control.value,
            deploy_command: deployField.control.value,
            start_command: startField.control.value,
            restart_command: restartField.control.value,
            stop_command: stopField.control.value,
            logs_command: logsField.control.value
        });

        const hostSnapshot = project.host_snapshot || hostRecord?.runner_snapshot || null;
        const hostSummary = hostSnapshot?.status || (project.deployment_host ? 'unknown' : 'unconfigured');
        const statusPanel = el('div', 'project-status-panel');
        const statusChips = el('div', 'project-status-chips');
        statusChips.appendChild(
            el(
                'span',
                `project-health-chip ${projectHealthClass(project.ops_summary)}`,
                projectHealthLabel(project.ops_summary)
            )
        );
        statusChips.appendChild(
            el(
                'span',
                `project-health-chip ${projectHealthClass(hostSummary)}`,
                project.deployment_host ? `Runner ${projectHealthLabel(hostSummary)}` : 'Runner Unconfigured'
            )
        );
        statusChips.appendChild(
            el(
                'span',
                `project-health-chip ${projectHealthClass(project.dependency_snapshot?.summary)}`,
                `Deps ${projectHealthLabel(project.dependency_snapshot?.summary)}`
            )
        );
        statusPanel.appendChild(statusChips);
        if (project.public_summary) {
            statusPanel.appendChild(el('p', 'project-card-copy', project.public_summary));
        }
        const statusList = el('div', 'project-status-list');
        projectStatusSummary(project, hostSummary, hostSnapshot).forEach(line => {
            statusList.appendChild(el('div', 'project-status-line', line));
        });
        if (project.health_public_url) {
            statusList.appendChild(el('div', 'project-status-line', projectSurfaceHealthLine('public', project.health_snapshot)));
        }
        if (project.health_private_url) {
            statusList.appendChild(el('div', 'project-status-line', projectSurfaceHealthLine('private', project.health_snapshot)));
        }
        statusPanel.appendChild(statusList);
        article.appendChild(statusPanel);

        const actionBar = el('div', 'project-action-bar');
        const openBtn = el('button', 'project-action-btn project-action-btn-primary', 'Open');
        openBtn.type = 'button';
        openBtn.disabled = !projectOpenUrl(currentPayload());
        openBtn.addEventListener('click', () => {
            const target = projectOpenUrl(currentPayload());
            if (!target) return;
            window.open(target, '_blank', 'noopener,noreferrer');
        });
        actionBar.appendChild(openBtn);

        const healthBtn = el('button', 'project-action-btn', 'Check Health');
        healthBtn.type = 'button';
        healthBtn.disabled = !project.slug || (!healthPublicField.control.value.trim() && !healthPrivateField.control.value.trim());
        healthBtn.addEventListener('click', async () => {
            await runProjectHealthCheck(project.slug, currentPayload());
        });
        actionBar.appendChild(healthBtn);

        ['deploy', 'restart', 'logs'].forEach(action => {
            const button = el('button', 'project-action-btn', projectActionLabel(action));
            button.type = 'button';
            const field = ({
                deploy: deployField,
                restart: restartField,
                logs: logsField
            })[action];
            button.disabled = !project.slug || !field.control.value.trim();
            button.addEventListener('click', async () => {
                await runProjectAction(project.slug, action, currentPayload());
            });
            actionBar.appendChild(button);
        });
        article.appendChild(actionBar);

        const actionFeedback = projectFeedbackMessage(project);
        if (actionFeedback) {
            article.appendChild(
                el(
                    'div',
                    `project-action-feedback${project.action_result?.ok ? ' is-success' : ' is-error'}`,
                    actionFeedback
                )
            );
        }

        if (project.action_result) {
            const panel = el(
                'div',
                `project-action-result${project.action_result.ok ? ' is-success' : ' is-error'}`
            );
            const panelHeader = el('div', 'project-action-result-header');
            panelHeader.appendChild(
                el(
                    'div',
                    'project-action-result-title',
                    `${projectActionLabel(project.action_result.action)} ${project.action_result.ok ? 'succeeded' : 'failed'}`
                )
            );
            if (project.action_result.ran_at) {
                panelHeader.appendChild(
                    el('div', 'project-action-result-time', project.action_result.ran_at)
                );
            }
            panel.appendChild(panelHeader);

            const panelBody = el('div', 'project-action-result-body');
            panelBody.appendChild(
                el(
                    'div',
                    'project-action-result-line',
                    project.action_result.detail || ''
                )
            );
            if (project.action_result.command) {
                panelBody.appendChild(
                    el(
                        'div',
                        'project-action-result-line',
                        `Command: ${project.action_result.command}`
                    )
                );
            }
            if (project.action_result.host_slug) {
                panelBody.appendChild(
                    el(
                        'div',
                        'project-action-result-line',
                        `Host: ${project.action_result.host_slug}${project.action_result.runner_transport ? ` via ${project.action_result.runner_transport}` : ''}`
                    )
                );
            }
            if (project.action_result.cwd) {
                panelBody.appendChild(
                    el(
                        'div',
                        'project-action-result-line',
                        `Working dir: ${project.action_result.cwd}`
                    )
                );
            }
            const stdout = String(project.action_result.stdout || '').trim();
            const stderr = String(project.action_result.stderr || '').trim();
            if (stdout) {
                const block = el('div', 'project-action-result-block');
                block.appendChild(el('span', 'project-action-result-block-label', 'Stdout'));
                const pre = document.createElement('pre');
                pre.textContent = stdout;
                block.appendChild(pre);
                panelBody.appendChild(block);
            }
            if (stderr) {
                const block = el('div', 'project-action-result-block');
                block.appendChild(el('span', 'project-action-result-block-label', 'Stderr'));
                const pre = document.createElement('pre');
                pre.textContent = stderr;
                block.appendChild(pre);
                panelBody.appendChild(block);
            }
            panel.appendChild(panelBody);
            article.appendChild(panel);
        }

        const configBody = el('div', 'project-config-body');

        const publicSection = createProjectSection(fieldKey, 'public', 'Public', false);
        [
            slugField.field,
            titleField.field,
            summaryField.field,
            modeField.field,
            sortField.field,
            primaryField.field,
            repoField.field
        ].forEach(node => publicSection.grid.appendChild(node));
        configBody.appendChild(publicSection.details);

        const runtimeSection = createProjectSection(fieldKey, 'runtime', 'Runtime', false);
        [
            privateField.field,
            hostField.field,
            locationField.field,
            runtimeField.field,
            dependsOnField.field
        ].forEach(node => runtimeSection.grid.appendChild(node));
        configBody.appendChild(runtimeSection.details);

        const healthSection = createProjectSection(fieldKey, 'health', 'Health', false);
        [
            healthPublicField.field,
            healthPrivateField.field
        ].forEach(node => healthSection.grid.appendChild(node));
        configBody.appendChild(healthSection.details);

        const actionsSection = createProjectSection(fieldKey, 'actions', 'Actions', false);
        [
            deployField.field,
            startField.field,
            restartField.field,
            stopField.field,
            logsField.field
        ].forEach(node => actionsSection.grid.appendChild(node));
        configBody.appendChild(actionsSection.details);
        article.appendChild(configBody);

        const actions = el('div', 'project-editor-actions');
        const meta = el('div', 'project-editor-meta', project.updated_at ? `Updated ${project.updated_at}` : 'Draft project');
        const actionsRight = el('div', 'project-editor-actions-right');
        const saveBtn = el('button', 'project-editor-save', project.slug ? 'Save Project' : 'Create Project');
        saveBtn.type = 'button';
        saveBtn.addEventListener('click', async () => {
            await saveProjectRecord(project.slug, currentPayload());
        });
        const deleteBtn = el('button', 'project-editor-delete', project.slug ? 'Delete' : 'Remove Draft');
        deleteBtn.type = 'button';
        deleteBtn.addEventListener('click', async () => {
            await deleteProjectRecord(project);
        });
        actions.appendChild(meta);
        actionsRight.appendChild(dirtyBadge);
        actionsRight.appendChild(deleteBtn);
        actionsRight.appendChild(saveBtn);
        actions.appendChild(actionsRight);
        article.appendChild(actions);

        const savedSnapshot = JSON.stringify(normalizeProjectPayload(currentPayload()));
        const trackedControls = [
            titleField.control,
            summaryField.control,
            modeField.control,
            sortField.control,
            primaryField.control,
            repoField.control,
            dependsOnField.control,
            privateField.control,
            hostField.control,
            locationField.control,
            runtimeField.control,
            healthPublicField.control,
            healthPrivateField.control,
            deployField.control,
            startField.control,
            restartField.control,
            stopField.control,
            logsField.control
        ];
        const updateDirtyState = () => {
            const isDirty = JSON.stringify(normalizeProjectPayload(currentPayload())) !== savedSnapshot;
            dirtyBadge.classList.toggle('is-visible', isDirty);
            meta.textContent = project.updated_at ? `Updated ${project.updated_at}` : 'Draft project';
            openBtn.disabled = !projectOpenUrl(currentPayload());
            healthBtn.disabled = !project.slug || (!healthPublicField.control.value.trim() && !healthPrivateField.control.value.trim());
        };
        trackedControls.forEach(control => {
            control.addEventListener('input', updateDirtyState);
            control.addEventListener('change', updateDirtyState);
        });
        updateDirtyState();

        return article;
    }

    async function saveProjectRecord(existingSlug, payload, options = {}) {
        if (!options.silent) {
            setProjectsFeedback(existingSlug ? 'Saving project...' : 'Creating project...');
        }
        try {
            const url = existingSlug ? `/projects/${encodeURIComponent(existingSlug)}` : '/projects';
            const method = existingSlug ? 'PUT' : 'POST';
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data?.detail || 'save failed');
            if (!options.silent) {
                setProjectsFeedback(`Saved ${data.project.title}.`, 'success');
            }
            if (options.refreshAfterSave === false) {
                state.projects = state.projects.map(project => {
                    if (project.slug !== existingSlug) return project;
                    return normalizeProjectRecord({
                        ...project,
                        ...data.project,
                        action_result: project.action_result || null
                    });
                });
            } else {
                await loadProjects({ preserveActionResult: true });
            }
            return { ok: true, project: data.project };
        } catch (error) {
            if (!options.silent) {
                setProjectsFeedback(error.message || 'Failed to save project.', 'error');
            }
            return { ok: false, error: error.message || 'Failed to save project.' };
        }
    }

    function updateProjectState(slug, updater) {
        state.projects = state.projects.map(project => {
            if (project.slug !== slug) return project;
            const next = typeof updater === 'function' ? updater(project) : updater;
            return normalizeProjectRecord({ ...project, ...next });
        });
        renderProjects();
    }

    function mergeProjectUiState(nextProjects, options = {}) {
        const preserveActionResult = !!options.preserveActionResult;
        const currentByKey = new Map(
            state.projects.map(project => [projectEditorKey(project), project])
        );
        return nextProjects.map(project => {
            const current = currentByKey.get(projectEditorKey(project));
            if (!current) return project;
            return normalizeProjectRecord({
                ...project,
                action_result: preserveActionResult
                    ? (project.action_result || current.action_result || null)
                    : (project.action_result || null)
            });
        });
    }

    async function runProjectHealthCheck(slug, payload) {
        state.openProjectRows.add(String(slug || '').trim());
        setProjectsFeedback('Checking project health...');
        const saveResult = await saveProjectRecord(slug, payload, {
            silent: true,
            refreshAfterSave: false
        });
        if (!saveResult.ok) {
            setProjectsFeedback(saveResult.error || 'Failed to save project before health check.', 'error');
            return;
        }
        try {
            const resp = await fetch(`/projects/${encodeURIComponent(slug)}/health-check`, {
                method: 'POST'
            });
            const data = await readJsonResponse(resp);
            if (!resp.ok) throw new Error(data?.detail || 'health check failed');
            updateProjectState(slug, { health_snapshot: data });
            setProjectsFeedback(`Checked ${slug} health.`, 'success');
        } catch (error) {
            setProjectsFeedback(error.message || 'Failed to check project health.', 'error');
        }
    }

    async function runProjectAction(slug, action, payload) {
        state.openProjectRows.add(String(slug || '').trim());
        setProjectsFeedback(`${projectActionLabel(action)} running...`);
        const saveResult = await saveProjectRecord(slug, payload, {
            silent: true,
            refreshAfterSave: false
        });
        if (!saveResult.ok) {
            updateProjectState(slug, {
                action_result: {
                    ok: false,
                    action,
                    command: '',
                    stdout: '',
                    stderr: '',
                    detail: saveResult.error || `Failed to save project before ${action}.`
                }
            });
            setProjectsFeedback(saveResult.error || `Failed to save project before ${action}.`, 'error');
            return;
        }
        try {
            const resp = await fetch(`/projects/${encodeURIComponent(slug)}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            const data = await readJsonResponse(resp);
            if (!resp.ok) {
                updateProjectState(slug, { action_result: data });
                throw new Error(data?.detail || data?.stderr || `${action} failed`);
            }
            updateProjectState(slug, { action_result: data });
            setProjectsFeedback(`${projectActionLabel(action)} completed.`, 'success');
        } catch (error) {
            setProjectsFeedback(error.message || `Failed to ${action} project.`, 'error');
        }
    }

    async function deleteProjectRecord(project) {
        if (!project?.slug) {
            state.projects = state.projects.filter(item => item.draft_key !== project?.draft_key);
            renderProjects();
            setProjectsFeedback('Removed draft project.', 'success');
            return;
        }

        const confirmed = window.confirm(`Delete project "${project.title || project.slug}" from the catalog?`);
        if (!confirmed) return;

        setProjectsFeedback(`Deleting ${project.title || project.slug}...`);
        try {
            const resp = await fetch(`/projects/${encodeURIComponent(project.slug)}`, {
                method: 'DELETE'
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data?.detail || 'delete failed');
            setProjectsFeedback(`Deleted ${data.project.title}.`, 'success');
            await loadProjects();
        } catch (error) {
            setProjectsFeedback(error.message || 'Failed to delete project.', 'error');
        }
    }

    async function exportProjectsCatalog() {
        if (hasDirtyProjectEditors()) {
            setProjectsFeedback('Save all project changes before exporting the catalog.', 'error');
            renderProjectsResult(null);
            return;
        }
        setProjectsFeedback('Exporting project catalog...');
        try {
            const resp = await fetch('/projects/export', {
                method: 'POST'
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data?.detail || 'export failed');
            const syncedCopy = Array.isArray(data.synced_paths) && data.synced_paths.length > 0;
            const message = syncedCopy
                ? `Exported ${data.count} projects and synced portfolio data to ${data.synced_paths.join(', ')}.`
                : `Exported ${data.count} projects to ${data.path}.`;
            setProjectsFeedback(message, 'success');
            renderProjectsResult(null);
        } catch (error) {
            setProjectsFeedback(error.message || 'Failed to export projects.', 'error');
            renderProjectsResult(null);
        }
    }

    async function publishPortfolioCatalog() {
        if (hasDirtyProjectEditors()) {
            setProjectsFeedback('Save all project changes before publishing the portfolio.', 'error');
            renderProjectsResult(null);
            return;
        }
        setProjectsFeedback('Publishing portfolio catalog...');
        try {
            const resp = await fetch('/projects/publish', {
                method: 'POST'
            });
            const data = await resp.json();
            if (!resp.ok) {
                renderProjectsResult(data, 'error');
                throw new Error(data?.detail || 'publish failed');
            }
            renderProjectsResult(data, 'success');
            const message = data.no_changes
                ? 'Portfolio catalog was already up to date.'
                : `Published portfolio catalog to ${data.branch}.`;
            setProjectsFeedback(message, 'success');
        } catch (error) {
            setProjectsFeedback(error.message || 'Failed to publish portfolio.', 'error');
        }
    }

    async function loadHosts(options = {}) {
        if (!els.hostsList) return;
        try {
            const resp = await fetch('/hosts');
            const data = await readJsonResponse(resp);
            if (!resp.ok) throw new Error(data?.detail || 'host load failed');
            state.hosts = Array.isArray(data.hosts) ? data.hosts.map(normalizeHostRecord) : [];
            renderHosts();
            if (options.refreshHealth !== false) {
                refreshHostsHealth({ silent: true });
            }
        } catch (error) {
            console.error('Failed to load hosts', error);
            if (!options.silent) {
                setHostsFeedback(error.message || 'Failed to load hosts.', 'error');
            }
        }
    }

    async function refreshHostsHealth(options = {}) {
        try {
            const resp = await fetch('/hosts/refresh-health', { method: 'POST' });
            const data = await readJsonResponse(resp);
            if (!resp.ok) throw new Error(data?.detail || 'host health refresh failed');
            state.hosts = Array.isArray(data.hosts) ? data.hosts.map(normalizeHostRecord) : state.hosts;
            renderHosts();
            await loadProjects({ silent: true, refreshHealth: false });
            if (!options.silent) {
                setHostsFeedback('Host runner health refreshed.', 'success');
            }
        } catch (error) {
            console.error('Failed to refresh hosts', error);
            if (!options.silent) {
                setHostsFeedback(error.message || 'Failed to refresh host runner health.', 'error');
            }
        }
    }

    async function loadProjects(options = {}) {
        if (!els.projectsList) return;
        if (options.auto && hasDirtyProjectEditors()) {
            return;
        }
        try {
            const resp = await fetch('/projects');
            const data = await resp.json();
            state.projects = Array.isArray(data.projects)
                ? mergeProjectUiState(data.projects.map(normalizeProjectRecord), {
                    preserveActionResult: !!options.preserveActionResult
                })
                : [];
            renderProjects();
            if (options.refreshHealth !== false) {
                refreshProjectsHealth({ silent: true });
            }
        } catch (error) {
            console.error('Failed to load projects', error);
            if (!options.silent) {
                setProjectsFeedback('Failed to load projects.', 'error');
            }
        }
    }

    async function refreshProjectsHealth(options = {}) {
        if (hasDirtyProjectEditors()) {
            return;
        }
        try {
            const resp = await fetch('/projects/refresh-health', {
                method: 'POST'
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data?.detail || 'health refresh failed');
            state.projects = Array.isArray(data.projects)
                ? mergeProjectUiState(data.projects.map(normalizeProjectRecord))
                : state.projects;
            renderProjects();
            if (!options.silent) {
                setProjectsFeedback('Project health refreshed.', 'success');
            }
        } catch (error) {
            console.error('Failed to refresh project health', error);
            if (!options.silent) {
                setProjectsFeedback(error.message || 'Failed to refresh project health.', 'error');
            }
        }
    }

    function addProjectDraft() {
        const draft = emptyProjectDraft();
        state.projects = [...state.projects, draft];
        const draftKey = projectEditorKey(draft);
        state.openProjectRows.add(draftKey);
        renderProjects();
        setProjectsFeedback('Fill in the draft project, then save it.');
        if (state.activePanelId !== 'projects') openPanel('projects');
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
            updateStatusPills();
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
        if (!els.hiddenToolsMenu || !els.pillTools) return;
        state.hiddenToolsMenuOpen = !!open;
        if (!state.hiddenToolsMenuOpen) {
            state.appsRowMenuOpenFor = null;
            renderHiddenToolsMenu();
        }
        els.hiddenToolsMenu.hidden = !state.hiddenToolsMenuOpen;
        els.pillTools.setAttribute('aria-expanded', state.hiddenToolsMenuOpen ? 'true' : 'false');
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
            updateStatusPills();

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
    if (els.pillTools) {
        els.pillTools.addEventListener('click', event => {
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
    if (els.pillProjects) {
        els.pillProjects.addEventListener('click', event => {
            event.stopPropagation();
            openPanel('projects', event.currentTarget);
        });
    }
    if (els.pillHosts) {
        els.pillHosts.addEventListener('click', event => {
            event.stopPropagation();
            openPanel('hosts', event.currentTarget);
        });
    }
    if (els.panelProjectsClose) {
        els.panelProjectsClose.addEventListener('click', () => closePanel());
    }
    if (els.panelHostsClose) {
        els.panelHostsClose.addEventListener('click', () => closePanel());
    }
    if (els.panelBackdrop) {
        els.panelBackdrop.addEventListener('click', () => closePanel());
    }
    if (els.projectAddBtn) {
        els.projectAddBtn.addEventListener('click', event => {
            event.stopPropagation();
            addProjectDraft();
        });
    }
    if (els.projectExportBtn) {
        els.projectExportBtn.addEventListener('click', event => {
            event.stopPropagation();
            exportProjectsCatalog();
        });
    }
    if (els.projectPublishBtn) {
        els.projectPublishBtn.addEventListener('click', event => {
            event.stopPropagation();
            publishPortfolioCatalog();
        });
    }
    document.addEventListener('click', event => {
        const inMenu = event.target && event.target.closest('.tool-settings-menu');
        const inButton = event.target && event.target.closest('.tool-settings-btn');
        const inHiddenToolsMenu = event.target && event.target.closest('#hidden-tools-menu');
        const inPillTools = event.target && event.target.closest('#pill-tools');
        const inReorderPanel = event.target && event.target.closest('#reorder-panel');
        const inReorderBtn = event.target && event.target.closest('#reorder-mode-btn');
        const inPanel = event.target && event.target.closest('.side-panel');
        const inPillProjects = event.target && event.target.closest('#pill-projects');
        const inPillHosts = event.target && event.target.closest('#pill-hosts');
        if (!inMenu && !inButton) closeAllToolMenus();
        if (!inHiddenToolsMenu && !inPillTools) {
            setHiddenToolsMenuOpen(false);
        } else if (!event.target.closest('.apps-row-settings-btn, .apps-row-menu')) {
            closeAppsRowMenus();
        }
        if (!inReorderPanel && !inReorderBtn) {
            setReorderModeOpen(false);
        }
        if (!inPanel && !inPillProjects && !inPillHosts && state.activePanelId) {
            closePanel();
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Tab' && state.activePanelId) {
            const panelEl = getActivePanelElement();
            const focusables = getPanelFocusableElements(panelEl);
            if (!focusables.length) {
                event.preventDefault();
                panelEl?.focus();
                return;
            }
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
                return;
            }
            if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
                return;
            }
        }
        if (event.key === 'Escape') {
            closeAllToolMenus();
            setHiddenToolsMenuOpen(false);
            setReorderModeOpen(false);
            if (state.activePanelId) closePanel();
        }
    });
    window.addEventListener('resize', () => {
        enforceCardSpanConstraints();
        enforceWidgetHeightConstraints();
        requestAnimationFrame(resizeAllCards);
    });

    loadHosts({ silent: true });
    loadProjects({ silent: true });
    loadDashboard();
    setInterval(refreshAllStatuses, REFRESH_RATE);
    setInterval(() => refreshHostsHealth({ silent: true }), PROJECT_REFRESH_RATE);
    setInterval(() => refreshProjectsHealth({ silent: true }), PROJECT_REFRESH_RATE);
