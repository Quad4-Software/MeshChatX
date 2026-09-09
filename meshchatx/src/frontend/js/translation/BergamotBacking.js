import { TranslatorBacking } from "@browsermt/bergamot-translator";

const BASE_URL = `${(import.meta.env.BASE_URL || "/").replace(/\/?$/, "/")}`;

export class BergamotBacking extends TranslatorBacking {
    constructor(options = {}) {
        super({
            ...options,
            cacheSize: options.cacheSize ?? 4096,
            useNativeIntGemm: options.useNativeIntGemm ?? true,
            registryUrl: options.registryUrl ?? `${BASE_URL}translation-packs/registry.json`,
        });
        this.workerUrl = options.workerUrl ?? `${BASE_URL}vendor/bergamot/translator-worker.js`;
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
                    }),
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
                },
            ),
        };
    }

    async fetch(url, checksum, extra) {
        // Same-origin local packs do not need credentials.
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error(`Failed to fetch ${url}: ${response.status}`);
        }
        return response.arrayBuffer();
    }
}
