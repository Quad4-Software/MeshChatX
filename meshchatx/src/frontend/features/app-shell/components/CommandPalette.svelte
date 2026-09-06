<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, tick } from "svelte";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { listCommands } from "../../../js/registries/commandRegistry.js";
    import type { CommandEntry } from "../../../js/registries/coreCommandEntries.js";
    import { navigate } from "../../../shell/hashRouter.js";
    import type { RouteTarget } from "../../../shell/hashRouter.js";
    import type { PeerAnnounce, Contact, ResultItem } from "../lib/commandPaletteTypes.js";
    import CommandPaletteResultRow from "./CommandPaletteResultRow.svelte";

    interface Props {
        isOpen?: boolean;
        onnavigate?: (route: RouteTarget) => void | Promise<void>;
        onexecuteaction?: () => void;
    }

    let { isOpen = $bindable(false), onnavigate, onexecuteaction }: Props = $props();

    let query = $state("");
    let rawHighlightedId = $state<string | null>(null);
    let peers = $state<PeerAnnounce[]>([]);
    let contacts = $state<Contact[]>([]);
    let inputRef: HTMLInputElement | undefined = $state(undefined);

    const actions = $derived(listCommands());

    const allResults = $derived.by(() => {
        const results: ResultItem[] = actions.map((action: CommandEntry) => ({
            id: action.id,
            title: t(`command_palette.${action.title}`),
            description: t(`command_palette.${action.description}`),
            icon: action.icon,
            type: action.type,
            route: action.route,
            action: action.action,
        }));

        if (Array.isArray(peers)) {
            for (const peer of peers) {
                results.push({
                    id: `peer-${peer.destination_hash}`,
                    title: peer.custom_display_name ?? peer.display_name ?? peer.destination_hash,
                    description: peer.destination_hash,
                    icon: peer.lxmf_user_icon?.icon_name ?? "account",
                    iconForeground: peer.lxmf_user_icon?.foreground_colour,
                    iconBackground: peer.lxmf_user_icon?.background_colour,
                    type: "peer",
                    peer,
                });
            }
        }

        if (Array.isArray(contacts)) {
            for (const contact of contacts) {
                results.push({
                    id: `contact-${contact.id}`,
                    title: contact.name,
                    description: `${t("app.call")} ${contact.remote_identity_hash}`,
                    icon: "phone",
                    type: "contact",
                    contact,
                });
            }
        }

        return results;
    });

    const filteredResults = $derived.by(() => {
        if (!query.trim()) {
            return allResults.filter((r) => r.type === "navigation" || r.type === "action");
        }
        const q = query.toLowerCase();
        return allResults.filter((r) => r.title.toLowerCase().includes(q) || r.description.toLowerCase().includes(q));
    });

    const highlightedId = $derived.by(() => {
        if (filteredResults.length === 0) return null;
        if (rawHighlightedId && filteredResults.some((r) => r.id === rawHighlightedId)) {
            return rawHighlightedId;
        }
        return filteredResults[0]?.id || null;
    });

    const groupedResults = $derived.by(() => {
        const groups: Record<string, ResultItem[]> = {};
        for (const result of filteredResults) {
            const groupName =
                result.type === "peer"
                    ? "group_recent"
                    : result.type === "contact"
                      ? "group_contacts"
                      : "group_actions";
            if (!groups[groupName]) {
                groups[groupName] = [];
            }
            groups[groupName].push(result);
        }
        return groups;
    });

    export async function open(): Promise<void> {
        query = "";
        rawHighlightedId = null;
        isOpen = true;
        void loadPeersAndContacts();
        await tick();
        inputRef?.focus();
    }

    export function close(): void {
        isOpen = false;
    }

    export async function toggle(): Promise<void> {
        if (isOpen) {
            close();
        } else {
            await open();
        }
    }

    export function getIsOpen(): boolean {
        return isOpen;
    }

    export function getFilteredResults(): ResultItem[] {
        return filteredResults;
    }

    export function getGroupedResults(): Record<string, ResultItem[]> {
        return groupedResults;
    }

    export function setQuery(val: string): void {
        query = val;
    }

    export function setPeers(val: PeerAnnounce[]): void {
        peers = val;
    }

    export function setContacts(val: Contact[]): void {
        contacts = val;
    }

    export function getHighlightedId(): string | null {
        return highlightedId;
    }

    export function setHighlightedId(val: string | null): void {
        rawHighlightedId = val;
    }

    async function loadPeersAndContacts(): Promise<void> {
        try {
            const api = (
                window as unknown as { api?: { get: (url: string, config?: unknown) => Promise<{ data: unknown }> } }
            ).api;
            if (!api) return;
            const peerResponse = await api.get("/api/v1/announces", {
                params: { aspect: "lxmf.delivery", limit: 20 },
            });
            const pData = peerResponse?.data as { announces?: PeerAnnounce[] } | undefined;
            peers = pData?.announces || [];

            const contactResponse = await api.get("/api/v1/telephone/contacts");
            const cData = contactResponse?.data as { contacts?: Contact[] } | Contact[] | undefined;
            if (Array.isArray(cData)) {
                contacts = cData;
            } else if (cData && Array.isArray(cData.contacts)) {
                contacts = cData.contacts;
            } else {
                contacts = [];
            }
        } catch (e) {
            console.error("Failed to load command palette data:", e);
        }
    }

    function handleGlobalKeydown(e: KeyboardEvent): void {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            e.stopPropagation();
            void toggle();
        }
    }

    if (typeof window !== "undefined") {
        window.addEventListener("keydown", handleGlobalKeydown, true);
        GlobalEmitter.on("open-command-palette", open);
    }

    onDestroy(() => {
        if (typeof window !== "undefined") {
            window.removeEventListener("keydown", handleGlobalKeydown, true);
            GlobalEmitter.off("open-command-palette", open);
        }
    });

    export function moveHighlight(step: number): void {
        const index = filteredResults.findIndex((r) => r.id === highlightedId);
        let nextIndex = index + step;
        if (nextIndex < 0) nextIndex = filteredResults.length - 1;
        if (nextIndex >= filteredResults.length) nextIndex = 0;
        if (filteredResults[nextIndex]) {
            rawHighlightedId = filteredResults[nextIndex].id;
        }
    }

    export function executeAction(direct = false): void {
        if (!direct && onexecuteaction) {
            onexecuteaction();
            return;
        }
        const result = filteredResults.find((r) => r.id === highlightedId);
        if (result) {
            void handleExecuteResult(result);
        }
    }

    export async function executeResult(result: ResultItem): Promise<void> {
        await handleExecuteResult(result);
    }

    async function handleExecuteResult(result: ResultItem): Promise<void> {
        close();
        if (result.type === "navigation") {
            if (onnavigate && result.route) {
                onnavigate(result.route);
            } else if (result.route) {
                void navigate(result.route);
            }
        } else if (result.type === "peer" && result.peer) {
            const peerRoute: RouteTarget = {
                name: "messages",
                params: { destinationHash: result.peer.destination_hash },
            };
            if (onnavigate) {
                onnavigate(peerRoute);
            } else {
                void navigate(peerRoute);
            }
        } else if (result.type === "contact" && result.contact) {
            void dialContact(result.contact.remote_identity_hash);
        } else if (result.type === "action") {
            if (result.action === "sync") {
                GlobalEmitter.emit("sync-propagation-node");
            } else if (result.action === "compose") {
                if (onnavigate) {
                    await Promise.resolve(onnavigate({ name: "messages" }));
                } else {
                    await navigate({ name: "messages" });
                }
                GlobalEmitter.emit("compose-new-message");
            } else if (result.action === "show-tutorial") {
                GlobalEmitter.emit("show-tutorial");
            } else if (result.action === "show-changelog") {
                GlobalEmitter.emit("show-changelog");
            }
        }
    }

    async function dialContact(hash: string): Promise<void> {
        try {
            const api = (window as unknown as { api?: { post: (url: string) => Promise<unknown> } }).api;
            if (api) {
                await api.post(`/api/v1/telephone/call/${hash}`);
            }
            if (onnavigate) {
                onnavigate({ name: "call" });
            } else {
                void navigate({ name: "call" });
            }
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || "Failed to initiate call");
        }
    }

    function onBackdropClick(e: MouseEvent): void {
        if (e.target === e.currentTarget) {
            close();
        }
    }
