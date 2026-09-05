<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";

    interface RecordingItem {
        id: number | string;
        remote_identity_name?: string;
        remote_identity_hash?: string;
        timestamp?: number;
        duration_seconds?: number;
        remote_icon?: {
            icon_name?: string;
            foreground_colour?: string;
            background_colour?: string;
        };
        [key: string]: unknown;
    }

    interface Props {
        recordings?: RecordingItem[];
        recordingSearch?: string;
        playingRecordingId?: string | number | null;
        playingSide?: "rx" | "tx" | null;
        formatDestinationHash?: (hash?: string) => string;
        formatDateTime?: (timestampMs: number) => string;
        formatDuration?: (seconds: number) => string;
        onsearchinput?: (query: string) => void;
        onplay?: (recording: RecordingItem, side: "rx" | "tx") => void;
        ondelete?: (recordingId: number | string) => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        recordings = [],
        recordingSearch = "",
        playingRecordingId = null,
        playingSide = null,
        formatDestinationHash = (h?: string) => Utils.formatDestinationHash(h),
        formatDateTime = (ms: number) => Utils.convertUnixMillisToLocalDateTimeString(ms),
        formatDuration = (s: number) => Utils.formatMinutesSeconds(s),
        onsearchinput,
        onplay,
        ondelete,
        oncopyhash = (hash: string) => {
            if (typeof navigator !== "undefined" && navigator.clipboard) {
                void navigator.clipboard.writeText(hash);
            }
        },
    }: Props = $props();
</script>

<div class="flex-1 flex flex-col max-w-3xl mx-auto w-full">
    <div class="mb-4">
        <div class="relative">
            <input
                value={recordingSearch}
                type="text"
                placeholder={t("call.search_recordings")}
                class="block w-full rounded-lg border-0 py-2 pl-10 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                oninput={(e) => onsearchinput?.((e.target as HTMLInputElement).value)}
            />
            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <MaterialDesignIcon iconName="magnify" class="size-5 text-gray-400" />
            </div>
        </div>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0">
        <div class="border-b border-sem-border overflow-hidden">
            {#if recordings.length === 0}
                <div class="py-12 text-center">
                    <MaterialDesignIcon
                        iconName="microphone-off"
                        class="size-12 text-gray-300 dark:text-zinc-700 mx-auto mb-2"
                    />
                    <p class="text-sem-fg-muted text-sm">
                        {t("call.no_recordings")}
                    </p>
                </div>
            {:else}
                <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                    {#each recordings as recording (recording.id)}
                        <li class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors">
                            <div class="flex items-start space-x-4">
                                <div class="shrink-0">
                                    {#if recording.remote_icon}
                                        <LxmfUserIcon
                                            iconName={recording.remote_icon.icon_name}
                                            iconForegroundColour={recording.remote_icon.foreground_colour}
                                            iconBackgroundColour={recording.remote_icon.background_colour}
                                            iconClass="size-10"
                                        />
                                    {:else}
                                        <div
                                            class="size-10 rounded-full bg-sem-surface-muted flex items-center justify-center text-gray-400"
                                        >
                                            <MaterialDesignIcon iconName="account" class="size-6" />
                                        </div>
                                    {/if}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center justify-between mb-1">
                                        <p class="text-sm font-bold text-sem-fg truncate">
                                            {recording.remote_identity_name || t("call.unknown")}
                                        </p>
                                        <span class="text-[10px] text-sem-fg-muted font-mono">
                                            {recording.timestamp ? formatDateTime(recording.timestamp * 1000) : ""}
                                        </span>
                                    </div>
                                    <div class="flex items-center text-xs text-sem-fg-muted space-x-3 mb-3">
                                        <span class="flex items-center gap-1">
                                            <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                                            {formatDuration(recording.duration_seconds || 0)}
                                        </span>
                                        <button
                                            type="button"
                                            class="opacity-60 font-mono text-[10px] truncate hover:text-blue-500 transition-colors cursor-pointer text-left"
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                oncopyhash?.(recording.remote_identity_hash || "");
                                            }}
                                        >
                                            {formatDestinationHash(recording.remote_identity_hash)}
                                        </button>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <!-- RX Play -->
                                        <button
                                            type="button"
                                            class="px-2 py-1 rounded-md bg-blue-500/10 hover:bg-blue-500/20 text-sem-accent text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1"
                                            onclick={() => onplay?.(recording, "rx")}
                                        >
                                            <MaterialDesignIcon
                                                iconName={playingRecordingId === recording.id && playingSide === "rx"
                                                    ? "stop"
                                                    : "play"}
                                                class="size-3"
                                            />
                                            {t("call.remote_rx")}
                                        </button>
                                        <!-- TX Play -->
                                        <button
                                            type="button"
                                            class="px-2 py-1 rounded-md bg-green-500/10 hover:bg-green-500/20 text-green-600 dark:text-green-400 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1"
                                            onclick={() => onplay?.(recording, "tx")}
                                        >
                                            <MaterialDesignIcon
                                                iconName={playingRecordingId === recording.id && playingSide === "tx"
                                                    ? "stop"
                                                    : "play"}
                                                class="size-3"
                                            />
                                            {t("call.local_tx")}
                                        </button>
                                        <div class="flex-1"></div>
                                        <!-- Download RX -->
                                        <a
                                            href={`/api/v1/telephone/recordings/${recording.id}/audio/rx`}
                                            download={`recording_${recording.id}_rx.opus`}
                                            class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                            title={t("call.download_rx")}
                                        >
                                            <MaterialDesignIcon iconName="download" class="size-4" />
                                        </a>
                                        <!-- Download TX -->
                                        <a
                                            href={`/api/v1/telephone/recordings/${recording.id}/audio/tx`}
                                            download={`recording_${recording.id}_tx.opus`}
                                            class="p-1.5 text-gray-400 hover:text-green-500 transition-colors"
                                            title={t("call.download_tx")}
                                        >
                                            <MaterialDesignIcon iconName="download" class="size-4" />
                                        </a>
                                        <button
                                            type="button"
                                            class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                            onclick={() => ondelete?.(recording.id)}
                                        >
                                            <MaterialDesignIcon iconName="delete" class="size-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>
    </div>
</div>
