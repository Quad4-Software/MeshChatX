<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import { onClickOutside } from "runed";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";

    let {
        isRecordingAudioAttachment = false,
        onstartrecording,
        onstoprecording,
        children,
    }: {
        isRecordingAudioAttachment?: boolean;
        onstartrecording?: (args: { codec: string; mode?: string }) => void;
        onstoprecording?: () => void;
        children?: Snippet;
    } = $props();

    let isShowingMenu = $state(false);
    let rootEl: HTMLDivElement | undefined = $state();

    function startRecording(args: { codec: string; mode?: string }) {
        isShowingMenu = false;
        onstartrecording?.(args);
    }

    onClickOutside(
        () => rootEl,
        () => {
            isShowingMenu = false;
        }
    );
</script>

<div bind:this={rootEl} class="relative inline-flex shrink-0">
    {#if isRecordingAudioAttachment}
        <button
            type="button"
            class="my-auto inline-flex items-center gap-x-1 rounded-full border border-sem-danger/40 bg-sem-danger/10 px-3 py-1.5 text-xs font-semibold text-sem-danger shadow-xs hover:border-sem-danger transition"
            onclick={() => {
                isShowingMenu = false;
                onstoprecording?.();
            }}
        >
            <MaterialDesignIcon iconName="microphone" class="w-4 h-4" />
            <span class="ml-1">
                {#if children}
                    {@render children()}
                {/if}
            </span>
        </button>
    {:else}
        <button
            type="button"
            class="my-auto inline-flex items-center justify-center rounded-lg size-8 text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg transition-colors"
            onclick={() => {
                isShowingMenu = true;
            }}
        >
            <MaterialDesignIcon iconName="microphone-plus" class="w-5 h-5" />
        </button>
    {/if}

    {#if isShowingMenu}
        <div
            class="absolute bottom-full right-0 z-10 mb-2 max-w-[min(20rem,calc(100vw-1.5rem))] rounded-xl bg-sem-surface shadow-lg ring-1 ring-sem-border focus:outline-hidden"
        >
            <div
                class="dropdown-caret pointer-events-none absolute -bottom-[5px] right-3 border-b border-r border-sem-border"
                aria-hidden="true"
            ></div>
            <div class="py-1">
                <button
                    type="button"
                    class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => startRecording({ codec: "codec2", mode: "1200" })}
                >
                    Low Quality - Codec2 (1200)
                </button>
                <button
                    type="button"
                    class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => startRecording({ codec: "codec2", mode: "3200" })}
                >
                    Medium Quality - Codec2 (3200)
                </button>
                <button
                    type="button"
                    class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => startRecording({ codec: "opus" })}
                >
                    High Quality - OPUS
                </button>
            </div>
        </div>
    {/if}
</div>