</script>

{#if isOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-200 flex items-start justify-center p-4 pt-[max(0.5rem,env(safe-area-inset-top))] bg-black/40 backdrop-blur-xs"
        onclick={onBackdropClick}
    >
        <div
            class="w-full max-w-2xl bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md rounded-2xl shadow-2xl border border-sem-border overflow-hidden flex flex-col max-h-[min(70dvh,70vh)] mt-2 sm:mt-8"
            role="dialog"
            aria-modal="true"
        >
            <!-- search input -->
            <div class="relative flex items-center p-4 border-b border-sem-border">
                <MaterialDesignIcon iconName="magnify" class="size-6 text-gray-400 mr-3" />
                <input
                    bind:this={inputRef}
                    bind:value={query}
                    type="text"
                    class="w-full bg-transparent border-none focus:ring-0 text-sem-fg placeholder-gray-400 text-lg outline-hidden"
                    placeholder={t("command_palette.search_placeholder")}
                    onkeydown={(e) => {
                        if (e.key === "ArrowDown" || e.keyCode === 40) {
                            e.preventDefault();
                            moveHighlight(1);
                        } else if (e.key === "ArrowUp" || e.keyCode === 38) {
                            e.preventDefault();
                            moveHighlight(-1);
                        } else if (e.key === "Enter" || e.keyCode === 13) {
                            e.preventDefault();
                            executeAction();
                        } else if (e.key === "Escape" || e.key === "Esc" || e.keyCode === 27) {
                            e.preventDefault();
                            close();
                        }
                    }}
                />
                <div class="flex items-center gap-1 ml-2">
                    <kbd
                        class="px-2 py-1 text-xs font-semibold text-gray-500 bg-sem-surface-muted border border-sem-border rounded-lg shadow-xs"
                    >
                        ESC
                    </kbd>
                </div>
            </div>

            <!-- results -->
            <div class="flex-1 overflow-y-auto p-2 min-h-0">
                {#if filteredResults.length === 0}
                    <div class="p-8 text-center text-sem-fg-muted">
                        {t("command_palette.no_results", { query })}
                    </div>
                {:else}
                    <div class="space-y-1">
                        {#each Object.entries(groupedResults) as [groupName, group] (groupName)}
                            <div>
                                <div class="px-3 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                                    {t(`command_palette.${groupName}`)}
                                </div>
                                {#each group as result (result.id)}
                                    <CommandPaletteResultRow
                                        {result}
                                        isHighlighted={highlightedId === result.id}
                                        onselect={executeResult}
                                        onhighlight={(id) => (rawHighlightedId = id)}
                                    />
                                {/each}
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            <!-- footer -->
            <div
                class="p-3 bg-gray-50/50 dark:bg-zinc-900/50 border-t border-sem-border flex justify-center gap-6 text-[10px] font-bold text-gray-400 uppercase tracking-widest"
            >
                <div class="flex items-center gap-1.5">
                    <kbd class="px-1.5 py-0.5 bg-white dark:bg-zinc-800 border border-sem-border rounded-xs shadow-xs">
                        &uarr;&darr;
                    </kbd>
                    <span>{t("command_palette.footer_navigate")}</span>
                </div>
                <div class="flex items-center gap-1.5">
                    <kbd class="px-1.5 py-0.5 bg-white dark:bg-zinc-800 border border-sem-border rounded-xs shadow-xs">
                        Enter
                    </kbd>
                    <span>{t("command_palette.footer_select")}</span>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    kbd {
        font-family: inherit;
    }
</style>
