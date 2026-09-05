<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        showEmergency?: boolean;
        emergencyLabel?: string;
        showDemo?: boolean;
        demoLabel?: string;
        showWsDisconnected?: boolean;
        wsDisconnectedLabel?: string;
        showBackendRecoveryActions?: boolean;
        backendRestarting?: boolean;
        restartBackendLabel?: string;
        viewBackendLogsLabel?: string;
        showWsReconnected?: boolean;
        wsReconnectedLabel?: string;
        showNetworkStarting?: boolean;
        networkStartingLabel?: string;
        showLanBindNoAuth?: boolean;
        lanBindNoAuthLabel?: string;
        dismissLanBindNoAuthLabel?: string;
        showNetworkDegraded?: boolean;
        networkDegradedLabel?: string;
        networkRecovering?: boolean;
        recoverNetworkLabel?: string;
        openSettingsLabel?: string;
        showOpenBackups?: boolean;
        openBackupsLabel?: string;
        autoRecoverLabel?: string;
        autoRecovering?: boolean;
        openInterfacesLabel?: string;

        onrestartbackend?: () => void;
        onviewbackendlogs?: () => void;
        onrecovernetwork?: () => void;
        onopensettings?: () => void;
        ondismisslanbindnoauth?: () => void;
        onopenbackups?: () => void;
        onautorecoverdatabase?: () => void;
        onopeninterfaces?: () => void;
    }

    let {
        showEmergency = false,
        emergencyLabel = "",
        showDemo = false,
        demoLabel = "",
        showWsDisconnected = false,
        wsDisconnectedLabel = "",
        showBackendRecoveryActions = false,
        backendRestarting = false,
        restartBackendLabel = "",
        viewBackendLogsLabel = "",
        showWsReconnected = false,
        wsReconnectedLabel = "",
        showNetworkStarting = false,
        networkStartingLabel = "",
        showLanBindNoAuth = false,
        lanBindNoAuthLabel = "",
        dismissLanBindNoAuthLabel = "",
        showNetworkDegraded = false,
        networkDegradedLabel = "",
        networkRecovering = false,
        recoverNetworkLabel = "",
        openSettingsLabel = "",
        showOpenBackups = false,
        openBackupsLabel = "",
        autoRecoverLabel = "",
        autoRecovering = false,
        openInterfacesLabel = "",

        onrestartbackend,
        onviewbackendlogs,
        onrecovernetwork,
        onopensettings,
        ondismisslanbindnoauth,
        onopenbackups,
        onautorecoverdatabase,
        onopeninterfaces,
    }: Props = $props();
</script>

<div>
    {#if showEmergency}
        <div
            class="relative z-100 bg-red-600 text-white px-4 py-2 text-center text-sm font-bold shadow-md animate-pulse"
        >
            <div class="flex items-center justify-center gap-2">
                <MaterialDesignIcon iconName="alert-decagram" class="size-5" />
                <span>{emergencyLabel}</span>
            </div>
        </div>
    {/if}

    {#if showDemo}
        <div
            class="relative z-100 bg-amber-600 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-amber-700/80"
            role="status"
        >
            {demoLabel}
        </div>
    {/if}

    {#if showWsDisconnected}
        <div
            class="relative z-100 bg-red-700 text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-red-800/80"
            role="status"
            aria-live="polite"
        >
            <p>{wsDisconnectedLabel}</p>
            {#if showBackendRecoveryActions}
                <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <button
                        type="button"
                        class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                        disabled={backendRestarting}
                        onclick={() => onrestartbackend?.()}
                    >
                        {restartBackendLabel}
                    </button>
                    <button
                        type="button"
                        class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                        onclick={() => onviewbackendlogs?.()}
                    >
                        {viewBackendLogsLabel}
                    </button>
                </div>
            {/if}
        </div>
    {/if}

    {#if showWsReconnected}
        <div
            class="relative z-100 bg-emerald-700 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-emerald-800/80 transition-opacity duration-300"
            role="status"
            aria-live="polite"
        >
            {wsReconnectedLabel}
        </div>
    {/if}

    {#if showNetworkStarting}
        <div
            class="relative z-100 bg-sky-800 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-sky-900/80"
            role="status"
            aria-live="polite"
        >
            {networkStartingLabel}
        </div>
    {/if}

    {#if showLanBindNoAuth}
        <div
            class="relative z-100 bg-amber-700 text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-amber-800/80"
            role="status"
            aria-live="polite"
        >
            <p>{lanBindNoAuthLabel}</p>
            <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25"
                    onclick={() => onopensettings?.()}
                >
                    {openSettingsLabel}
                </button>
                <button
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    onclick={() => ondismisslanbindnoauth?.()}
                >
                    {dismissLanBindNoAuthLabel}
                </button>
            </div>
        </div>
    {/if}

    {#if showNetworkDegraded}
        <div
            class="relative z-100 bg-amber-700 text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-amber-800/80"
            role="status"
            aria-live="polite"
        >
            <p>{networkDegradedLabel}</p>
            <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                    disabled={networkRecovering}
                    onclick={() => onrecovernetwork?.()}
                >
                    {recoverNetworkLabel}
                </button>
                {#if !showOpenBackups}
                    <button
                        type="button"
                        class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                        onclick={() => onopensettings?.()}
                    >
                        {openSettingsLabel}
                    </button>
                {/if}
                {#if showOpenBackups}
                    <button
                        type="button"
                        class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                        disabled={autoRecovering}
                        onclick={() => onautorecoverdatabase?.()}
                    >
                        {autoRecoverLabel}
                    </button>
                    <button
                        type="button"
                        class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25"
                        onclick={() => onopenbackups?.()}
                    >
                        {openBackupsLabel}
                    </button>
                {/if}
                <button
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    onclick={() => onopeninterfaces?.()}
                >
                    {openInterfacesLabel}
                </button>
            </div>
        </div>
    {/if}
</div>
