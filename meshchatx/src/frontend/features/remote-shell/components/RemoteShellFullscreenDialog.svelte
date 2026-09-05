<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import RemoteShellTerminal from "./RemoteShellTerminal.svelte";
    import type { RemoteShellSession } from "../lib/types.js";

    interface Props {
        session?: RemoteShellSession | null;
        output: string;
        commandInput: string;
        listenAddress: string;
        showSessionsToggle?: boolean;
        sessionsOpen?: boolean;
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
        commandInput,
        listenAddress,
        showSessionsToggle = false,
        sessionsOpen = false,
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

    let terminal = $state<ReturnType<typeof RemoteShellTerminal> | null>(null);

    export function scrollToBottom(): void {
        terminal?.scrollToBottom();
    }
</script>

<div
    class="fixed inset-0 z-[220] flex flex-col bg-zinc-950"
    role="dialog"
    aria-modal="true"
    aria-label={t(`${i18nPrefix}.session_output`)}
>
    <RemoteShellTerminal
        bind:this={terminal}
        {session}
        {output}
        {commandInput}
        {listenAddress}
        fullscreen
        {showSessionsToggle}
        {sessionsOpen}
        compactHeader
        {i18nPrefix}
        {onupdateCommandInput}
        {onsend}
        {onstart}
        {onstop}
        {onclear}
        {onremove}
        {oncopyAddress}
        {ontoggleFullscreen}
        {ontoggleSessions}
    />
</div>
