<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import LoadingState from "../../../ui/svelte/LoadingState.svelte";
    import { t } from "../../../js/i18n.js";
    import Utils from "../../../js/Utils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import GlobalState from "../../../js/GlobalState.js";
    import type { Conversation, Folder, Peer } from "../lib/types.js";

    type Props = {
        class?: string;
        sidebarPosition?: "left" | "right";
        collapsed?: boolean;
        conversations?: Conversation[];
        peers?: Record<string, Peer>;
        folders?: Folder[];
        selectedFolderId?: string | number | null;
        selectedDestinationHash?: string;
        conversationSearchTerm?: string;
        filterUnreadOnly?: boolean;
        filterFailedOnly?: boolean;
        filterHasAttachmentsOnly?: boolean;
        isLoading?: boolean;
        isLoadingMore?: boolean;
        hasMoreConversations?: boolean;
        isLoadingMoreAnnounces?: boolean;
        isSearchingAnnounces?: boolean;
        hasMoreAnnounces?: boolean;
        peersSearchTerm?: string;
        totalPeersCount?: number;
        pinnedPeerHashes?: string[];
        onconversationClick?: (c: Conversation) => void;
        onpeerClick?: (p: Peer) => void;
        onconversationSearchChanged?: (term: string) => void;
        onconversationFilterChanged?: (key: string) => void;
        onpeersSearchChanged?: (term: string) => void;
        oningestPaperMessage?: () => void;
        onloadMore?: () => void;
        onloadMoreAnnounces?: () => void;
        onannouncesTabActivated?: () => void;
        onfolderClick?: (id: string | number | null) => void;
        oncreateFolder?: (name: string) => void;
        onrenameFolder?: (payload: { id: string | number; name: string }) => void;
        ondeleteFolder?: (id: string | number) => void;
        onmoveToFolder?: (payload: { peer_hashes: string[]; folder_id: string | number | null }) => void;
        onbulkMarkAsRead?: (hashes: string[]) => void;
        onmarkAllAsRead?: () => void;
        onbulkDelete?: (hashes: string[]) => void;
        onexportFolders?: () => void;
        onimportFolders?: () => void;
        onmessagesImported?: () => void;
        ontoggleConversationPin?: (hash: string) => void;
        ontoggleCollapse?: () => void;
    };

    let {
        class: className = "",
        sidebarPosition = "left",
        collapsed = false,
        conversations = [],
        peers = {},
        folders = [],
        selectedFolderId = null,
        selectedDestinationHash = "",
        conversationSearchTerm = "",
        filterUnreadOnly = false,
        filterFailedOnly = false,
        filterHasAttachmentsOnly = false,
        isLoading = false,
        isLoadingMore = false,
        hasMoreConversations = false,
        isLoadingMoreAnnounces = false,
        isSearchingAnnounces = false,
        hasMoreAnnounces = false,
        peersSearchTerm = "",
        totalPeersCount = 0,
        pinnedPeerHashes = [],
        onconversationClick,
        onpeerClick,
        onconversationSearchChanged,
        onconversationFilterChanged,
        onpeersSearchChanged,
        oningestPaperMessage,
        onloadMore,
        onloadMoreAnnounces,
        onannouncesTabActivated,
        onfolderClick,
        oncreateFolder,
        onrenameFolder,
        ondeleteFolder,
        onexportFolders,
        onimportFolders,
        ontoggleConversationPin,
        ontoggleCollapse,
    }: Props = $props();

    let tab = $state<"conversations" | "announces">("conversations");
    let foldersExpanded = $state(true);
    let folderMenuShow = $state(false);
    let folderMenuRoot: HTMLDivElement | undefined = $state();

    const isRightSidebar = $derived(sidebarPosition === "right");
    const edgeBorderClass = $derived(isRightSidebar ? "border-l" : "border-r");
    const peerList = $derived(Object.values(peers || {}));
    const messageIconStyle = $derived.by(() => {
        const cfg = GlobalState.config as { message_icon_size?: number } | null | undefined;
        const size = Number(cfg?.message_icon_size) || 28;
        return { width: `${size}px`, height: `${size}px` };
    });
    const collapsedIconStyle = $derived({ width: "36px", height: "36px" });

    const sortedConversations = $derived.by(() => {
        const pinned = new Set(pinnedPeerHashes || []);
        const list = [...(conversations || [])];
        list.sort((a, b) => {
            const ap = pinned.has(a.destination_hash || "") ? 1 : 0;
            const bp = pinned.has(b.destination_hash || "") ? 1 : 0;
            if (ap !== bp) return bp - ap;
            const at = a.latest_message_created_at || 0;
            const bt = b.latest_message_created_at || 0;
            return Number(bt) - Number(at);
        });
        return list;
    });

    $effect(() => {
        if (tab === "announces") {
            onannouncesTabActivated?.();
        }
    });

    function displayName(row: Conversation | Peer): string {
        return String(row.custom_display_name || row.display_name || "Anonymous Peer");
    }

    function isPinned(hash: string | undefined): boolean {
        return Boolean(hash && pinnedPeerHashes.includes(hash));
    }

    function peerIconName(row: Conversation | Peer): string {
        return row.lxmf_user_icon?.icon_name || "";
    }

    function peerIconForeground(row: Conversation | Peer): string {
        return row.lxmf_user_icon?.foreground_colour || "";
    }

    function peerIconBackground(row: Conversation | Peer): string {
        return row.lxmf_user_icon?.background_colour || "";
    }

    function peerContactImage(row: Conversation | Peer): string {
        return row.contact_image || "";
    }

    function onConversationsScroll(event: Event) {
        const el = event.currentTarget as HTMLElement;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {
            onloadMore?.();
        }
    }

    function onAnnouncesScroll(event: Event) {
        const el = event.currentTarget as HTMLElement;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {
            onloadMoreAnnounces?.();
        }
    }

    async function createFolder() {
        const name = await DialogUtils.prompt(t("messages.enter_folder_name"), t("messages.new_folder"));
        if (name) oncreateFolder?.(String(name));
    }

    async function renameFolder(folder: Folder) {
        if (folder.id == null) return;
        const name = await DialogUtils.prompt(t("messages.rename_folder"), String(folder.name || ""));
        if (name && name !== folder.name) {
            onrenameFolder?.({ id: folder.id, name: String(name) });
        }
    }

    async function deleteFolder(folder: Folder) {
        if (folder.id == null) return;
        const confirmed = await DialogUtils.confirm(
            t("messages.delete_folder_confirm", { name: folder.name || "" }),
            t("messages.delete_folder")
        );
        if (confirmed) ondeleteFolder?.(folder.id);
    }

    $effect(() => {
        if (!folderMenuShow) return;
        const onDoc = (event: MouseEvent) => {
            if (folderMenuRoot && !folderMenuRoot.contains(event.target as Node)) {
                folderMenuShow = false;
            }
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

<aside
    class={[
        "flex flex-col h-full min-h-0 bg-sem-canvas shrink-0",
        collapsed ? "w-14" : "w-full sm:w-80",
        className,
    ].join(" ")}
>
    {#if collapsed}
        <div class={["flex flex-col h-full min-h-0 bg-sem-canvas border-sem-border", edgeBorderClass].join(" ")}>
            <div class="hidden sm:flex h-10 shrink-0 items-center justify-center border-b border-sem-border px-2">
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800 transition-colors"
                    onclick={() => ontoggleCollapse?.()}
                >
                    <MaterialDesignIcon iconName={isRightSidebar ? "chevron-left" : "chevron-right"} class="size-5" />
                </button>
            </div>
            <div class="flex flex-col items-center gap-1 py-2 px-1 border-b border-sem-border">
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors {tab === 'conversations'
                        ? 'bg-sem-accent text-white'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                    onclick={() => (tab = "conversations")}
                >
                    <MaterialDesignIcon iconName="message-text" class="size-6" />
                </button>
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors {tab === 'announces'
                        ? 'bg-sem-accent text-white'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                    onclick={() => (tab = "announces")}
                >
                    <MaterialDesignIcon iconName="account-search-outline" class="size-6" />
                </button>
            </div>
            {#if tab === "conversations"}
                <div
                    class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
                >
                    {#each sortedConversations.slice(0, 40) as c (c.destination_hash)}
                        <button
                            type="button"
                            class="shrink-0 p-0.5 rounded-xl transition-colors {selectedDestinationHash ===
                            c.destination_hash
                                ? 'ring-2 ring-sem-accent'
                                : 'hover:bg-white/10'}"
                            title={displayName(c)}
                            onclick={() => onconversationClick?.(c)}
                        >
                            <LxmfUserIcon
                                customImage={peerContactImage(c)}
                                iconName={peerIconName(c)}
                                iconForegroundColour={peerIconForeground(c)}
                                iconBackgroundColour={peerIconBackground(c)}
                                iconClass="shrink-0"
                                iconStyle={collapsedIconStyle}
                            />
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {:else}
        <div class={["bg-sem-canvas border-b border-sem-border", edgeBorderClass].join(" ")}>
            <div class="-mb-px flex h-10 min-w-0 items-stretch {isRightSidebar ? 'flex-row-reverse' : ''}">
                <div class="flex min-w-0 flex-1">
                    <button
                        type="button"
                        class="flex w-full cursor-pointer items-center justify-center border-b-2 px-1 text-center text-sm font-medium transition {tab ===
                        'conversations'
                            ? 'border-sem-accent text-sem-accent'
                            : 'border-transparent text-sem-fg-muted hover:border-sem-border hover:text-sem-fg'}"
                        onclick={() => (tab = "conversations")}
                    >
                        {t("messages.conversations")}
                    </button>
                    <button
                        type="button"
                        class="flex w-full cursor-pointer items-center justify-center border-b-2 px-1 text-center text-sm font-medium transition {tab ===
                        'announces'
                            ? 'border-sem-accent text-sem-accent'
                            : 'border-transparent text-sem-fg-muted hover:border-sem-border hover:text-sem-fg'}"
                        onclick={() => (tab = "announces")}
                    >
                        {t("messages.announces")}
                    </button>
                </div>
                <button
                    type="button"
                    class="hidden sm:flex shrink-0 items-center border-b-2 border-transparent px-1.5 text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800 transition-colors"
                    onclick={() => ontoggleCollapse?.()}
                >
                    <MaterialDesignIcon iconName={isRightSidebar ? "chevron-right" : "chevron-left"} class="size-5" />
                </button>
            </div>
        </div>

        {#if tab === "conversations"}
            <div
                class={[
                    "relative flex-1 flex flex-col bg-sem-canvas border-sem-border overflow-hidden min-h-0",
                    edgeBorderClass,
                ].join(" ")}
            >
                <div class="border-b border-sem-border bg-sem-canvas">
                    <div
                        class="flex cursor-pointer items-center justify-between px-3 py-2 transition-colors hover:bg-sem-surface-muted"
                    >
                        <button
                            type="button"
                            class="flex items-center gap-2 min-w-0 flex-1 text-left"
                            onclick={() => (foldersExpanded = !foldersExpanded)}
                        >
                            <MaterialDesignIcon
                                iconName={foldersExpanded ? "chevron-down" : "chevron-right"}
                                class="size-4 text-gray-400"
                            />
                            <span class="text-xs font-medium text-sem-fg-muted">{t("messages.folders")}</span>
                        </button>
                        <div class="flex gap-1 shrink-0">
                            <button
                                type="button"
                                class="p-1 text-gray-400 hover:text-sem-accent hover:bg-sem-surface-muted rounded-lg transition-colors"
                                title={t("messages.create_folder")}
                                onclick={(e) => {
                                    e.stopPropagation();
                                    void createFolder();
                                }}
                            >
                                <MaterialDesignIcon iconName="folder-plus-outline" class="size-4" />
                            </button>
                            <div bind:this={folderMenuRoot} class="relative">
                                <button
                                    type="button"
                                    class="p-1 text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted rounded-lg transition-colors"
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        folderMenuShow = !folderMenuShow;
                                    }}
                                >
                                    <MaterialDesignIcon iconName="dots-vertical" class="size-4" />
                                </button>
                                {#if folderMenuShow}
                                    <div
                                        class="absolute right-0 top-full mt-1 z-60 min-w-[160px] bg-sem-surface rounded-xl shadow-xl border border-sem-border py-1 overflow-hidden"
                                    >
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                                            onclick={() => {
                                                folderMenuShow = false;
                                                onexportFolders?.();
                                            }}
                                        >
                                            <MaterialDesignIcon iconName="export" class="size-4" />
                                            <span>{t("messages.export_folders")}</span>
                                        </button>
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                                            onclick={() => {
                                                folderMenuShow = false;
                                                onimportFolders?.();
                                            }}
                                        >
                                            <MaterialDesignIcon iconName="import" class="size-4" />
                                            <span>{t("messages.import_folders")}</span>
                                        </button>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                    {#if foldersExpanded}
                        <div class="flex flex-col max-h-48 overflow-y-auto overscroll-y-contain pb-1">
                            <button
                                type="button"
                                class="px-3 py-1.5 flex items-center gap-2 text-sm text-left transition-colors {selectedFolderId ===
                                null
                                    ? 'bg-sem-accent/15 text-sem-fg font-semibold'
                                    : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                                onclick={() => onfolderClick?.(null)}
                            >
                                <MaterialDesignIcon iconName="inbox-outline" class="size-4" />
                                <span class="truncate flex-1">{t("messages.all_messages")}</span>
                            </button>
                            {#each folders as folder (folder.id)}
                                <div
                                    class="group px-3 py-1.5 flex items-center gap-2 text-sm transition-colors {selectedFolderId ===
                                    folder.id
                                        ? 'bg-sem-accent/15 text-sem-fg font-semibold'
                                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                                >
                                    <button
                                        type="button"
                                        class="flex min-w-0 flex-1 items-center gap-2 text-left"
                                        onclick={() => onfolderClick?.(folder.id ?? null)}
                                    >
                                        <MaterialDesignIcon iconName="folder" class="size-4 shrink-0" />
                                        <span class="truncate flex-1">{folder.name || "Folder"}</span>
                                    </button>
                                    <div class="hidden group-hover:flex items-center gap-0.5 shrink-0">
                                        <button
                                            type="button"
                                            class="p-1 hover:text-sem-accent hover:bg-sem-surface-muted rounded-lg transition-colors"
                                            title={t("messages.rename_folder")}
                                            onclick={() => void renameFolder(folder)}
                                        >
                                            <MaterialDesignIcon iconName="pencil-outline" class="size-3.5" />
                                        </button>
                                        <button
                                            type="button"
                                            class="p-1 hover:text-red-500 hover:bg-sem-surface-muted rounded-lg transition-colors"
                                            title={t("messages.delete_folder")}
                                            onclick={() => void deleteFolder(folder)}
                                        >
                                            <MaterialDesignIcon iconName="trash-can-outline" class="size-3.5" />
                                        </button>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>

                <div class="p-2 border-b border-sem-border space-y-2">
                    <div class="flex gap-1">
                        <input
                            type="search"
                            class="input-field flex-1 min-w-0 text-sm"
                            value={conversationSearchTerm}
                            placeholder={t("messages.search_placeholder", {
                                count: conversations.length,
                            })}
                            oninput={(e) => onconversationSearchChanged?.((e.currentTarget as HTMLInputElement).value)}
                        />
                        <button
                            type="button"
                            class="p-2 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted"
                            title={t("messages.ingest_paper_message")}
                            onclick={() => oningestPaperMessage?.()}
                        >
                            <MaterialDesignIcon iconName="qrcode" class="size-5" />
                        </button>
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <button
                            type="button"
                            class="secondary-chip text-xs! py-1! px-2! {filterUnreadOnly
                                ? 'ring-1 ring-sem-accent'
                                : ''}"
                            onclick={() => onconversationFilterChanged?.("unread")}
                        >
                            {t("messages.unread")}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip text-xs! py-1! px-2! {filterFailedOnly
                                ? 'ring-1 ring-sem-accent'
                                : ''}"
                            onclick={() => onconversationFilterChanged?.("failed")}
                        >
                            {t("messages.failed")}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip text-xs! py-1! px-2! {filterHasAttachmentsOnly
                                ? 'ring-1 ring-sem-accent'
                                : ''}"
                            onclick={() => onconversationFilterChanged?.("attachments")}
                        >
                            {t("messages.attachments")}
                        </button>
                    </div>
                </div>

                <div class="flex-1 min-h-0 overflow-y-auto" onscroll={onConversationsScroll}>
                    {#if isLoading && conversations.length === 0}
                        <LoadingState />
                    {:else if conversations.length === 0}
                        <EmptyState
                            icon="message-text-outline"
                            title={t("messages.no_conversations") || "No conversations"}
                        />
                    {:else}
                        <ul class="divide-y divide-sem-border">
                            {#each sortedConversations as c (c.destination_hash)}
                                <li>
                                    <div
                                        class="group w-full text-left px-3 py-2 flex gap-2 items-center transition-colors hover:bg-sem-surface-muted {selectedDestinationHash ===
                                        c.destination_hash
                                            ? 'bg-sem-accent/10'
                                            : ''}"
                                    >
                                        <button
                                            type="button"
                                            class="flex min-w-0 flex-1 gap-2 items-center text-left"
                                            onclick={() => onconversationClick?.(c)}
                                        >
                                            <LxmfUserIcon
                                                customImage={peerContactImage(c)}
                                                iconName={peerIconName(c)}
                                                iconForegroundColour={peerIconForeground(c)}
                                                iconBackgroundColour={peerIconBackground(c)}
                                                iconClass="shrink-0"
                                                iconStyle={messageIconStyle}
                                            />
                                            <div class="min-w-0 flex-1">
                                                <div class="flex items-center gap-1">
                                                    <span class="truncate text-sm font-medium text-sem-fg"
                                                        >{displayName(c)}</span
                                                    >
                                                    {#if c.is_unread}
                                                        <span class="size-2 rounded-full bg-sem-accent shrink-0"></span>
                                                    {/if}
                                                </div>
                                                <div class="truncate text-xs text-sem-fg-muted mt-0.5">
                                                    {c.latest_message_preview ||
                                                        c.latest_message_title ||
                                                        Utils.formatDestinationHash(c.destination_hash || "")}
                                                </div>
                                            </div>
                                        </button>
                                        {#if c.destination_hash}
                                            <button
                                                type="button"
                                                class="p-1 text-sem-fg-muted hover:text-sem-fg rounded-lg transition-opacity opacity-0 group-hover:opacity-100 focus-visible:opacity-100 {selectedDestinationHash ===
                                                c.destination_hash
                                                    ? 'opacity-100'
                                                    : ''}"
                                                title={t("messages.pin_conversation")}
                                                onclick={() => ontoggleConversationPin?.(c.destination_hash || "")}
                                            >
                                                <MaterialDesignIcon
                                                    iconName={isPinned(c.destination_hash) ? "pin" : "pin-outline"}
                                                    class="size-4"
                                                />
                                            </button>
                                        {/if}
                                    </div>
                                </li>
                            {/each}
                        </ul>
                        {#if isLoadingMore}
                            <div class="p-3 text-center text-xs text-sem-fg-muted">{t("common.loading")}</div>
                        {:else if hasMoreConversations}
                            <button
                                type="button"
                                class="w-full p-3 text-xs text-sem-accent hover:bg-sem-surface-muted"
                                onclick={() => onloadMore?.()}
                            >
                                {t("common.load_more") || "Load more"}
                            </button>
                        {/if}
                    {/if}
                </div>
            </div>
        {:else}
            <div
                class={[
                    "relative flex-1 flex flex-col bg-sem-canvas border-sem-border overflow-hidden min-h-0",
                    edgeBorderClass,
                ].join(" ")}
            >
                <div class="p-2 border-b border-sem-border">
                    <input
                        type="search"
                        class="input-field w-full text-sm"
                        value={peersSearchTerm}
                        placeholder={t("messages.search_placeholder_announces", {
                            count: totalPeersCount,
                        })}
                        oninput={(e) => onpeersSearchChanged?.((e.currentTarget as HTMLInputElement).value)}
                    />
                </div>
                <div class="flex-1 min-h-0 overflow-y-auto" onscroll={onAnnouncesScroll}>
                    {#if isSearchingAnnounces && peerList.length === 0}
                        <LoadingState />
                    {:else if peerList.length === 0}
                        <EmptyState icon="account-search-outline" title={t("messages.no_peers_discovered")} />
                    {:else}
                        <ul class="divide-y divide-sem-border">
                            {#each peerList as p (p.destination_hash)}
                                <li>
                                    <button
                                        type="button"
                                        class="w-full text-left px-3 py-2 flex gap-2 items-center hover:bg-sem-surface-muted {selectedDestinationHash ===
                                        p.destination_hash
                                            ? 'bg-sem-accent/10'
                                            : ''}"
                                        onclick={() => onpeerClick?.(p)}
                                    >
                                        <LxmfUserIcon
                                            customImage={peerContactImage(p)}
                                            iconName={peerIconName(p)}
                                            iconForegroundColour={peerIconForeground(p)}
                                            iconBackgroundColour={peerIconBackground(p)}
                                            iconClass="shrink-0"
                                            iconStyle={messageIconStyle}
                                        />
                                        <div class="min-w-0 flex-1">
                                            <div class="truncate text-sm font-medium text-sem-fg">{displayName(p)}</div>
                                            <div class="truncate text-xs text-sem-fg-muted font-mono">
                                                {Utils.formatDestinationHash(p.destination_hash || "")}
                                            </div>
                                        </div>
                                    </button>
                                </li>
                            {/each}
                        </ul>
                        {#if isLoadingMoreAnnounces}
                            <div class="p-3 text-center text-xs text-sem-fg-muted">{t("common.loading")}</div>
                        {:else if hasMoreAnnounces}
                            <button
                                type="button"
                                class="w-full p-3 text-xs text-sem-accent hover:bg-sem-surface-muted"
                                onclick={() => onloadMoreAnnounces?.()}
                            >
                                {t("common.load_more") || "Load more"}
                            </button>
                        {/if}
                    {/if}
                </div>
            </div>
        {/if}
    {/if}
</aside>
