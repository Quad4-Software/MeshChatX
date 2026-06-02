<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        ref="host"
        class="sieve-flow-host rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
    />
</template>

<script>
import "vis-network/styles/vis-network.css";
import { DataSet } from "vis-data";
import { Network } from "vis-network";

export default {
    name: "SieveFlowNetwork",
    props: {
        filters: {
            type: Array,
            default: () => [],
        },
        folders: {
            type: Array,
            default: () => [],
        },
        labels: {
            type: Object,
            default: () => ({}),
        },
    },
    data() {
        return {
            network: null,
        };
    },
    watch: {
        filters: {
            deep: true,
            handler() {
                this.rebuild();
            },
        },
        folders: {
            deep: true,
            handler() {
                this.rebuild();
            },
        },
        labels: {
            deep: true,
            handler() {
                this.rebuild();
            },
        },
    },
    mounted() {
        this.$nextTick(() => this.rebuild());
        window.addEventListener("resize", this.onResize);
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.onResize);
        this.destroyNetwork();
    },
    methods: {
        onResize() {
            try {
                this.network?.redraw();
                this.network?.fit({ animation: false });
            } catch (error) {
                console.warn("SieveFlowNetwork resize failed:", error);
                this.destroyNetwork();
            }
        },
        destroyNetwork() {
            if (this.network) {
                this.network.destroy();
                this.network = null;
            }
        },
        folderName(folderId) {
            const f = this.folders.find((x) => x.id === folderId);
            return f ? f.name : String(folderId);
        },
        rebuild() {
            try {
                this.destroyNetwork();
                const el = this.$refs.host;
                if (!el) {
                    return;
                }
                const L = this.labels || {};
                const nodes = [];
                const edges = [];
                const palette = {
                    src: { background: "#2563eb", border: "#1d4ed8", font: "#ffffff" },
                    rule: { background: "#f4f4f5", border: "#a1a1aa", font: "#18181b" },
                    ruleDark: { background: "#27272a", border: "#52525b", font: "#fafafa" },
                    hide: { background: "#b91c1c", border: "#991b1b", font: "#ffffff" },
                    ignore: { background: "#ca8a04", border: "#a16207", font: "#ffffff" },
                    folder: { background: "#15803d", border: "#166534", font: "#ffffff" },
                    banish: { background: "#4c1d95", border: "#5b21b6", font: "#ffffff" },
                };
                const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
                const ruleColors = isDark ? palette.ruleDark : palette.rule;

                nodes.push({
                    id: "sieve-src",
                    label: L.sourceNode || "Peers",
                    title: L.sourceHint || "",
                    level: 0,
                    shape: "box",
                    margin: 12,
                    font: { color: palette.src.font, multi: true },
                    color: {
                        background: palette.src.background,
                        border: palette.src.border,
                        highlight: palette.src,
                    },
                });

                const enabled = (this.filters || []).filter((r) => r && r.enabled !== false);
                const outcomes = new Set();

                enabled.forEach((rule, ruleIndex) => {
                    const rid = `sieve-rule-${rule.id || ruleIndex}`;
                    const sc = rule.scope === "contacts" || rule.scope === "non_contacts" ? rule.scope : "everyone";
                    const scopeLine =
                        sc === "contacts"
                            ? L.graphScopeContacts || "Contacts"
                            : sc === "non_contacts"
                              ? L.graphScopeNonContacts || "Non-contacts"
                              : L.graphScopeEveryone || "Everyone";
                    const terms = (rule.terms || []).slice(0, 4).join(", ");
                    const more = (rule.terms || []).length > 4 ? "…" : "";
                    const matchPeer = rule.match_peer_fields !== false;
                    const matchMsg = !!rule.match_message;
                    const modeLine =
                        rule.match_mode === "regex"
                            ? L.graphMatchModeRegex || "regex"
                            : L.graphMatchModeSubstring || "substring";
                    const targetBits = [];
                    if (matchPeer) {
                        targetBits.push(L.graphMatchPeer || "peer");
                    }
                    if (matchMsg) {
                        targetBits.push(L.graphMatchMessage || "msg");
                    }
                    const targetLine = targetBits.length ? targetBits.join("+") : L.graphMatchPeer || "peer";
                    nodes.push({
                        id: rid,
                        label: `${scopeLine}\n${targetLine} · ${modeLine}\n${L.rulePrefix || "If"}:\n${terms || "…"}${more}`,
                        title: (rule.terms || []).join("\n"),
                        level: 1,
                        shape: "box",
                        margin: 10,
                        font: { color: ruleColors.font, multi: true, size: 13 },
                        color: {
                            background: ruleColors.background,
                            border: ruleColors.border,
                            highlight: ruleColors,
                        },
                    });
                    edges.push({
                        from: "sieve-src",
                        to: rid,
                        arrows: "to",
                        color: { color: "#94a3b8" },
                    });

                    let outId = "sieve-out-hide";
                    let outLabel = L.hide || "Hide";
                    let outColor = palette.hide;
                    const act = rule.action === "block" ? "hide" : rule.action;
                    if (act === "ignore") {
                        outId = "sieve-out-ignore";
                        outLabel = L.ignore || "Ignore";
                        outColor = palette.ignore;
                    } else if (act === "banish") {
                        outId = "sieve-out-banish";
                        outLabel = L.banish || "Banish";
                        outColor = palette.banish;
                    } else if (act === "folder" && rule.folder_id != null) {
                        outId = `sieve-out-folder-${rule.folder_id}`;
                        outLabel = `${L.folder || "Folder"}:\n${this.folderName(rule.folder_id)}`;
                        outColor = palette.folder;
                    }
                    outcomes.add(
                        JSON.stringify({
                            id: outId,
                            label: outLabel,
                            bg: outColor.background,
                            bd: outColor.border,
                            fg: outColor.font,
                        })
                    );
                    edges.push({
                        from: rid,
                        to: outId,
                        arrows: "to",
                        color: { color: "#64748b" },
                    });
                });

                outcomes.forEach((enc) => {
                    const o = JSON.parse(enc);
                    nodes.push({
                        id: o.id,
                        label: o.label,
                        level: 2,
                        shape: "box",
                        margin: 12,
                        font: { color: o.fg, multi: true },
                        color: {
                            background: o.bg,
                            border: o.bd,
                            highlight: { background: o.bg, border: o.bd },
                        },
                    });
                });

                if (enabled.length === 0) {
                    nodes.push({
                        id: "sieve-out-none",
                        label: L.noRules || "No rules",
                        level: 2,
                        shape: "box",
                        margin: 12,
                        font: { color: "#64748b" },
                        color: { background: "#f1f5f9", border: "#cbd5e1" },
                    });
                    edges.push({
                        from: "sieve-src",
                        to: "sieve-out-none",
                        arrows: "to",
                        color: { color: "#94a3b8" },
                    });
                }

                const data = { nodes: new DataSet(nodes), edges: new DataSet(edges) };
                this.network = new Network(el, data, {
                    layout: {
                        hierarchical: {
                            direction: "LR",
                            sortMethod: "directed",
                            levelSeparation: 140,
                            nodeSpacing: 110,
                        },
                    },
                    physics: false,
                    interaction: { hover: true, zoomView: true, dragView: true },
                    edges: { smooth: { type: "cubicBezier", forceDirection: "horizontal" } },
                });
                this.network.once("stabilizationIterationsDone", () => {
                    this.network.fit({ animation: false });
                });
            } catch (error) {
                console.warn("SieveFlowNetwork rebuild failed:", error);
                this.destroyNetwork();
            }
        },
    },
};
</script>

<style scoped>
.sieve-flow-host {
    width: 100%;
    height: min(420px, 55vh);
    min-height: 280px;
}
</style>
