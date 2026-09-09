import { TranslatorBacking } from "@browsermt/bergamot-translator";

function appBase() {
    const base = import.meta.env.BASE_URL || "/";
    const origin = typeof window !== "undefined" && window.location ? window.location.origin : "http://localhost";
    return `${origin}${base.replace(/\/?$/, "/")}`;
}

function absoluteUrl(path) {
    return new URL(path, appBase()).href;
}

export class BergamotBacking extends TranslatorBacking {
    constructor(options = {}) {
        super({
            ...options,
            cacheSize: options.cacheSize ?? 4096,
            useNativeIntGemm: options.useNativeIntGemm ?? true,
            registryUrl: absoluteUrl(options.registryUrl ?? "/translation-packs/registry.json"),
        });
        this.workerUrl = absoluteUrl(options.workerUrl ?? "/vendor/bergamot/translator-worker.js");
        this.allowedOrigin = typeof window !== "undefined" && window.location ? window.location.origin : null;
    }

    async loadModelRegistery() {
        const response = await fetch(this.registryUrl, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error(`Failed to fetch translation registry: ${response.status}`);
        }
        const registry = await response.json();
        return Object.entries(registry).map(([pair, pack]) => {
            const files = pack && typeof pack === "object" && pack.files ? pack.files : pack;
            return {
                from: pair.slice(0, 2),
                to: pair.slice(2, 4),
                files,
            };
        });
    }

    async loadWorker() {
        const worker = new Worker(this.workerUrl, { type: "classic" });

        let serial = 0;
        const pending = new Map();

        const call = (name, ...args) =>
            new Promise((accept, reject) => {
                const id = ++serial;
                pending.set(id, {
                    accept,
                    reject,
                    callsite: {
                        message: `${name}(${args.map(String).join(", ")})`,
                        stack: new Error().stack,
                    },
                });
                worker.postMessage({ id, name, args });
            });

        worker.addEventListener("message", ({ data }) => {
            const { id, result, error } = data;
            if (!pending.has(id)) {
                console.debug("Bergamot worker: unknown message id", id);
                return;
            }
            const { accept, reject, callsite } = pending.get(id);
            pending.delete(id);
            if (error !== undefined) {
                reject(
                    Object.assign(new Error(), error, {
                        message: `${error.message} (response to ${callsite.message})`,
                        stack: error.stack ? `${error.stack}\n${callsite.stack}` : callsite.stack,
                    })
                );
            } else {
                accept(result);
            }
        });

        worker.addEventListener("error", (err) => this.onerror(err));

        await call("initialize", this.options);

        return {
            worker,
            exports: new Proxy(
                {},
                {
                    get(_target, name) {
                        if (name === "then") {
                            return undefined;
                        }
                        return (...args) => call(name, ...args);
                    },
                }
            ),
        };
    }

    async fetch(url, checksum, extra) {
        const resolved = absoluteUrl(url);
        if (this.allowedOrigin && resolved.startsWith("http")) {
            const parsed = new URL(resolved);
            if (parsed.origin !== this.allowedOrigin) {
                throw new Error(`Refusing to fetch translation file from ${parsed.origin}`);
            }
        }
        const options = { credentials: "same-origin" };
        if (extra?.signal) {
            options.signal = extra.signal;
        }
        if (checksum) {
            options.integrity = `sha256-${this.hexToBase64(checksum)}`;
        }
        const response = await fetch(resolved, options);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${url}: ${response.status}`);
        }
        return response.arrayBuffer();
    }
}
