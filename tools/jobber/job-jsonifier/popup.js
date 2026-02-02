// --- EVENT LISTENERS ---

let statusLocked = false;

async function fetchJsonWithTimeout(url, options = {}, timeoutMs = 1500) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        let data = null;
        try {
            data = await res.json();
        } catch {
            data = null;
        }
        return { res, data };
    } finally {
        clearTimeout(timeoutId);
    }
}

function setStatus(text, color, force = false) {
    if (statusLocked && !force) return;
    const statusDiv = document.getElementById("statusMsg");
    statusDiv.textContent = text;
    if (color) statusDiv.style.color = color;
}

function setStatusWithOpen(text, path) {
    const statusDiv = document.getElementById("statusMsg");
    statusDiv.style.color = "green";
    statusDiv.innerHTML = `${text} — <span id="openOutput" class="status-link">Open</span>`;
    const openEl = document.getElementById("openOutput");
    openEl.addEventListener("click", () => openOutput(path));
}

async function openOutput(path) {
    try {
        const { data } = await fetchJsonWithTimeout(
            "http://127.0.0.1:30001/open-output",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path })
            },
            1500
        );
        if (!data || !data.ok) {
            setStatus(`❌ ${(data && data.error) || "Unable to open file"}`, "red", true);
        }
    } catch (error) {
        setStatus("❌ Jobber is offline", "red", true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Fast path: scrape immediately, then try DB in parallel.
    runScraper();
    checkDbAndMaybeLoad();
});

document.getElementById("deleteBtn").addEventListener("click", async () => {
    const url = document.getElementById("jobUrl").value;
    const statusDiv = document.getElementById("statusMsg");

    if (!confirm("Are you sure you want to DELETE this job from your database?")) {
        return;
    }

    setStatus("Deleting...", "#666", true);
    
    try {
        const { res: response } = await fetchJsonWithTimeout(
            "http://127.0.0.1:30001/delete",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            },
            3000
        );

        if (response && response.ok) {
            setStatus("🗑️ Job Deleted!", "red", true);
            
            // Optional: Close popup or clear form after delay
            setTimeout(() => window.close(), 1000);
        } else {
            setStatus("Error deleting", "red", true);
        }
    } catch (error) {
        console.error(error);
        setStatus("Server Error", "red", true);
    }
});

document.getElementById("extractBtn").addEventListener("click", runScraper);

document.getElementById("saveBtn").addEventListener("click", async () => {
    const jobData = collectJobData();

    if (!jobData.title) {
        setStatus("⚠️ Title is required", "orange", true);
        return;
    }

    // 2. Send to Jobber
    setStatus("Sending...", "#666", true);
    await sendToJobber(jobData);
});

document.getElementById("generateBtn").addEventListener("click", async () => {
    const jobData = collectJobData();

    if (!jobData.title || !jobData.description) {
        setStatus("⚠️ Title and description are required", "orange", true);
        return;
    }

    statusLocked = true;
    setStatus("Generating letter...", "#666", true);

    try {
        const { res: response, data } = await fetchJsonWithTimeout(
            "http://127.0.0.1:30001/generate",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jobTitle: jobData.title,
                    company: jobData.company,
                    jobDescription: jobData.description,
                    jobUrl: jobData.url
                })
            },
            3000
        );

        if (!data || !data.ok) {
            setStatus(`❌ ${(data && data.error) || "Server Error"}`, "red", true);
            return;
        }

        if (data.skipped) {
            setStatusWithOpen("✅ Already exists", data.outputPath);
            return;
        }

        if (data.inFlight && data.jobId) {
            setStatus("Already running... ", "#666", true);
            await pollGenerateStatus(data.jobId);
            return;
        }

        if (data.jobId) {
            await pollGenerateStatus(data.jobId);
            return;
        }

        // Back-compat in case the server returns a completed response.
        const totalMs = data.timingsMs?.total;
        const llmMs = data.timingsMs?.llm;
        const engine = data.engine || "llm";
        const promptLog = data.promptLogPath;
        const timingLine =
            typeof totalMs === "number"
                ? ` (${Math.round(totalMs / 1000)}s total` +
                  (typeof llmMs === "number"
                      ? `, ${Math.round(llmMs / 1000)}s ${engine}`
                      : "") +
                  ")"
                : "";
        const promptLine = promptLog ? `\nPrompt: ${promptLog}` : "";

        setStatusWithOpen(`✅ Saved${timingLine}${promptLine}`, data.outputPath);
    } catch (error) {
        setStatus("❌ Jobber server is offline", "red", true);
    } finally {
        statusLocked = false;
    }
});

