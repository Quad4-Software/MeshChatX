<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { onMount } from "svelte";
    import "vis-network/styles/vis-network.css";
    import { DataSet } from "vis-data";
    import { Network } from "vis-network";
    import { SIEVE_PALETTE } from "../lib/constants";
    import type { SieveFolder, SieveFlowLabels, SieveRule } from "../lib/types";

    interface Props {
        filters?: SieveRule[];
        folders?: SieveFolder[];
        labels?: SieveFlowLabels;
    }

    let { filters = [], folders = [], labels = {} }: Props = $props();

    let hostEl = $state<HTMLDivElement | null>(null);
    let network: Network | null = null;

    function folderName(folderId: number | null): string {
        if (folderId == null) {
            return "";
        }
        const f = folders.find((x) => x.id === folderId);
        return f ? f.name : String(folderId);
    }

    function destroyNetwork(): void {
        if (network) {
            try {
                network.destroy();
            } catch {
                // Ignore destruction error on unmounted elements
            }
            network = null;
        }
    }

    function onResize(): void {
        try {
            network?.redraw();
            network?.fit({ animation: false });
        } catch (error) {
            console.warn("SieveFlowNetwork resize failed:", error);
            destroyNetwork();
        }
    }

    function rebuild(): void {
        try {
            destroyNetwork();
            if (!hostEl) {
                return;
            }
            const L = labels || {};
            const nodes: Array<Record<string, unknown>> = [];
            const edges: Array<Record<string, unknown>> = [];
            const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
            const ruleColors = isDark ? SIEVE_PALETTE.ruleDark : SIEVE_PALETTE.rule;

            nodes.push({
                id: "sieve-src",
                label: L.sourceNode || "Peers",
                title: L.sourceHint || "",
                level: 0,
                shape: "box",
                margin: 12,
                font: { color: SIEVE_PALETTE.src.font, multi: true },
                color: {
                    background: SIEVE_PALETTE.src.background,
                    border: SIEVE_PALETTE.src.border,
                    highlight: SIEVE_PALETTE.src,
                },
            });

            const enabled = (filters || []).filter((r) => r && r.enabled !== false);
            const outcomes = new Set<string>();

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
                const matchMsg = Boolean(rule.match_message);
                const modeLine =
                    rule.match_mode === "regex"
                        ? L.graphMatchModeRegex || "regex"
                        : L.graphMatchModeSubstring || "substring";
                const targetBits: string[] = [];
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
                let outColor: { background: string; border: string; font: string } = SIEVE_PALETTE.hide;
                const act = rule.action === "block" ? "hide" : rule.action;

                if (act === "ignore") {
                    outId = "sieve-out-ignore";
                    outLabel = L.ignore || "Ignore";
                    outColor = SIEVE_PALETTE.ignore;
                } else if (act === "banish") {
                    outId = "sieve-out-banish";
                    outLabel = L.banish || "Banish";
                    outColor = SIEVE_PALETTE.banish;
                } else if (act === "folder" && rule.folder_id != null) {
                    outId = `sieve-out-folder-${rule.folder_id}`;
                    outLabel = `${L.folder || "Folder"}:\n${folderName(rule.folder_id)}`;
                    outColor = SIEVE_PALETTE.folder;
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

            const data = { nodes: new DataSet(nodes as any), edges: new DataSet(edges as any) };
            network = new Network(hostEl, data as any, {
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
                edges: {
                    smooth: {
                        enabled: true,
                        type: "cubicBezier",
                        forceDirection: "horizontal",
                        roundness: 0.5,
                    },
                },
            });

            network.once("stabilizationIterationsDone", () => {
                network?.fit({ animation: false });
            });
        } catch (error) {
            console.warn("SieveFlowNetwork rebuild failed:", error);
            destroyNetwork();
        }
    }

    $effect(() => {
        // Track reactive dependencies
        const _ = [filters, folders, labels];
        rebuild();
    });

    onMount(() => {
        window.addEventListener("resize", onResize);
        return () => {
            window.removeEventListener("resize", onResize);
            destroyNetwork();
        };
    });
</script>

<div bind:this={hostEl} class="sieve-flow-host rounded-xl border border-sem-border bg-sem-surface"></div>

<style>
    .sieve-flow-host {
        width: 100%;
        height: min(420px, 55vh);
        min-height: 280px;
    }
</style>
