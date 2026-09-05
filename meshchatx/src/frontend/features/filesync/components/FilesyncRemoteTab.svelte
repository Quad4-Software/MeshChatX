<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatFileSize } from "../lib/filesyncFormat.js";
    import type { FilesyncPeer, FilesyncRemoteFile, FilesyncStatus } from "../lib/types.js";

    interface Props {
        status: FilesyncStatus;
        peers: FilesyncPeer[];
        browsePeerId: string;
        remoteFiles: FilesyncRemoteFile[];
        busy: boolean;
        onBrowse: () => void;
        onDownload: (path: string) => void;
    }

    let {
        status,
        peers = [],
        browsePeerId = $bindable(""),
        remoteFiles = [],
        busy,
        onBrowse,
        onDownload,
    }: Props = $props();

    function filePathOf(file: FilesyncRemoteFile): string {
        if (typeof file === "string") {
            return file;
        }
        return file.path || file.name || "";
    }

    function fileSizeOf(file: FilesyncRemoteFile): number | undefined {
        if (typeof file === "object" && file !== null && typeof file.size === "number") {
            return file.size;
        }
        return undefined;
    }
</script>

<div class="space-y-4">
    <p class="text-sm text-sem-fg-muted">{t("rns_filesync.remote_help")}</p>
    <div class="flex flex-col sm:flex-row gap-2">
        <select bind:value={browsePeerId} class="input-field flex-1 font-mono text-sm">
            <option value="">{t("rns_filesync.select_peer")}</option>
            {#each peers as peer (peer.peer_id)}
                <option value={peer.peer_id}>
                    {peer.peer_id}
                </option>
            {/each}
        </select>
        <button
            type="button"
            class="primary-chip px-4 py-2 text-sm cursor-pointer"
            disabled={busy || !status.running || !browsePeerId}
            onclick={onBrowse}
        >
            <MaterialDesignIcon iconName="folder-open-outline" class="w-4 h-4" />
            {t("rns_filesync.browse")}
        </button>
    </div>
    {#if remoteFiles.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("rns_filesync.no_remote_files")}
        </div>
    {:else}
        <ul class="space-y-2">
            {#each remoteFiles as file (filePathOf(file))}
                <li
                    class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
                >
                    <div class="min-w-0 text-sm break-all text-sem-fg">
                        {filePathOf(file)}
                        {#if fileSizeOf(file) != null}
                            <span class="text-xs text-sem-fg-muted">
                                · {formatFileSize(fileSizeOf(file))}
                            </span>
                        {/if}
                    </div>
                    <button
                        type="button"
                        class="secondary-chip px-3 py-1.5 text-sm cursor-pointer"
                        disabled={busy || !browsePeerId}
                        onclick={() => onDownload(filePathOf(file))}
                    >
                        {t("rns_filesync.download")}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>