async function pollGenerateStatus(jobId) {
    const startedAt = Date.now();
    while (true) {
        if (Date.now() - startedAt > 5 * 60 * 1000) {
            setStatus("❌ Timed out waiting for generation", "red", true);
            return;
        }

        let data;
        try {
            ({ data } = await fetchJsonWithTimeout(
                `http://127.0.0.1:30001/generate-status/${jobId}`,
                {},
                1500
            ));
        } catch (e) {
            setStatus("❌ Jobber server is offline", "red", true);
            return;
        }

        if (!data.ok) {
            setStatus(`❌ ${data.error || "Generation failed"}`, "red", true);
            return;
        }

        if (data.status === "done") {
            const totalMs = data.timingsMs?.total;
            const llmMs = data.timingsMs?.llm;
            const engine = data.engine || "llm";
            const promptLog = data.promptLogPath;
            const timingLine =
                typeof totalMs === "number"
                    ? ` (${Math.round(totalMs / 1000)}s total` +
                      (typeof llmMs === "number"
                          ? `, ${Math.round(llmMs / 1000)}s ${engine}`
                          : "") +
                      ")"
                    : "";
            const promptLine = promptLog ? `\nPrompt: ${promptLog}` : "";

            setStatusWithOpen(`✅ Saved${timingLine}${promptLine}`, data.outputPath);
            return;
        }

        if (data.status === "error") {
            setStatus(`❌ ${data.error || "Generation failed"}`, "red", true);
            return;
        }

        setStatus("Generating letter...", "#666", true);
        await new Promise((r) => setTimeout(r, 800));
    }
}

function collectJobData() {
    return {
        title: document.getElementById("jobTitle").value,
        company: document.getElementById("jobCompany").value,
        location: document.getElementById("jobLocation").value,
        url: document.getElementById("jobUrl").value,
        date_scraped: document.getElementById("jobDate").value || new Date().toISOString(),
        description: document.getElementById("jobDesc").value
    };
}

// --- MAIN SCRAPER ORCHESTRATOR ---

async function runScraper() {
    setStatus("Scanning page...", "#666");

    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: scrapeJobData,
    }, (results) => {

        if (results && results[0]) {
            const data = results[0].result;
            
            // Populate Form
            document.getElementById("jobTitle").value = data.title;
            document.getElementById("jobCompany").value = data.company;
            document.getElementById("jobLocation").value = data.location;
            document.getElementById("jobDesc").value = data.description;
            
            // Hidden fields
            document.getElementById("jobUrl").value = data.url;
            document.getElementById("jobDate").value = data.date_scraped;

            setStatus("", null, true);
        } else {
            setStatus("Could not extract data", "red", true);
        }
    });
}

async function sendToJobber(jobData) {
    try {
        const { res: response } = await fetchJsonWithTimeout(
            "http://127.0.0.1:30001/save",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(jobData)
            },
            3000
        );

        if (response.ok) {
            setStatus("✅ Saved to Jobber!", "green", true);
            setTimeout(() => window.close(), 1200); // Close popup after success
        } else {
            setStatus("❌ Server Error", "red", true);
        }
    } catch (error) {
        setStatus("❌ Jobber is offline", "red", true);
    }
}

