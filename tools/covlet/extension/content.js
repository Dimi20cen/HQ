function cleanText(text) {
  return String(text || "")
    .replace(/\s+/g, " ")
    .replace(/\u00a0/g, " ")
    .trim();
}

function pickFirst(selectors) {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && cleanText(el.textContent)) return el;
  }
  return null;
}

function pickLongest(selectors) {
  let best = "";
  for (const sel of selectors) {
    document.querySelectorAll(sel).forEach((el) => {
      const text = cleanText(el.textContent);
      if (text.length > best.length) best = text;
    });
  }
  return best;
}

function expandDescription() {
  const buttons = Array.from(document.querySelectorAll("button"));
  buttons.forEach((btn) => {
    const label = cleanText(btn.getAttribute("aria-label"));
    const text = cleanText(btn.textContent);
    if (/see more|show more/i.test(label) || /see more|show more/i.test(text)) {
      try {
        btn.click();
      } catch {
        // ignore
      }
    }
  });
}

function parseFromTitle() {
  const title = document.title || "";
  // Example: "Software Engineer at Foo | LinkedIn"
  const match = title.match(/^(.*?)\s+at\s+(.*?)\s+\|/i);
  if (!match) return {};
  return {
    jobTitle: cleanText(match[1]),
    company: cleanText(match[2])
  };
}

function getJobData() {
  expandDescription();

  const titleEl = pickFirst([
    "h1.top-card-layout__title",
    "h1.jobs-unified-top-card__job-title",
    "h1"
  ]);

  const companyEl = pickFirst([
    "a.topcard__org-name-link",
    "a.topcard__flavor--black-link",
    "a.jobs-unified-top-card__company-name",
    "span.topcard__flavor",
    "span.jobs-unified-top-card__company-name"
  ]);

  const description = pickLongest([
    "div.jobs-description-content__text",
    "div.jobs-box__html-content",
    "div.show-more-less-html__markup",
    "div.jobs-description__content",
    "div#job-details",
    "div[data-testid='job-details']",
    "div[data-test-job-description]",
    "section.jobs-description",
    "div.description__text",
    "section.description",
    "article",
    "main"
  ]);

  const fallback = parseFromTitle();

  return {
    jobTitle: cleanText(titleEl ? titleEl.textContent : fallback.jobTitle),
    company: cleanText(companyEl ? companyEl.textContent : fallback.company),
    jobDescription: description
  };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "COVLET_GET_JOB_DATA") {
    try {
      const data = getJobData();
      sendResponse({ ok: true, data });
    } catch (err) {
      sendResponse({ ok: false, error: String(err.message || err) });
    }
  }
  return true;
});
