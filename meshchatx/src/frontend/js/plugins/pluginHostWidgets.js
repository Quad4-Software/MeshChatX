// SPDX-License-Identifier: 0BSD

import { defineAsyncComponent, h } from "vue";

/** Reviewed host widgets plugins may request via manifest ui.widgets. */

export const HOST_WIDGET_NAMES = Object.freeze(["IssueStackView", "HashBadge"]);

/**
 * @param {string} name
 * @returns {boolean}
 */
export function isKnownHostWidget(name) {
    return HOST_WIDGET_NAMES.includes(name);
}

const IssueStackView = {
    name: "IssueStackView",
    props: {
        stack: { type: String, default: "" },
        maxHeight: { type: String, default: "16rem" },
    },
    setup(props) {
        return () =>
            h(
                "pre",
                {
                    class: "overflow-auto rounded-lg border border-sem-border bg-sem-surface-muted p-3 font-mono text-xs text-sem-fg whitespace-pre-wrap break-all",
                    style: { maxHeight: props.maxHeight },
                },
                props.stack || ""
            );
    },
};

const HashBadge = {
    name: "HashBadge",
    props: {
        hash: { type: String, default: "" },
        label: { type: String, default: "" },
    },
    setup(props) {
        return () => {
            const raw = props.hash || "";
            const short = raw.length >= 12 ? `${raw.slice(0, 10)}…${raw.slice(-6)}` : raw || "-";
            return h(
                "span",
                {
                    class: "inline-flex items-center gap-1.5 rounded-md border border-sem-border bg-sem-surface-muted px-2 py-0.5 font-mono text-xs text-sem-fg",
                    title: raw,
                },
                [props.label ? `${props.label} ` : "", short]
            );
        };
    },
};

const WIDGET_MAP = {
    IssueStackView,
    HashBadge,
};

/**
 * @param {string} name
 * @returns {import('vue').Component | null}
 */
export function resolveHostWidget(name) {
    return WIDGET_MAP[name] || null;
}

/**
 * Lazy stub kept for future heavier widgets.
 * @param {string} name
 */
export function resolveHostWidgetAsync(name) {
    const comp = resolveHostWidget(name);
    if (!comp) {
        return null;
    }
    return defineAsyncComponent(() => Promise.resolve(comp));
}
