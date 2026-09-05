<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import Skeleton from "../../../ui/svelte/Skeleton.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import type { Recording } from "../lib/types.js";

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
        active?: boolean;
        recordings?: (RecordingItem | Recording)[];
        recordingSearch?: string;
        playingRecordingId?: string | number | null;
        playingSide?: "rx" | "tx" | null;
        isLoading?: boolean;
        formatDestinationHash?: (hash?: string) => string;
        formatDateTime?: (timestampMs: number) => string;
        formatDuration?: (seconds: number) => string;
        onsearchinput?: (query: string) => void;
        onplay?: (recording: any, side: "rx" | "tx") => void;
        ondelete?: (recordingId: number | string) => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        active = true,
        recordings = [],
        recordingSearch = "",
        playingRecordingId = null,
        playingSide = null,
        isLoading = false,
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

    const transitionDuration = $derived(
        typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 120
    );
</script>

{#if active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2" transition:fade={{ duration: transitionDuration }}>
        <div class="mb-4">
            <div class="relative">
                <input
                    value={recordingSearch}
                    type="text"
                    placeholder={t("call.search_recordings")}
                    class="input-field w-full pl-10"
                    oninput={(e) => onsearchinput?.((e.target as HTMLInputElement).value)}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-sem-fg-muted" />
                </div>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto min-h-0">
            <div class="border-b border-sem-border overflow-hidden">
                {#if isLoading && recordings.length === 0}
                    <div class="space-y-4 p-4">
                        <div class="flex items-center gap-4">
                            <Skeleton variant="avatar" />
                            <div class="flex-1 space-y-2">
                                <Skeleton variant="line" class="w-1/3" />
                                <Skeleton variant="line" class="w-1/2" />
                            </div>
                        </div>
                        <div class="flex items-center gap-4">
                            <Skeleton variant="avatar" />
                            <div class="flex-1 space-y-2">
                                <Skeleton variant="line" class="w-1/4" />
                                <Skeleton variant="line" class="w-2/3" />
                            </div>
                        </div>
                    </div>
                {:else if recordings.length === 0}
                    <EmptyState
                        icon="microphone-off"
                        title={t("call.no_recordings")}
                        description={t("call.no_recordings_hint")}
                        class="my-auto py-12"
                    />
                {:else}
                    <ul class="divide-y divide-sem-border">
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
                                                class="size-10 rounded-full bg-sem-surface-muted flex items-center justify-center text-sem-fg-muted"
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
                                                {(recording as any).timestamp
                                                    ? formatDateTime(Number((recording as any).timestamp) * 1000)
                                                    : (recording as any).created_at
                                                      ? formatDateTime(
                                                            Date.parse(String((recording as any).created_at))
                                                        )
                                                      : ""}
                                            </span>
                                        </div>
                                        <div class="flex items-center text-xs text-sem-fg-muted space-x-3 mb-3">
                                            <span class="flex items-center gap-1">
                                                <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                                                {formatDuration(
                                                    Number(
                                                        (recording as any).duration_seconds ??
                                                            (recording as any).duration ??
                                                            0
                                                    )
                                                )}
                                            </span>
                                            <button
                                                type="button"
                                                class="opacity-60 font-mono text-[10px] truncate hover:text-sem-accent transition-colors cursor-pointer text-left focus-ring-sem"
                                                title={recording.remote_identity_hash}
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
                                                class="px-2 py-1 rounded-md bg-sem-accent-subtle hover:bg-sem-accent-subtle/80 text-sem-accent text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 focus-ring-sem cursor-pointer"
                                                onclick={() => onplay?.(recording, "rx")}
                                            >
                                                <MaterialDesignIcon
                                                    iconName={playingRecordingId === recording.id &&
                                                    playingSide === "rx"
                                                        ? "stop"
                                                        : "play"}
                                                    class="size-3"
                                                />
                                                {t("call.remote_rx")}
                                            </button>
                                            <!-- TX Play -->
                                            <button
                                                type="button"
                                                class="px-2 py-1 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 focus-ring-sem cursor-pointer"
                                                onclick={() => onplay?.(recording, "tx")}
                                            >
                                                <MaterialDesignIcon
                                                    iconName={playingRecordingId === recording.id &&
                                                    playingSide === "tx"
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
                                                class="p-1.5 text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem rounded-md"
                                                title={t("call.download_rx")}
                                            >
                                                <MaterialDesignIcon iconName="download" class="size-4" />
                                            </a>
                                            <!-- Download TX -->
                                            <a
                                                href={`/api/v1/telephone/recordings/${recording.id}/audio/tx`}
                                                download={`recording_${recording.id}_tx.opus`}
                                                class="p-1.5 text-sem-fg-muted hover:text-emerald-500 transition-colors focus-ring-sem rounded-md"
                                                title={t("call.download_tx")}
                                            >
                                                <MaterialDesignIcon iconName="download" class="size-4" />
                                            </a>
                                            <button
                                                type="button"
                                                class="p-1.5 text-sem-fg-muted hover:text-sem-danger transition-colors focus-ring-sem rounded-md cursor-pointer"
                                                title={t("call.delete")}
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
{/if}
