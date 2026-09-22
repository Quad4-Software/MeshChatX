/**
 * Lazy client for micronRenderWorker. Keeps one worker, correlates
 * request/response by id, and reports permanent unavailability so callers
 * can fall back to the synchronous main-thread path.
 */

export interface RenderWorkerSegment {
    type: "html" | "partial";
    html?: string;
    line?: string;
}

interface PendingJob {
    resolve: (v: any) => void;
    reject: (e: any) => void;
    timer: ReturnType<typeof setTimeout>;
}

const JOB_TIMEOUT_MS = 30000;

let worker: Worker | null = null;
let workerFailed = false;
let nextId = 1;
const pending = new Map<number, PendingJob>();

function getWorker(): Worker {
    if (workerFailed) {
        throw new Error("render worker unavailable");
    }
    if (worker) {
        return worker;
    }
    if (typeof Worker === "undefined") {
        workerFailed = true;
        throw new Error("render worker unsupported");
    }
    worker = new Worker(new URL("./workers/micronRenderWorker.js", import.meta.url));
    worker.onerror = () => {
        workerFailed = true;
        flushAll(new Error("render worker crashed"));
    };
    worker.onmessage = (event: MessageEvent) => {
        const msg = event.data || {};
        const job = pending.get(msg.id);
        if (!job) {
            return;
        }
        pending.delete(msg.id);
        clearTimeout(job.timer);
        if (msg.ok) {
            job.resolve(msg);
        } else {
            job.reject(new Error(msg.error || "render worker job failed"));
        }
    };
    return worker;
}

function flushAll(err: Error) {
    for (const job of pending.values()) {
        clearTimeout(job.timer);
        job.reject(err);
    }
    pending.clear();
    if (worker) {
        try {
            worker.terminate();
        } catch {
            // terminate is best-effort
        }
        worker = null;
    }
}

function post(payload: Record<string, unknown>): Promise<any> {
    const w = getWorker();
    const id = nextId++;
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            pending.delete(id);
            reject(new Error("render worker job timed out"));
        }, JOB_TIMEOUT_MS);
        pending.set(id, { resolve, reject, timer });
        w.postMessage({ id, ...payload });
    });
}

/** Convert the mu segments of a micron document via worker-side WASM. */
export async function convertMicronWasmSegmentsInWorker(
    markup: string,
    darkTheme: boolean,
    forceMonospace: boolean,
): Promise<RenderWorkerSegment[]> {
    const res = await post({
        kind: "micron-wasm",
        markup,
        darkTheme,
        forceMonospace,
    });
    return res.segments as RenderWorkerSegment[];
}

/** marked.parse off-thread. Returns raw HTML; caller sanitizes. */
export async function renderMarkdownInWorker(markdown: string): Promise<string> {
    const res = await post({ kind: "markdown", markdown });
    return String(res.html ?? "");
}

/** Test hook: drop the worker so the next job starts fresh. */
export function terminateMicronRenderWorkerForTests() {
    flushAll(new Error("render worker terminated"));
    workerFailed = false;
}
