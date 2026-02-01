const statusEl = document.getElementById("status");
const button = document.getElementById("generate");

function setStatus(text) {
  statusEl.textContent = text;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"]
  });
}

async function requestJobData(tabId) {
  return await chrome.tabs.sendMessage(tabId, { type: "COVLET_GET_JOB_DATA" });
}

async function generateCoverLetter() {
  button.disabled = true;
  setStatus("Reading job page...");

  const tab = await getActiveTab();
  if (!tab || !tab.url) {
    setStatus("Open a job page first.");
    button.disabled = false;
    return;
  }

  let response;
  try {
    await ensureContentScript(tab.id);
    response = await requestJobData(tab.id);
  } catch (err) {
    setStatus("Failed to read page. Reload and try again.");
    button.disabled = false;
    return;
  }

  if (!response || !response.ok) {
    setStatus(`Page parse failed: ${response?.error || "unknown"}`);
    button.disabled = false;
    return;
  }

  const { jobTitle, company, jobDescription } = response.data || {};
  if (!jobDescription) {
    setStatus("Could not find job description on this page.");
    button.disabled = false;
    return;
  }

  setStatus("Calling local server...");

  try {
    const res = await fetch("http://localhost:5055/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jobTitle,
        company,
        jobDescription,
        jobUrl: tab.url
      })
    });

    const data = await res.json();
    if (!data.ok) {
      setStatus(`Error: ${data.error}`);
    } else {
      const totalMs = data.timingsMs?.total;
      const codexMs = data.timingsMs?.codex;
      const promptLog = data.promptLogPath;
      const warnings = Array.isArray(data.warnings) ? data.warnings : [];
      const timingLine =
        typeof totalMs === "number"
          ? ` (${Math.round(totalMs / 1000)}s total` +
            (typeof codexMs === "number"
              ? `, ${Math.round(codexMs / 1000)}s codex`
              : "") +
            ")"
          : "";
      const promptLine = promptLog ? `\nPrompt: ${promptLog}` : "";
      const warningLine = warnings.length ? `\nWarning: ${warnings.join(" | ")}` : "";
      setStatus(`Saved: ${data.outputPath}${timingLine}${promptLine}${warningLine}`);
    }
  } catch (err) {
    setStatus("Server not running? Start it and try again.");
  } finally {
    button.disabled = false;
  }
}

button.addEventListener("click", generateCoverLetter);
