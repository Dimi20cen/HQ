// --- EVENT LISTENERS ---

document.addEventListener('DOMContentLoaded', () => {
    // Check DB first, then scrape if unknown
    checkDbOrScrape();
});

document.getElementById("deleteBtn").addEventListener("click", async () => {
    const url = document.getElementById("jobUrl").value;
    const statusDiv = document.getElementById("statusMsg");

    if (!confirm("Are you sure you want to DELETE this job from your database?")) {
        return;
    }

    statusDiv.innerText = "Deleting...";
    
    try {
        const response = await fetch("http://127.0.0.1:30001/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url })
        });

        if (response.ok) {
            statusDiv.innerText = "🗑️ Job Deleted!";
            statusDiv.style.color = "red";
            
            // Optional: Close popup or clear form after delay
            setTimeout(() => window.close(), 1000);
        } else {
            statusDiv.innerText = "Error deleting";
        }
    } catch (error) {
        console.error(error);
        statusDiv.innerText = "Server Error";
    }
});

document.getElementById("extractBtn").addEventListener("click", runScraper);

document.getElementById("saveBtn").addEventListener("click", async () => {
    const statusDiv = document.getElementById("statusMsg");
    
    const jobData = collectJobData();

    if (!jobData.title) {
        statusDiv.innerText = "⚠️ Title is required";
        statusDiv.style.color = "orange";
        return;
    }

    // 2. Send to Kolibri
    statusDiv.innerText = "Sending...";
    await sendToKolibri(jobData);
});

document.getElementById("generateBtn").addEventListener("click", async () => {
    const statusDiv = document.getElementById("statusMsg");
    const jobData = collectJobData();

    if (!jobData.title || !jobData.description) {
        statusDiv.innerText = "⚠️ Title and description are required";
        statusDiv.style.color = "orange";
        return;
    }

    statusDiv.innerText = "Generating letter...";
    statusDiv.style.color = "#666";

    try {
        const response = await fetch("http://127.0.0.1:5055/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jobTitle: jobData.title,
                company: jobData.company,
                jobDescription: jobData.description,
                jobUrl: jobData.url
            })
        });

        const data = await response.json();
        if (!data.ok) {
            statusDiv.innerText = `❌ ${data.error}`;
            statusDiv.style.color = "red";
            return;
        }

        const totalMs = data.timingsMs?.total;
        const codexMs = data.timingsMs?.codex;
        const promptLog = data.promptLogPath;
        const timingLine =
            typeof totalMs === "number"
                ? ` (${Math.round(totalMs / 1000)}s total` +
                  (typeof codexMs === "number"
                      ? `, ${Math.round(codexMs / 1000)}s codex`
                      : "") +
                  ")"
                : "";
        const promptLine = promptLog ? `\nPrompt: ${promptLog}` : "";

        statusDiv.innerText = `✅ Saved: ${data.outputPath}${timingLine}${promptLine}`;
        statusDiv.style.color = "green";
    } catch (error) {
        statusDiv.innerText = "❌ Covlet server is offline";
        statusDiv.style.color = "red";
    }
});

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
    const statusDiv = document.getElementById("statusMsg");
    statusDiv.innerText = "Scanning page...";
    statusDiv.style.color = "#666";

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

            statusDiv.innerText = ""; // Clear status
        } else {
            statusDiv.innerText = "Could not extract data";
            statusDiv.style.color = "red";
        }
    });
}

async function sendToKolibri(jobData) {
    const statusDiv = document.getElementById("statusMsg");
    try {
        const response = await fetch("http://127.0.0.1:30001/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jobData)
        });

        if (response.ok) {
            statusDiv.innerText = "✅ Saved to Database!";
            statusDiv.style.color = "green";
            setTimeout(() => window.close(), 1200); // Close popup after success
        } else {
            statusDiv.innerText = "❌ Server Error";
            statusDiv.style.color = "red";
        }
    } catch (error) {
        statusDiv.innerText = "❌ Kolibri is offline";
        statusDiv.style.color = "red";
    }
}

// --- INJECTED SCRIPT (The Scraper Logic) ---
function scrapeJobData() {
    const clean = (text) => text ? text.replace(/\s+/g, ' ').trim() : "";

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
        "#jobDescriptionText",           // Indeed
        ".show-more-less-html__markup",  // LinkedIn
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

    data.description = htmlToMarkdown(contentNode);

    return data;
}

async function checkDbOrScrape() {
    const statusDiv = document.getElementById("statusMsg");
    statusDiv.innerText = "Checking database...";
    
    // 1. Get the current Tab URL first
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url) {
        statusDiv.innerText = "Error: No URL found";
        return;
    }

    try {
        // 2. Ask the backend if we have this URL
        const response = await fetch("http://127.0.0.1:30001/check", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: tab.url })
        });

        const result = await response.json();

        if (result.found && result.data) {
            // --- SCENARIO A: LOAD FROM DB ---
            console.log("Job found in DB!");
            const data = result.data;
            
            document.getElementById("jobTitle").value = data.title || "";
            document.getElementById("jobCompany").value = data.company || "";
            document.getElementById("jobLocation").value = data.location || "";
            document.getElementById("jobDesc").value = data.description || "";
            
            document.getElementById("jobUrl").value = data.url;
            document.getElementById("jobDate").value = data.date_scraped;

            statusDiv.innerText = "✅ Loaded from Database";
            statusDiv.style.color = "blue";
            document.getElementById("deleteBtn").style.display = "block";
            
        } else {
            // --- SCENARIO B: NOT FOUND, RUN SCRAPER ---
            console.log("Job not in DB, scraping...");
            runScraper();
            document.getElementById("deleteBtn").style.display = "none";
        }

    } catch (error) {
        // If Backend is offline, fail gracefully back to scraping
        console.warn("Backend unavailable, falling back to scrape", error);
        runScraper();
    }
}