// --- INJECTED SCRIPT (The Scraper Logic) ---
function scrapeJobData() {
    const clean = (text) => text ? text.replace(/\s+/g, ' ').trim() : "";
    const hostname = window.location.hostname;

    function cleanupJobDescription(rawText) {
        if (!rawText) return "";
        let lines = rawText.split("\n").map((line) => line.trim());

        const startMarkers = [
            /^##\s*about the job/i,
            /^about the job/i,
            /^##\s*job description/i,
            /^job description/i,
            /^##\s*role/i
        ];
        const endMarkers = [
            /^##\s*about the company/i,
            /^about the company/i,
            /^##\s*company photos/i,
            /^company photos/i,
            /^##\s*more jobs/i,
            /^more jobs/i,
            /^##\s*set alert/i,
            /^set alert/i,
            /^##\s*see more jobs/i,
            /^see more jobs/i,
            /^##\s*job search/i,
            /^job search/i,
            /^looking for talent\?/i
        ];

        let startIdx = 0;
        for (let i = 0; i < lines.length; i++) {
            if (startMarkers.some((rx) => rx.test(lines[i]))) {
                startIdx = i;
                break;
            }
        }

        let endIdx = lines.length;
        for (let i = startIdx + 1; i < lines.length; i++) {
            if (endMarkers.some((rx) => rx.test(lines[i]))) {
                endIdx = i;
                break;
            }
        }

        lines = lines.slice(startIdx, endIdx);

        const noisePatterns = [
            /reactivate premium/i,
            /premium/i,
            /easy apply/i,
            /over \d+ applicants/i,
            /applicants\b/i,
            /actively reviewing applicants/i,
            /promoted by hirer/i,
            /people you can reach out to/i,
            /meet the hiring team/i,
            /^message$/i,
            /set alert/i,
            /see more jobs/i,
            /job search faster/i,
            /job search smarter/i,
            /looking for talent/i
        ];

        const cleaned = [];
        let lastLine = "";
        for (const line of lines) {
            if (!line) {
                if (cleaned.length && cleaned[cleaned.length - 1] !== "") {
                    cleaned.push("");
                }
                continue;
            }
            if (noisePatterns.some((rx) => rx.test(line))) {
                continue;
            }

            const mdLinkMatch = line.match(/^\[.*\]\((https?:\/\/[^)]+)\)$/);
            if (mdLinkMatch) {
                const url = mdLinkMatch[1].toLowerCase();
                if (
                    url.includes("linkedin.com/premium") ||
                    url.includes("/jobs/collections") ||
                    url.includes("/messaging/compose") ||
                    url.includes("/help/linkedin/answer")
                ) {
                    continue;
                }
            }

            if (line === lastLine) {
                continue;
            }
            cleaned.push(line);
            lastLine = line;
        }

        while (cleaned[0] === "") cleaned.shift();
        while (cleaned[cleaned.length - 1] === "") cleaned.pop();

        let result = cleaned.join("\n");
        const maxChars = 8000;
        if (result.length > maxChars) {
            result = result.slice(0, maxChars).trim();
        }
        return result;
    }

    // --- HELPER: HTML to Markdown Converter ---
    function htmlToMarkdown(element) {
        if (!element) return "";
        
        let node = element.cloneNode(true);
        
        // 1. ADVANCED CLEANUP
        // Remove interactive bits, hidden a11y text, and common footer/nav noise
        const junkSelectors = [
            'script', 'style', 'noscript', 'iframe', 'svg', 
            'nav', 'footer', 'header', 'aside', 
            'button', 'input', 'select', 'textarea',
            '.ad', '.share-buttons', '.social-media',
            '[role="alert"]', '[role="banner"]', '[role="navigation"]',
            '.visually-hidden', '.sr-only', '.screen-reader-text', // Fixes "Page is loaded"
            '[aria-hidden="true"]'
        ];
        
        node.querySelectorAll(junkSelectors.join(',')).forEach(el => el.remove());

        function walk(n) {
            let out = "";
            n.childNodes.forEach(child => {
                if (child.nodeType === 3) { 
                    // TEXT NODE: Normalize whitespace
                    let text = child.nodeValue.replace(/[\n\r\t]+/g, " ");
                    out += text;
                } 
                else if (child.nodeType === 1) { 
                    // ELEMENT NODE
                    const tag = child.tagName.toLowerCase();
                    const childText = walk(child);
                    const cleanText = childText.trim();

                    // SKIP EMPTY ELEMENTS (Fixes empty ## headers)
                    if (cleanText === "" && !['br', 'img', 'hr'].includes(tag)) {
                        return;
                    }

                    if (tag === 'br') {
                        out += "\n"; 
                    }
                    else if (['div', 'p', 'section', 'article', 'main'].includes(tag)) {
                        out += "\n" + childText + "\n";
                    }
                    else if (['h1','h2','h3','h4','h5','h6'].includes(tag)) {
                        // Only add header markings if there is actual text
                        if (cleanText.length > 0) {
                            out += "\n\n## " + cleanText + "\n";
                        }
                    }
                    else if (tag === 'li') {
                        out += "\n- " + cleanText;
                    }
                    else if (tag === 'ul' || tag === 'ol') {
                        out += "\n" + childText + "\n";
                    }
                    else if (tag === 'dt') {
                        out += "\n**" + cleanText + "**\n";
                    }
                    else if (tag === 'dd') {
                        out += "> " + cleanText + "\n";
                    }
                    else if (tag === 'b' || tag === 'strong') {
                        out += "**" + childText + "**";
                    }
                    else if (tag === 'em' || tag === 'i') {
                        out += "_" + childText + "_";
                    }
                    else if (tag === 'a') {
                        const href = child.href;
                        // NOISE FILTER: specific link text to ignore
                        const ignoreList = ['apply', 'apply now', 'privacy policy', 'terms', 'sign in', 'skip to main'];
                        
                        if (ignoreList.includes(cleanText.toLowerCase())) {
                            return; // Skip this link entirely
                        }

                        if (href && cleanText && !href.startsWith('javascript') && !href.startsWith('#')) {
                            out += `[${cleanText}](${href})`;
                        } else {
                            out += childText;
                        }
                    }
                    else if (tag === 'span' || tag === 'label') {
                        // Avoid adding spaces if the span is just a container, 
                        // but add them if it's text like "Location: New York"
                        out += " " + childText + " "; 
                    }
                    else {
                        out += childText; 
                    }
                }
            });
            return out;
        }

        const rawMarkdown = walk(node);
        
        return rawMarkdown
            // 2. POST-PROCESSING REGEX
            .replace(/[ \t]+/g, ' ')       // Collapse multiple spaces
            .replace(/\n\s/g, '\n')        // Remove leading space on new lines
            .replace(/\n{3,}/g, '\n\n')    // Max 2 empty lines
            .replace(/ \*\*/g, ' **')      // Fix bold spacing
            .replace(/\*\* /g, '** ')      // Fix bold spacing
            .trim();
    }

    // --- INITIALIZE DATA ---
    let data = {
        title: "",
        company: "",
        location: "",
        url: window.location.href,
        date_scraped: new Date().toISOString(),
        description: "" 
    };

    // --- 1. JSON-LD (Structured Data) - Highest Priority ---
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const json = JSON.parse(script.innerText);
            const graph = json['@graph'] || (Array.isArray(json) ? json : [json]);
            const jobPost = graph.find(item => item['@type'] === 'JobPosting');
            
            if (jobPost) {
                data.title = clean(jobPost.title);
                data.company = clean(jobPost.hiringOrganization?.name);
                
                // Smart Location Handling
                if (jobPost.jobLocation) {
                    const addr = jobPost.jobLocation.address;
                    if (typeof addr === 'string') {
                        data.location = clean(addr);
                    } else if (addr) {
                        const parts = [addr.addressLocality, addr.addressRegion].filter(Boolean);
                        data.location = parts.join(", ");
                    }
                }
            }
        } catch (e) {}
    }

    // --- 2. FALLBACKS (If JSON-LD was empty) ---

    // A. Title
    if (!data.title) {
        const titleCandidates = [
            document.querySelector('meta[property="og:title"]')?.content,
            document.querySelector('meta[name="twitter:title"]')?.content,
            document.querySelector('meta[name="title"]')?.content
        ].filter(Boolean);

        const rawTitle = titleCandidates[0] || document.title || "";
        const splitTitle = rawTitle.split(/\\s[\\-|\\|—–]\\s/)[0];

        const titleSelectors = [
            'h1',
            '[data-test="jobTitle"]',
            '[data-testid="jobTitle"]',
            '.topcard__title',
            '.jobs-unified-top-card__job-title',
            '.jobsearch-JobInfoHeader-title',
            '.job-details-jobs-header__title'
        ];

        let selectorTitle = "";
        for (const sel of titleSelectors) {
            const el = document.querySelector(sel);
            if (el && clean(el.innerText)) {
                selectorTitle = clean(el.innerText);
                break;
            }
        }

        data.title = selectorTitle || clean(splitTitle) || "Unknown Title";
    }

    // B. Company (Heuristic Selectors)
    if (!data.company) {
        const companySelectors = [
            '.job-details-jobs-header__company-url', // LinkedIn
            '[data-company-name="true"]', 
            '.topcard__org-name-link',    
            '[data-testid="inlineHeader-companyName"]', // Indeed
            '.c-job-header__company',     
            'a[href*="/company/"]'        
        ];
        for (let sel of companySelectors) {
            const el = document.querySelector(sel);
            if (el) { data.company = clean(el.innerText); break; }
        }
    }

    // C. Location (Heuristic Selectors)
    if (!data.location) {
        const locationSelectors = [
            '.job-details-jobs-header__company-location', 
            '.topcard__flavor--bullet',   
            '[data-testid="inlineHeader-companyLocation"]', 
            '.location', 
            '.job-location',
            '[class*="location"]'
        ];
        for (let sel of locationSelectors) {
            const el = document.querySelector(sel);
            if (el) { data.location = clean(el.innerText); break; }
        }
    }

    // --- 3. DESCRIPTION ---
    const descSelectors = [
        ".jobs-description-content__text", // LinkedIn
        ".show-more-less-html__markup",    // LinkedIn
        "#jobDescriptionText",             // Indeed
        ".job-description",
        "[class*='job-description']",
        "article"
    ];

    let contentNode = null;
    for (const sel of descSelectors) {
        const found = document.querySelector(sel);
        if (found) { contentNode = found; break; }
    }
    
    // Default to body if specific container not found
    if (!contentNode) {
        contentNode = document.querySelector('main') || document.body;
    }

    data.description = cleanupJobDescription(htmlToMarkdown(contentNode));

    return data;
}

