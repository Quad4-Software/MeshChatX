// SPDX-License-Identifier: 0BSD

/**
 * Framework-free message lookup over svelte-i18n or a plain dictionary.
 * Pages and kernel code use t() from here.
 */

type TranslateFn = (key: string, values?: Record<string, unknown>) => string;

let translateFn: TranslateFn | null = null;
let fallbackMessages: Record<string, unknown> | null = null;

function lookupPath(key: string, messages: Record<string, unknown> | null): unknown {
    if (!messages || typeof messages !== "object") {
        return undefined;
    }
    const parts = String(key).split(".");
    let cur: unknown = messages;
    for (const part of parts) {
        if (cur == null || typeof cur !== "object") {
            return undefined;
        }
        cur = (cur as Record<string, unknown>)[part];
    }
    return cur;
}

function interpolate(template: string, values?: Record<string, unknown>): string {
    if (!values || typeof values !== "object") {
        return template;
    }
    return template.replace(/\{(\w+)\}/g, (_, name: string) => {
        if (Object.prototype.hasOwnProperty.call(values, name)) {
            return String(values[name]);
        }
        return `{${name}}`;
    });
}

export function registerTranslator(fn: TranslateFn | null | undefined): void {
    translateFn = typeof fn === "function" ? fn : null;
}

export function registerFallbackMessages(messages: Record<string, unknown> | null | undefined): void {
    fallbackMessages = messages && typeof messages === "object" ? messages : null;
}

export function t(key: string, values?: Record<string, unknown>): string {
    if (translateFn) {
        try {
            const out = translateFn(key, values);
            if (out != null && out !== "") {
                return String(out);
            }
        } catch {
            /* fall through */
        }
    }
    const found = lookupPath(key, fallbackMessages);
    if (typeof found === "string") {
        return interpolate(found, values);
    }
    return String(key);
}
