// Standalone vision-judge: compare two screenshots (or one vs an intent
// description) and return a verdict. Provider-agnostic via llm.cjs.
//
// Usage:
//   node tests/agentic/vision-judge.cjs baseline.png candidate.png "intent text"
//   node tests/agentic/vision-judge.cjs --selftest page.png "what should be here"

const fs = require("fs");
const path = require("path");
const llm = require("./llm.cjs");

const VERDICT_PROMPT = `You are a UI regression judge. Compare the two screenshots.
The first is the baseline, the second is the candidate under test.
Intent of the change under test: {INTENT}

Classify the candidate:
- "regression": the candidate broke something the intent does not cover
- "intended": the differences match the stated intent
- "noise": only cosmetic drift (timestamps, fonts, animation frames)
- "flake": nondeterministic environment artifact

Reply ONLY as JSON:
{"verdict":"regression|intended|noise|flake","confidence":0-1,"regions":[{"area":"where","description":"what changed"}],"reasoning":"one sentence"}`;

const SELFTEST_PROMPT = `You are a UI reviewer. Look at this screenshot of an app page.
Expected content: {INTENT}
Does the page render this content correctly without clipping, overlap, blank areas, or visible errors?
Reply ONLY as JSON:
{"verdict":"pass|fail","confidence":0-1,"issues":["short description"],"reasoning":"one sentence"}`;

async function main() {
    const selftest = process.argv.includes("--selftest");
    const args = process.argv.slice(2).filter((a) => !a.startsWith("--"));
    if (args.length < 2) {
        console.error("usage: vision-judge.cjs [--selftest] baseline.png candidate.png [intent]");
        process.exit(2);
    }
    const [imgA, imgB, ...rest] = args;
    const intent = rest.join(" ") || "no stated intent";

    if (!llm.configured()) {
        console.error("no vision model configured (AGENTIC_VISION_MODEL / AGENTIC_LLM_*)");
        process.exit(3);
    }

    const shots = [];
    for (const p of selftest ? [imgA] : [imgA, imgB]) {
        const f = path.resolve(p);
        if (!fs.existsSync(f)) {
            console.error(`missing image: ${f}`);
            process.exit(2);
        }
        shots.push(fs.readFileSync(f).toString("base64"));
    }

    const prompt = (selftest ? SELFTEST_PROMPT : VERDICT_PROMPT).replace("{INTENT}", intent);
    const msgs = llm.imageMessage(prompt, shots);
    const verdict = await llm.chatJson(msgs, { model: llm.VISION_MODEL, temperature: 0 });
    console.log(JSON.stringify(verdict, null, 2));

    const fail = selftest ? verdict.verdict === "fail" : verdict.verdict === "regression";
    process.exit(fail ? 1 : 0);
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});
