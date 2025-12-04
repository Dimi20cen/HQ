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
            statusDiv.innerText = `✅ Saved! (Total: ${resData.total_count})`;
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
    const getText = (selector) => {
        const el = document.querySelector(selector);
        return el ? el.innerText.trim() : "";
    };

    // Attempt to handle LinkedIn, Indeed, and generic sites
    let title = getText("h1") || getText(".job-title") || "Unknown Title";
    
    // LinkedIn specific selectors
    let company = getText(".job-details-jobs-unified-top-card__company-name") || 
                  getText(".topcard__org-name-link") || 
                  getText(".company-name") || "Unknown Company";
                  
    let location = getText(".job-details-jobs-unified-top-card__bullet") || 
                   getText(".topcard__flavor--bullet") || 
                   getText(".location") || "Unknown Location";

    return {
        title: title,
        company: company,
        location: location,
        url: window.location.href,
        date_scraped: new Date().toISOString()
    };
}
