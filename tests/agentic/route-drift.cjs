// Route-coverage drift detector. No LLM needed.
//
// Compares the live Vue router table in meshchatx/src/frontend/main.js
// against the ROUTES arrays declared in the e2e crawl specs, and reports
// routes nobody crawls. Exits 1 when coverage has gaps so CI can flag it.

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const MAIN_JS = path.join(ROOT, "meshchatx/src/frontend/main.js");

// Specs whose ROUTES arrays count as crawl coverage.
const COVERED_SPECS = [
    "tests/e2e/exploratory-interactions.spec.js",
    "tests/e2e/exploratory.spec.js",
    "tests/e2e/routes.spec.js",
];

// Routes that are intentionally not crawl targets.
const IGNORED = new Set(["/", "/auth"]);
// Popout window routes and plugin-attached routes are out of crawl scope.
const IGNORED_PREFIX = ["/popout/", "/plugins/"];

function routerPaths() {
    const src = fs.readFileSync(MAIN_JS, "utf8");
    const out = new Set();
    for (const m of src.matchAll(/path:\s*"([^"]+)"/g)) {
        out.add(m[1]);
    }
    return out;
}

function specRoutes(rel) {
    const file = path.join(ROOT, rel);
    if (!fs.existsSync(file)) {
        return [];
    }
    const src = fs.readFileSync(file, "utf8");
    const routes = [];
    for (const m of src.matchAll(/const\s+ROUTES\s*=\s*\[([\s\S]*?)\];/g)) {
        for (const p of m[1].matchAll(/"(\/[^"]*)"/g)) {
            routes.push(p[1]);
        }
    }
    return routes;
}

// /messages/:destinationHash? -> /messages (crawls mount the bare route)
function normalize(p) {
    return p.replace(/\/:[^/]+\??/g, "").replace(/\/+$/, "") || "/";
}

function main() {
    const ignored = (p) => IGNORED.has(p) || IGNORED_PREFIX.some((x) => p.startsWith(x));
    const defined = [...routerPaths()].filter((p) => !ignored(p));
    const covered = new Set();
    for (const spec of COVERED_SPECS) {
        for (const r of specRoutes(spec)) {
            covered.add(r);
            covered.add(normalize(r));
        }
    }

    const uncovered = defined.filter((p) => !covered.has(p) && !covered.has(normalize(p)));
    const stale = [...covered].filter(
        (p) =>
            !ignored(p) &&
            !p.includes(":") &&
            !defined.includes(p) &&
            ![...defined].some((d) => normalize(d) === p),
    );

    console.log(`router paths: ${defined.length}, crawl-covered: ${covered.size}`);
    for (const p of uncovered) {
        console.log(`UNCOVERED ${p}`);
    }
    for (const p of stale) {
        console.log(`STALE (crawled but not in router) ${p}`);
    }

    if (uncovered.length || stale.length) {
        console.log("\nroute drift: coverage does not match router table");
        process.exit(1);
    }
    console.log("route drift: ok");
}

main();
