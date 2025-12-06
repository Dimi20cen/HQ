document.getElementById("scrapeBtn").addEventListener("click", async () => {
    const statusDiv = document.getElementById("statusMsg");
    statusDiv.innerText = "Analyzing page...";
    statusDiv.style.color = "#666";

    // 1. Get current tab
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // 2. Inject script
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: scrapeJobData,
    }, async (results) => {
        if (results && results[0]) {
            const data = results[0].result;
            
            // Show JSON in box
            document.getElementById("result").value = JSON.stringify(data, null, 2);
            
            // 3. Send to Python Backend
            statusDiv.innerText = "Sending to Kolibri...";
            await sendToKolibri(data);
        } else {
            statusDiv.innerText = "Failed to extract data.";
            statusDiv.style.color = "red";
        }
    });
});

async function sendToKolibri(jobData) {
    const statusDiv = document.getElementById("statusMsg");
    
    try {
        const response = await fetch("http://127.0.0.1:30001/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jobData)
        });

        if (response.ok) {
            const resData = await response.json();
            const countMsg = resData.total_count ? ` (Total: ${resData.total_count})` : "";
            statusDiv.innerText = `✅ Saved!${countMsg}`;
            statusDiv.style.color = "green";
        } else {
            statusDiv.innerText = "❌ Server Error. Is Kolibri running?";
            statusDiv.style.color = "red";
        }
    } catch (error) {
        statusDiv.innerText = "❌ Connection Refused. Check Kolibri.";
        statusDiv.style.color = "red";
        console.error(error);
    }
}

// --- CORE LOGIC: RUNS INSIDE THE PAGE ---
function scrapeJobData() {
    const clean = (text) => text ? text.trim() : "";

    let data = {
        title: "Unknown Title",
        company: "Unknown Company",
        location: "Unknown Location",
        url: window.location.href,
        date_scraped: new Date().toISOString(),
        description: "" 
    };

    // --- HELPER: Lightweight HTML to Markdown Converter ---
    function htmlToMarkdown(element) {
        if (!element) return "";
        
        let node = element.cloneNode(true);
        
        // 1. CLEANUP: Added 'noscript' to the list to kill the "Enable JS" message
        const junk = node.querySelectorAll('script, style, noscript, iframe, svg, nav, footer, .ad, button, [aria-hidden="true"], .assistive-text');
        junk.forEach(el => el.remove());

        function walk(n) {
            let out = "";
            n.childNodes.forEach(child => {
                if (child.nodeType === 3) { 
                    // Normalize whitespace 
                    let text = child.nodeValue.replace(/[\n\r\t]+/g, " ");
                    out += text;
                } else if (child.nodeType === 1) { 
                    const tag = child.tagName.toLowerCase();
                    const childText = walk(child);
                    
                    if (tag === 'br') {
                        out += "\n"; 
                    }
                    else if (['div', 'p', 'section', 'article', 'dt', 'dd', 'tr'].includes(tag)) {
                        out += "\n" + childText + "\n";
                    }
                    else if (['h1','h2','h3','h4'].includes(tag)) {
                        out += "\n\n## " + childText.trim() + "\n";
                    }
                    else if (tag === 'li') {
                        const trimmed = childText.trim();
                        if (trimmed) {
                            out += "\n- " + trimmed;
                        }
                    }
                    else if (tag === 'ul' || tag === 'ol') {
                        out += "\n" + childText + "\n";
                    }
                    else if (tag === 'b' || tag === 'strong') {
                        out += "**" + childText + "**";
                    }
                    else if (tag === 'a') {
                        const href = child.href;
                        const txt = childText.trim();
                        if (txt.toLowerCase().includes('skip to main')) return;

                        if (href && txt.length > 0 && !href.startsWith('javascript') && !href.startsWith('#')) {
                            out += `[${txt}](${href})`;
                        } else {
                            out += childText;
                        }
                    }
                    else if (tag === 'span' || tag === 'label') {
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
            .replace(/[ \t]+/g, ' ')      
            .replace(/\n\s/g, '\n')       
            .replace(/\n{3,}/g, '\n\n')   
            .trim();
    }

    // --- 1. METADATA EXTRACTION (Keep existing logic) ---
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const json = JSON.parse(script.innerText);
            const graph = json['@graph'] || (Array.isArray(json) ? json : [json]);
            const jobPost = graph.find(item => item['@type'] === 'JobPosting');
            if (jobPost) {
                data.title = clean(jobPost.title) || data.title;
                data.company = clean(jobPost.hiringOrganization?.name) || data.company;
                data.location = clean(jobPost.jobLocation?.address?.addressLocality) || data.location;
            }
        } catch (e) {}
    }
    
    // Meta tag fallbacks
    const getMeta = (name) => document.querySelector(`meta[property="${name}"]`)?.content;
    const ogTitle = getMeta("og:title");
    if (data.title === "Unknown Title" && ogTitle) data.title = ogTitle.split('|')[0].trim();
    if (data.title === "Unknown Title") data.title = clean(document.querySelector('h1')?.innerText) || "Saved Job Page";

    // --- 2. DESCRIPTION EXTRACTION (The Prioritized List) ---
    
    // We list selectors in order of preference. 
    // The script will try the first one; if it fails, it tries the next.
    const selectors = [
        "#jobDescriptionText",           // Indeed (Main Body) - HIGHEST PRIORITY
        ".show-more-less-html__markup",  // LinkedIn (Main Body)
        ".job-description",              // Generic
        "[class*='job-description']",    // Generic fuzzy match
        "article",                       // Semantic HTML
    ];

    let contentNode = null;
    
    // Loop through our list and take the FIRST one that actually exists
    for (const sel of selectors) {
        const found = document.querySelector(sel);
        if (found) {
            contentNode = found;
            break; // We found the best one, stop looking!
        }
    }

    // Fallback: If absolutely nothing matched, grab the main page
    if (!contentNode) {
        contentNode = document.querySelector('main') || document.body;
        data.description = "⚠️ [Auto-Scraped Full Page]\n\n";
    }

    // Run the markdown converter on whatever we found
    data.description += htmlToMarkdown(contentNode);

    return data;
}
