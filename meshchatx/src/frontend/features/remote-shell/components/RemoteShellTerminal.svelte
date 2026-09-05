<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RemoteShellSession } from "../lib/types.js";

    interface Props {
        session?: RemoteShellSession | null;
        output: string;
        commandInput?: string;
        listenAddress?: string;
        fullscreen?: boolean;
        showSessionsToggle?: boolean;
        sessionsOpen?: boolean;
        compactHeader?: boolean;
        i18nPrefix?: string;
        onupdateCommandInput?: (value: string) => void;
        onsend?: () => void;
        onstart?: () => void;
        onstop?: () => void;
        onclear?: () => void;
        onremove?: () => void;
        oncopyAddress?: () => void;
        ontoggleFullscreen?: () => void;
        ontoggleSessions?: () => void;
    }

    let {
        session = null,
        output,
        commandInput = "",
        listenAddress = "",
        fullscreen = false,
        showSessionsToggle = false,
        sessionsOpen = false,
        compactHeader = false,
        i18nPrefix = "rnsh",
        onupdateCommandInput,
        onsend,
        onstart,
        onstop,
        onclear,
        onremove,
        oncopyAddress,
        ontoggleFullscreen,
        ontoggleSessions,
    }: Props = $props();

    let outputBox = $state<HTMLDivElement | null>(null);

    function tKey(suffix: string): string {
        return t(`${i18nPrefix}.${suffix}`);
    }

    export function scrollToBottom(): void {
        if (outputBox) {
            outputBox.scrollTop = outputBox.scrollHeight;
        }
    }

    function handleInput(event: Event): void {
        const target = event.target as HTMLInputElement;
        onupdateCommandInput?.(target.value);
    }

    function handleSubmit(event: Event): void {
        event.preventDefault();
        onsend?.();
    }
</script>

