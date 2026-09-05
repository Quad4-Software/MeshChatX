<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import AudioWaveformPlayer from "./AudioWaveformPlayer.svelte";

    type AudioAttachment = {
        audio_blob: Blob;
        audio_preview_url: string;
    };

    let {
        imageUrls = [] as string[],
        files = [] as File[],
        audio = null as AudioAttachment | null,
        onremoveimage,
        onremovefile,
        onremoveaudio,
        onopenimage,
    }: {
        imageUrls?: string[];
        files?: File[];
        audio?: AudioAttachment | null;
        onremoveimage?: (index: number) => void;
        onremovefile?: (file: File) => void;
        onremoveaudio?: () => void;
        onopenimage?: (url: string, gallery: string[]) => void;
    } = $props();

    const imageCount = $derived(imageUrls.length);
</script>

<div class="space-y-2 mb-2">
    {#if imageCount > 0}
        <div
            class="w-full max-w-[min(280px,100%)] rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-xs bg-black/5 dark:bg-white/5"
        >
            {#if imageCount === 1}
                <div class="relative group">
                    <button
                        type="button"
                        class="block w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-sem-focus"
                        onclick={(e) => {
                            e.stopPropagation();
                            onopenimage?.(imageUrls[0], imageUrls);
                        }}
                    >
                        <img
                            src={imageUrls[0]}
                            alt=""
                            class="max-h-52 w-full object-contain object-center bg-black/5 dark:bg-white/5"
                        />
                    </button>
                    <button
                        type="button"
                        class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-sem-surface border border-sem-border text-gray-600 dark:text-gray-200 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/40 shadow-md"
                        onclick={(e) => {
                            e.stopPropagation();
                            onremoveimage?.(0);
                        }}
                    >
                        <MaterialDesignIcon iconName="close" class="w-3.5 h-3.5" />
                    </button>
                </div>
            {:else}
                <div class="grid grid-cols-2 gap-0.5">
                    {#each imageUrls.slice(0, 4) as url, index (url + index)}
                        <div class="relative group {imageCount === 3 && index === 2 ? 'col-span-2' : ''}">
                            <button
                                type="button"
                                class="relative block {imageCount === 3 && index === 2
                                    ? 'aspect-2/1 max-h-44 min-h-[72px]'
                                    : 'aspect-square min-h-[88px]'} w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-sem-focus"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    onopenimage?.(url, imageUrls);
                                }}
                            >
                                <img src={url} alt="" class="h-full w-full object-cover" />
                                {#if index === 3 && imageCount > 4}
                                    <div
                                        class="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55 text-2xl font-bold text-white"
                                    >
                                        +{imageCount - 4}
                                    </div>
                                {/if}
                            </button>
                            <button
                                type="button"
                                class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    onremoveimage?.(index);
                                }}
                            >
                                <MaterialDesignIcon iconName="close" class="w-3.5 h-3.5" />
                            </button>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}

    {#if audio}
        <div class="attachment-card">
            <div class="attachment-card__body w-full">
                <div class="attachment-card__title">{t("messages.voice_note")}</div>
                <div class="attachment-card__meta mb-2">{Utils.formatBytes(audio.audio_blob.size)}</div>
                <AudioWaveformPlayer src={audio.audio_preview_url} isOutbound={true} />
            </div>
            <button type="button" class="attachment-card__remove" onclick={() => onremoveaudio?.()}>
                <MaterialDesignIcon iconName="delete" class="w-4 h-4" />
            </button>
        </div>
    {/if}

    {#if files.length > 0}
        <div class="flex flex-wrap gap-2">
            {#each files as file (file.name + file.size)}
                <div class="attachment-chip">
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon iconName="paperclip" class="w-4 h-4 text-gray-500 dark:text-gray-300" />
                        <div class="text-sm text-gray-800 dark:text-gray-200 truncate max-w-[160px]">{file.name}</div>
                        <span class="text-xs text-sem-fg-muted">{Utils.formatBytes(file.size)}</span>
                    </div>
                    <button type="button" class="attachment-chip__remove" onclick={() => onremovefile?.(file)}>
                        <MaterialDesignIcon iconName="close" class="w-3.5 h-3.5" />
                    </button>
                </div>
            {/each}
        </div>
    {/if}
</div>
