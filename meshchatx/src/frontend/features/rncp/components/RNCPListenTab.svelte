<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        allowedHashes?: string;
        fetchJail?: string | null;
        fetchAllowed?: boolean;
        allowOverwrite?: boolean;
        receiveDirectory?: string | null;
        lastReceiveEvent?: { status: string; saved_path?: string; error?: string } | null;
        listenActive?: boolean;
        destinationHash?: string | null;
        listenResult?: { success: boolean; message: string } | null;
        onstart?: () => void;
        onstop?: () => void;
        onopenreceivedir?: () => void;
        onopenpath?: (path: string) => void;
    }

    let {
        allowedHashes = $bindable(""),
        fetchJail = $bindable<string | null>(null),
        fetchAllowed = $bindable(false),
        allowOverwrite = $bindable(false),
        receiveDirectory = null,
        lastReceiveEvent = null,
        listenActive = false,
        destinationHash = null,
        listenResult = null,
        onstart,
        onstop,
        onopenreceivedir,
        onopenpath,
    }: Props = $props();

    const listenHashesPlaceholder = "7b746057a7294469799cd8d7d429676a\n8c857168b830557080ad9e8e8e539787b";
</script>

<div class="space-y-4">
    <div>
        <label class="glass-label" for="rncp-listen-hashes">{t("rncp.allowed_hashes")}</label>
        <textarea
            id="rncp-listen-hashes"
            bind:value={allowedHashes}
            rows="4"
            placeholder={listenHashesPlaceholder}
            class="input-field font-mono text-sm"></textarea>
    </div>
    <div class="grid lg:grid-cols-2 gap-4">
        <div>
            <label class="glass-label" for="rncp-listen-jail">{t("rncp.fetch_jail_path")}</label>
            <input
                id="rncp-listen-jail"
                bind:value={fetchJail}
                type="text"
                placeholder="/path/to/jail"
                class="input-field"
            />
        </div>
        <div class="flex items-end gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
                <input bind:checked={fetchAllowed} type="checkbox" class="rounded-sm" />
                <span class="text-sm text-gray-700 dark:text-gray-300">{t("rncp.allow_fetch")}</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
                <input bind:checked={allowOverwrite} type="checkbox" class="rounded-sm" />
                <span class="text-sm text-gray-700 dark:text-gray-300">{t("rncp.allow_overwrite")}</span>
            </label>
        </div>
    </div>
    <p class="text-xs text-sem-fg-muted">
        {t("rncp.listening_active_background")}
    </p>
    {#if receiveDirectory}
        <div class="p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/80 border border-sem-border space-y-2">
            <div class="text-xs font-semibold text-sem-fg-muted">
                {t("rncp.receive_folder")}
            </div>
            <div class="font-mono text-xs break-all text-sem-fg">
                {receiveDirectory}
            </div>
            <button type="button" class="secondary-chip text-xs py-1.5 px-2 cursor-pointer" onclick={onopenreceivedir}>
                <MaterialDesignIcon iconName="folder-open-outline" class="w-4 h-4" />
                {t("rncp.open_folder")}
            </button>
        </div>
    {/if}
    {#if lastReceiveEvent}
        <div
            class="p-3 rounded-lg border space-y-2 {lastReceiveEvent.status === 'completed'
                ? 'bg-green-50/80 dark:bg-green-900/15 border-green-200 dark:border-green-800'
                : 'bg-amber-50/80 dark:bg-amber-900/15 border-amber-200 dark:border-amber-800'}"
        >
            <div class="text-sm font-semibold text-sem-fg">
                {lastReceiveEvent.status === "completed" ? t("rncp.received_file") : t("rncp.receive_failed")}
            </div>
            {#if lastReceiveEvent.saved_path}
                <div class="font-mono text-xs break-all">
                    {lastReceiveEvent.saved_path}
                </div>
            {/if}
            {#if lastReceiveEvent.error}
                <div class="text-xs text-red-600 dark:text-red-400">
                    {lastReceiveEvent.error}
                </div>
            {/if}
            {#if lastReceiveEvent.saved_path}
                <button
                    type="button"
                    class="secondary-chip text-xs py-1 px-2 cursor-pointer"
                    onclick={() => onopenpath?.(lastReceiveEvent?.saved_path || "")}
                >
                    {t("rncp.show_in_folder")}
                </button>
            {/if}
        </div>
    {/if}
    <div class="flex gap-2">
        {#if !listenActive}
            <button type="button" class="primary-chip px-4 py-2 text-sm cursor-pointer" onclick={onstart}>
                <MaterialDesignIcon iconName="play" class="w-4 h-4" />
                {t("rncp.start_listening")}
            </button>
        {:else}
            <button
                type="button"
                class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50 cursor-pointer"
                onclick={onstop}
            >
                <MaterialDesignIcon iconName="stop" class="w-4 h-4" />
                {t("rncp.stop_listening")}
            </button>
        {/if}
    </div>
    {#if destinationHash}
        <div class="p-3 rounded-lg bg-sem-surface-muted text-blue-700 dark:text-blue-300">
            <div class="font-semibold mb-1">{t("rncp.listening_on")}</div>
            <div class="font-mono text-sm">{destinationHash}</div>
        </div>
    {/if}
    {#if listenResult}
        <div
            class="p-3 rounded-lg {listenResult.success
                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}"
        >
            {listenResult.message}
        </div>
    {/if}
</div>

<style>
    .glass-label {
        display: block;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
</style>
