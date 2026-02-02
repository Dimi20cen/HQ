#!/usr/bin/env node

const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawn } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const CONFIG_PATH = path.join(ROOT, "covlet.config.json");
const DEFAULT_PORT = 5055;
const DEFAULT_HOST = "127.0.0.1";

function loadConfig() {
  try {
    const raw = fs.readFileSync(CONFIG_PATH, "utf8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

const config = loadConfig();
function expandHome(value) {
  if (!value) return value;
  if (value === "~") return os.homedir();
  if (value.startsWith("~/")) return path.join(os.homedir(), value.slice(2));
  return value;
}
function resolveInfoFile(value) {
  if (!value) return path.join(ROOT, "info.md");
  const expanded = expandHome(value);
  if (path.isAbsolute(expanded)) return expanded;
  return path.resolve(ROOT, expanded);
}
const INFO_FILE = resolveInfoFile(process.env.COVLET_INFO_FILE || config.infoFile);
const OUTPUT_DIR = process.env.COVLET_OUTPUT_DIR || config.outputDir || "cover-letter";
const CONFIG_MODEL = config.model || "";
const CONFIG_REASONING_EFFORT = config.reasoningEffort || "";
const PORT = Number(process.env.COVLET_PORT) || DEFAULT_PORT;
const HOST = process.env.COVLET_HOST || DEFAULT_HOST;
const MODEL = process.env.COVLET_MODEL || CONFIG_MODEL || "";
const REASONING_EFFORT = process.env.COVLET_REASONING_EFFORT || CONFIG_REASONING_EFFORT || "";
const PROMPT_LOG = process.env.COVLET_PROMPT_LOG || path.join(os.tmpdir(), "covlet-last-prompt.txt");

function slugify(input) {
  return String(input || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "unknown-company";
}

function safeRead(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (err) {
    return null;
  }
}

function buildPrompt({ company, jobTitle, jobDescription, jobUrl, infoText }) {
  const parts = [];
  parts.push(
    "Write a tailored cover letter in plain text.",
    "Constraints:",
    "- Use only the provided info and job ad; do not invent details.",
    "- Keep it concise (120-170 words).",
    "- No placeholders.",
    "- Professional, warm tone.",
    "- No typical AI language; should feel human",
    "- Stick to facts; no over exaggeration",
    "- Output plain text only."
  );

  parts.push("\nCandidate info:\n" + infoText.trim());

  parts.push("\nJob context:");
  if (company) parts.push(`Company: ${company}`);
  if (jobTitle) parts.push(`Role: ${jobTitle}`);
  if (jobUrl) parts.push(`Job URL: ${jobUrl}`);
  if (jobDescription) parts.push("\nJob ad text:\n" + jobDescription.trim());

  return parts.join("\n");
}

function validateModelName(name) {
  if (!name) return null;
  const trimmed = String(name).trim();
  if (/(^|[\s-])((x)?high|medium|low)\b/i.test(trimmed)) {
    return `Model "${trimmed}" looks like it includes a reasoning-effort suffix. Use "gpt-5.2-codex" and set reasoningEffort separately.`;
  }
  return null;
}

function runCodex(prompt) {
  return new Promise((resolve, reject) => {
    const tmpOut = path.join(os.tmpdir(), `covlet-${Date.now()}.txt`);
    const args = ["exec", "--skip-git-repo-check", "--output-last-message", tmpOut];
    if (MODEL) {
      args.push("-m", MODEL);
    }
    if (REASONING_EFFORT) {
      args.push("-c", `model_reasoning_effort="${REASONING_EFFORT}"`);
    }
    args.push("-");

    const child = spawn("codex", args, { cwd: ROOT });

    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => reject(err));

    child.stdin.write(prompt);
    child.stdin.end();

    child.on("close", (code) => {
      if (code !== 0) {
        return reject(new Error(`codex exited with code ${code}: ${stderr.trim()}`));
      }
      const output = safeRead(tmpOut);
      if (!output) {
        return reject(new Error("codex output file missing"));
      }
      resolve(output.trim());
    });
  });
}

function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    return sendJson(res, 200, { ok: true });
  }

  if (req.method !== "POST" || req.url !== "/generate") {
    return sendJson(res, 404, { ok: false, error: "Not found" });
  }

  let raw = "";
  req.on("data", (chunk) => (raw += chunk));
  req.on("end", async () => {
    const requestStart = Date.now();
    let payload;
    try {
      payload = JSON.parse(raw || "{}");
    } catch {
      return sendJson(res, 400, { ok: false, error: "Invalid JSON" });
    }

    const infoText = safeRead(INFO_FILE);
    if (!infoText) {
      return sendJson(res, 500, { ok: false, error: `Missing info file: ${INFO_FILE}` });
    }

    const company = (payload.company || "").trim();
    const jobTitle = (payload.jobTitle || "").trim();
    const jobDescription = (payload.jobDescription || "").trim();
    const jobUrl = (payload.jobUrl || "").trim();

    if (!jobDescription) {
      return sendJson(res, 400, { ok: false, error: "Missing job description" });
    }

    const prompt = buildPrompt({ company, jobTitle, jobDescription, jobUrl, infoText });
    const warnings = [];
    const modelWarning = validateModelName(MODEL);
    if (modelWarning) warnings.push(modelWarning);
    if (warnings.length) {
      console.warn("covlet: warnings:", warnings.join(" | "));
    }
    try {
      fs.writeFileSync(PROMPT_LOG, prompt + "\n", "utf8");
    } catch {
      // ignore prompt log errors
    }

    try {
      const codexStart = Date.now();
      const letter = await runCodex(prompt);
      const codexMs = Date.now() - codexStart;
      const outputName = `${slugify(company || jobTitle || "job")}.txt`;
      const outputDir = path.resolve(ROOT, OUTPUT_DIR);
      fs.mkdirSync(outputDir, { recursive: true });
      const outputPath = path.join(outputDir, outputName);
      fs.writeFileSync(outputPath, letter + "\n", "utf8");

      const totalMs = Date.now() - requestStart;
      console.log(
        `covlet: generated ${outputName} in ${totalMs}ms (codex ${codexMs}ms)`
      );
      return sendJson(res, 200, {
        ok: true,
        outputPath,
        preview: letter.slice(0, 500),
        timingsMs: { total: totalMs, codex: codexMs },
        promptLogPath: PROMPT_LOG,
        warnings
      });
    } catch (err) {
      return sendJson(res, 500, { ok: false, error: String(err.message || err) });
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`covlet server listening on http://${HOST}:${PORT}`);
  console.log(`info file: ${INFO_FILE}`);
  console.log(`output dir: ${OUTPUT_DIR}`);
});