<div class="flex flex-col min-h-0 flex-1 min-w-0" class:h-dvh={fullscreen} class:max-h-dvh={fullscreen}>
    <div
        class="shrink-0 flex flex-wrap items-center justify-between gap-1.5 sm:gap-2 border-b border-sem-border {fullscreen
            ? 'px-2 py-2 bg-zinc-900 safe-top'
            : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'}"
    >
        <div class="min-w-0 flex-1 flex items-center gap-1.5">
            {#if showSessionsToggle}
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem text-xs px-2 py-1.5 shrink-0 lg:hidden"
                    aria-label={sessionsOpen ? tKey("hide_sessions") : tKey("show_sessions")}
                    onclick={ontoggleSessions}
                >
                    <MaterialDesignIcon iconName="format-list-bulleted" class="size-4" />
                    <span class="hidden sm:inline">
                        {sessionsOpen ? tKey("hide_sessions") : tKey("show_sessions")}
                    </span>
                </button>
            {/if}
            <div class="min-w-0">
                <div class="text-xs sm:text-sm font-semibold text-sem-fg truncate">
                    {session?.name || tKey("session_output")}
                </div>
                {#if !compactHeader}
                    <div class="text-[10px] sm:text-xs text-sem-fg-muted font-mono truncate">
                        {session?.last_command || tKey("no_command_yet")}
                    </div>
                {/if}
            </div>
        </div>

        <div class="flex flex-wrap items-center gap-1 sm:gap-2 shrink-0">
            <button
                type="button"
                class="secondary-chip focus-ring-sem text-xs p-1.5 sm:px-2 sm:py-1.5"
                disabled={!session}
                title={tKey("start")}
                aria-label={tKey("start")}
                onclick={onstart}
            >
                <MaterialDesignIcon iconName="play" class="size-4" />
                <span class="hidden sm:inline ml-1">{tKey("start")}</span>
            </button>
            <button
                type="button"
                class="secondary-chip focus-ring-sem text-xs p-1.5 sm:px-2 sm:py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                disabled={!session}
                title={tKey("stop")}
                aria-label={tKey("stop")}
                onclick={onstop}
            >
                <MaterialDesignIcon iconName="stop" class="size-4" />
                <span class="hidden sm:inline ml-1">{tKey("stop")}</span>
            </button>
            <button
                type="button"
                class="secondary-chip focus-ring-sem text-xs p-1.5 sm:px-2 sm:py-1.5"
                disabled={!session}
                title={tKey("clear")}
                aria-label={tKey("clear")}
                onclick={onclear}
            >
                <MaterialDesignIcon iconName="broom" class="size-4" />
                <span class="hidden sm:inline ml-1">{tKey("clear")}</span>
            </button>
            <button
                type="button"
                class="secondary-chip focus-ring-sem text-xs p-1.5 sm:px-2 sm:py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                disabled={!session}
                title={tKey("remove")}
                aria-label={tKey("remove")}
                onclick={onremove}
            >
                <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                <span class="hidden sm:inline ml-1">{tKey("remove")}</span>
            </button>
            <button
                type="button"
                class="secondary-chip focus-ring-sem text-xs p-1.5 sm:px-2 sm:py-1.5"
                title={fullscreen ? tKey("exit_fullscreen") : tKey("fullscreen")}
                aria-label={fullscreen ? tKey("exit_fullscreen") : tKey("fullscreen")}
                onclick={ontoggleFullscreen}
            >
                <MaterialDesignIcon iconName={fullscreen ? "fullscreen-exit" : "fullscreen"} class="size-4" />
            </button>
        </div>
    </div>

    {#if session && session.mode === "listen"}
        <div
            class="shrink-0 flex items-center gap-2 px-2 sm:px-3 md:px-4 py-1.5 border-b border-sem-border bg-indigo-50 dark:bg-indigo-950/40"
        >
            <span
                class="text-[10px] sm:text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300 shrink-0"
            >
                {tKey("listening_on")}
            </span>
            <span class="min-w-0 flex-1 font-mono text-[11px] sm:text-xs text-sem-fg truncate">
                {listenAddress || tKey("waiting_for_address")}
            </span>
            {#if listenAddress}
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem text-xs p-1 sm:px-2 sm:py-1 shrink-0"
                    title={tKey("copy_address")}
                    aria-label={tKey("copy_address")}
                    onclick={oncopyAddress}
                >
                    <MaterialDesignIcon iconName="content-copy" class="size-4" />
                    <span class="hidden sm:inline ml-1">{tKey("copy_address")}</span>
                </button>
            {/if}
        </div>
    {/if}

    <div
        bind:this={outputBox}
        class="flex-1 min-h-0 bg-zinc-950 dark:bg-black text-zinc-100 font-mono whitespace-pre-wrap wrap-break-word overflow-auto custom-scrollbar {fullscreen
            ? 'text-[11px] leading-relaxed px-2 py-2'
            : 'text-xs px-2 sm:px-3 md:px-4 py-2 sm:py-3'}"
    >
        {output}
    </div>

    <form
        class="shrink-0 flex gap-1.5 sm:gap-2 border-t border-sem-border bg-sem-canvas {fullscreen
            ? 'px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] safe-bottom'
            : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'}"
        onsubmit={handleSubmit}
    >
        <input
            value={commandInput}
            type="text"
            class="input-field flex-1 min-w-0 font-mono text-xs"
            placeholder={tKey("command_input_placeholder")}
            disabled={!session}
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            oninput={handleInput}
        />
        <button
            type="submit"
            class="primary-chip focus-ring-sem px-2.5 sm:px-3 py-2 text-xs shrink-0"
            disabled={!session || !commandInput.trim()}
            aria-label={tKey("send_line")}
        >
            <MaterialDesignIcon iconName="send" class="size-4" />
            <span class="hidden sm:inline ml-1">{tKey("send_line")}</span>
        </button>
    </form>
</div>

<style>
    .safe-top {
        padding-top: max(0.5rem, env(safe-area-inset-top));
    }
    .safe-bottom {
        padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
    }
</style>
