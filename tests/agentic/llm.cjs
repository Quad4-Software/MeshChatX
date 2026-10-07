// Provider-agnostic OpenAI-compatible chat client for agentic test legs.
//
// Env:
//   AGENTIC_LLM_BASE_URL   default http://127.0.0.1:11434/v1 (Ollama)
//   AGENTIC_LLM_API_KEY    bearer token, optional for local endpoints
//   AGENTIC_LLM_MODEL      text model, default llama3.1:8b
//   AGENTIC_VISION_MODEL   vision model, defaults to AGENTIC_LLM_MODEL
//   AGENTIC_LLM_TIMEOUT_MS request timeout, default 120000
//
// Works with Ollama, LM Studio, llama.cpp server, OpenRouter,
// OpenCode Console, or any /chat/completions compatible endpoint.

const BASE_URL = (process.env.AGENTIC_LLM_BASE_URL || "http://127.0.0.1:11434/v1").replace(/\/$/, "");
const API_KEY = process.env.AGENTIC_LLM_API_KEY || "";
const MODEL = process.env.AGENTIC_LLM_MODEL || "llama3.1:8b";
const VISION_MODEL = process.env.AGENTIC_VISION_MODEL || MODEL;
const TIMEOUT_MS = parseInt(process.env.AGENTIC_LLM_TIMEOUT_MS || "120000", 10);

function configured() {
    // A local default endpoint counts as configured. Remote endpoints need a key.
    if (/^(https?:\/\/)?(127\.|localhost|0\.0\.0\.0|\[::1\])/.test(BASE_URL)) {
        return true;
    }
    return Boolean(API_KEY);
}

async function chat(messages, { model, json = false, temperature = 0.2 } = {}) {
    if (!configured()) {
        throw new Error("agentic llm not configured (set AGENTIC_LLM_BASE_URL/API_KEY)");
    }
    const headers = { "content-type": "application/json" };
    if (API_KEY) {
        headers.authorization = `Bearer ${API_KEY}`;
    }
    const body = {
        model: model || MODEL,
        messages,
        temperature,
        stream: false,
    };
    if (json) {
        body.response_format = { type: "json_object" };
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
        const res = await fetch(`${BASE_URL}/chat/completions`, {
            method: "POST",
            headers,
            body: JSON.stringify(body),
            signal: ctrl.signal,
        });
        if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(`llm http ${res.status}: ${text.slice(0, 300)}`);
        }
        const data = await res.json();
        const msg = data.choices && data.choices[0] && data.choices[0].message;
        return (msg && msg.content) || "";
    } finally {
        clearTimeout(timer);
    }
}

async function chatJson(messages, opts = {}) {
    const text = await chat(messages, { ...opts, json: true });
    // Tolerate models that wrap JSON in prose or code fences.
    const m = text.match(/\{[\s\S]*\}/);
    if (!m) {
        throw new Error(`llm returned non-json: ${text.slice(0, 200)}`);
    }
    return JSON.parse(m[0]);
}

function imageMessage(prompt, base64Pngs) {
    const content = [{ type: "text", text: prompt }];
    for (const b64 of base64Pngs) {
        content.push({
            type: "image_url",
            image_url: { url: `data:image/png;base64,${b64}` },
        });
    }
    return [{ role: "user", content }];
}

module.exports = {
    BASE_URL,
    MODEL,
    VISION_MODEL,
    configured,
    chat,
    chatJson,
    imageMessage,
};
