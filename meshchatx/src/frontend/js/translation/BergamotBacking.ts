// SPDX-License-Identifier: 0BSD

import { TranslatorBacking, type TranslatorBackingOptions } from "@browsermt/bergamot-translator";

export interface BergamotBackingOptions extends TranslatorBackingOptions {
    registryUrl?: string;
    workerUrl?: string;
}

interface PendingCall {
    accept: (value: unknown) => void;
    reject: (err: Error) => void;
    callsite: { message: string; stack?: string };
}

interface RegistryModelEntry {
    from: string;
    to: string;
    files: unknown;
}

function appBase(): string {
    const base = import.meta.env.BASE_URL || "/";
    const origin = typeof window !== "undefined" && window.location ? window.location.origin : "http://localhost";
    return `${origin}${base.replace(/\/?$/, "/")}`;
}

function absoluteUrl(path: string): string {
    return new URL(path, appBase()).href;
}

/**
 * TranslatorBacking wired to same-origin pack files and the vendored worker.
 * The registry and all model files are served by the local backend under
 * /translation-packs/; cross-origin fetches are refused.
 */
export class BergamotBacking extends TranslatorBacking {
    workerUrl: string;
    allowedOrigin: string | null;

    constructor(options: BergamotBackingOptions = {}) {
        super({
            ...options,
            cacheSize: options.cacheSize ?? 4096,
            useNativeIntGemm: options.useNativeIntGemm ?? true,
            registryUrl: absoluteUrl(options.registryUrl ?? "/translation-packs/registry.json"),
        });
        this.workerUrl = absoluteUrl(options.workerUrl ?? "/vendor/bergamot/translator-worker.js");
        this.allowedOrigin = typeof window !== "undefined" && window.location ? window.location.origin : null;
    }

    async loadModelRegistery(): Promise<RegistryModelEntry[]> {
        const response = await fetch(this.registryUrl, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error(`Failed to fetch translation registry: ${response.status}`);
        }
        const registry = (await response.json()) as Record<string, unknown>;
        return Object.entries(registry).map(([pair, pack]) => {
            const files =
                pack && typeof pack === "object" && "files" in pack ? (pack as { files: unknown }).files : pack;
            return {
                from: pair.slice(0, 2),
                to: pair.slice(2, 4),
                files,
            };
        });
    }

    async loadWorker(): Promise<{ worker: Worker; exports: unknown }> {
        const worker = new Worker(this.workerUrl, { type: "classic" });

        let serial = 0;
        const pending = new Map<number, PendingCall>();

        const call = (name: string, ...args: unknown[]) =>
            new Promise<unknown>((accept, reject) => {
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
            const { id, result, error } = data as {
                id: number;
                result: unknown;
                error?: { message?: string; stack?: string };
            };
            if (!pending.has(id)) {
                console.debug("Bergamot worker: unknown message id", id);
                return;
            }
            const entry = pending.get(id) as PendingCall;
            pending.delete(id);
            if (error !== undefined) {
                entry.reject(
                    Object.assign(new Error(), error, {
                        message: `${error.message} (response to ${entry.callsite.message})`,
                        stack: error.stack ? `${error.stack}\n${entry.callsite.stack}` : entry.callsite.stack,
                    })
                );
            } else {
                entry.accept(result);
            }
        });

        worker.addEventListener("error", (err) => this.onerror(err as unknown as Error));

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
                        return (...args: unknown[]) => call(String(name), ...args);
                    },
                }
            ),
        };
    }

    async fetch(url: string, checksum?: string, extra?: { signal?: AbortSignal }): Promise<ArrayBuffer> {
        const resolved = absoluteUrl(url);
        if (this.allowedOrigin && resolved.startsWith("http")) {
            const parsed = new URL(resolved);
            if (parsed.origin !== this.allowedOrigin) {
                throw new Error(`Refusing to fetch translation file from ${parsed.origin}`);
            }
        }
        const options: RequestInit = { credentials: "same-origin" };
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