async function checkDbAndMaybeLoad() {
    
    // 1. Get the current Tab URL first
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url) {
        setStatus("Error: No URL found", "red", true);
        return;
    }

    try {
        // 2. Ask the backend if we have this URL
        const { data: result } = await fetchJsonWithTimeout(
            "http://127.0.0.1:30001/check",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: tab.url })
            },
            600
        );

        if (result && result.found && result.data) {
            // --- SCENARIO A: LOAD FROM DB ---
            console.log("Job found in DB!");
            const data = result.data;
            
            document.getElementById("jobTitle").value = data.title || "";
            document.getElementById("jobCompany").value = data.company || "";
            document.getElementById("jobLocation").value = data.location || "";
            document.getElementById("jobDesc").value = data.description || "";
            
            document.getElementById("jobUrl").value = data.url;
            document.getElementById("jobDate").value = data.date_scraped;

            setStatus("✅ Loaded from Database", "blue");
            document.getElementById("deleteBtn").style.display = "block";
            
        } else {
            // Not found: keep scraped values.
            document.getElementById("deleteBtn").style.display = "none";
        }

    } catch (error) {
        // If backend is offline/slow, keep scraped values.
        console.warn("Backend unavailable, using scraped data", error);
        document.getElementById("deleteBtn").style.display = "none";
    }
}
