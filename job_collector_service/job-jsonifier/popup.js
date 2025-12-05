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
            // Fallback to "Saved!" if total_count isn't sent by server
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

// This function runs INSIDE the web page
function scrapeJobData() {
    const clean = (text) => text ? text.trim() : "";

    let data = {
        title: "Unknown Title",
        company: "Unknown Company",
        location: "Unknown Location",
        url: window.location.href,
        date_scraped: new Date().toISOString()
    };

    // --- STRATEGY 1: JSON-LD (The Gold Standard) ---
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const json = JSON.parse(script.innerText);
            const graph = json['@graph'] || (Array.isArray(json) ? json : [json]);
            const jobPost = graph.find(item => item['@type'] === 'JobPosting');
            
            if (jobPost) {
                data.title = clean(jobPost.title);
                data.company = clean(jobPost.hiringOrganization?.name);
                data.location = clean(jobPost.jobLocation?.address?.addressLocality || jobPost.jobLocation?.address?.region || "Remote");
                return data; // Trust JSON-LD and exit
            }
        } catch (e) { console.log("JSON-LD parse error", e); }
    }

    // --- STRATEGY 2: Meta Tags (The Backup) ---
    const getMeta = (name) => document.querySelector(`meta[property="${name}"]`)?.content;
    const ogTitle = getMeta("og:title");
    
    if (ogTitle) {
        // Clean up title: Remove " | LinkedIn", " | Indeed", etc.
        data.title = ogTitle.split('|')[0].trim(); 
        // Sometimes title is "Role at Company", try to extract company if missing
        if (data.title.includes(" at ")) {
             const parts = data.title.split(" at ");
             // If we still don't have a company, guess it from the title
             if (data.company === "Unknown Company" && parts.length > 1) {
                 data.company = parts[parts.length - 1];
             }
        }
    }

    // --- STRATEGY 3: CSS Selectors (The Last Resort) ---
    const getText = (s) => document.querySelector(s)?.innerText;
    
    if (data.title === "Unknown Title") {
        data.title = clean(getText("h1") || getText(".job-title"));
    }
    if (data.company === "Unknown Company") {
        data.company = clean(getText(".job-details-jobs-unified-top-card__company-name") || getText(".company-name"));
    }
    if (data.location === "Unknown Location") {
        data.location = clean(getText(".job-details-jobs-unified-top-card__bullet") || getText(".location"));
    }

    return data;
}
