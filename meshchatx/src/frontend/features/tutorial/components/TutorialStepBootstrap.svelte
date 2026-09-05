<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 4. Choose bootstrap peers from the announced discovery list and the
     * bundled community list. Nothing is added until Confirm, and a skip path
     * exists because a mesh-only install may have neither list populated.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "../../../ui/svelte/Toggle.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    function discoveredKey(iface: { discovery_hash?: string; name: string }): string {
        return `disc:${iface.discovery_hash || iface.name}`;
    }
</script>

<div class={page ? "space-y-6 py-8" : "space-y-6"} data-tutorial-step="bootstrap">
    <div class="text-center space-y-2">
        <h2 class="{page ? 'text-3xl font-black' : 'text-2xl font-bold'} text-sem-fg">
            {state.t("tutorial.bootstrap_title")}
        </h2>
        <p class="text-sem-fg-muted {page ? 'text-lg max-w-3xl mx-auto' : 'text-sm'}">
            {state.t(page ? "tutorial.bootstrap_desc_page" : "tutorial.bootstrap_desc")}
        </p>
        <div class="flex flex-col items-center {page ? 'gap-3 pt-2' : 'gap-2 pt-1'}">
            <button
                type="button"
                class="inline-flex items-center gap-2 rounded-xl bg-blue-500/10 font-semibold text-blue-700 transition-colors hover:bg-blue-500/15 dark:text-blue-300 dark:hover:bg-blue-500/20 disabled:opacity-60 {page
                    ? 'border-2 border-blue-500/30 px-5 py-2.5 text-sm'
                    : 'border border-blue-500/30 px-4 py-2 text-xs'}"
                disabled={state.bootstrapPickBusy}
                onclick={() => void state.pickRandomTcpBootstraps()}
            >
                {#if state.bootstrapPickBusy}
                    <MaterialDesignIcon
                        iconName="loading"
                        class="{page ? 'size-[18px]' : 'size-4'} animate-spin text-blue-500"
                    />
                {:else}
                    <MaterialDesignIcon iconName="shuffle-variant" class={page ? "size-5" : "size-[18px]"} />
                {/if}
                {state.t("tutorial.bootstrap_pick_random_tcp")}
            </button>

            {#if state.bootstrapSelectedLabels.length > 0}
                <div
                    class="w-full rounded-xl border border-gray-200/90 bg-gray-50/80 text-left dark:border-zinc-700 dark:bg-zinc-900/50 {page
                        ? 'max-w-xl px-4 py-3'
                        : 'max-w-md px-3 py-2'}"
                >
                    <div class="{page ? 'text-xs' : 'text-[10px]'} font-bold uppercase tracking-wide text-sem-fg-muted">
                        {state.t("tutorial.bootstrap_selected_nodes_heading")}
                    </div>
                    <ul class="{page ? 'mt-1.5 space-y-1 text-sm' : 'mt-1 space-y-0.5 text-xs'} text-sem-fg">
                        {#each state.bootstrapSelectedLabels as label, index (state.selectedBootstrapKeys[index])}
                            <li>{label}</li>
                        {/each}
                    </ul>
                </div>
            {/if}
        </div>
    </div>

    <div
        class="flex items-start gap-3 rounded-2xl border border-sem-border bg-white/80 dark:bg-zinc-900/60 p-3.5 {page
            ? 'sm:gap-5 max-w-3xl mx-auto sm:p-5'
            : 'sm:gap-4 sm:p-4'}"
    >
        <div class="shrink-0 pr-0.5 pt-0.5 sm:pr-1 flex items-start {page ? 'sm:pt-1.5' : 'sm:pt-1'}">
            <Toggle
                id="tutorial-bootstrap-only"
                checked={state.defaultBootstrapOnly}
                onchange={(value) => void state.persistDefaultBootstrapOnly(value)}
            />
        </div>
        <div class="min-w-0 flex-1 pl-0.5 sm:pl-0 sm:pt-0.5">
            <div class="font-semibold text-sem-fg leading-snug {page ? 'text-sm sm:text-base' : 'text-sm'}">
                {state.t("tutorial.bootstrap_only_label")}
            </div>
            <p
                class="text-sem-fg-muted leading-relaxed {page
                    ? 'text-xs sm:text-sm mt-1.5 sm:mt-2'
                    : 'text-xs mt-1.5'}"
            >
                {state.t("tutorial.bootstrap_only_hint")}
            </p>
        </div>
    </div>

    <div class={page ? "" : "space-y-4"}>
        {#if state.hasAnyBootstrapsToShow}
            <div
                class="w-full max-w-6xl mx-auto flex items-center gap-2 border-0 border-b border-gray-200/90 dark:border-zinc-600/90 py-1.5 {page
                    ? ''
                    : 'mb-4'}"
            >
                <MaterialDesignIcon
                    iconName="magnify"
                    class="{page ? 'size-[22px]' : 'size-5'} shrink-0 text-gray-400"
                />
                <input
                    bind:value={state.bootstrapListSearch}
                    type="search"
                    autocomplete="off"
                    placeholder={state.t("tutorial.bootstrap_search_placeholder")}
                    class="min-w-0 flex-1 border-0 bg-transparent p-0 shadow-none ring-0 outline-hidden focus:ring-0 text-sem-fg placeholder:text-gray-400 dark:placeholder:text-zinc-500 {page
                        ? 'text-base'
                        : 'text-sm'}"
                />
                {#if state.bootstrapListSearch}
                    <button
                        type="button"
                        class="shrink-0 rounded text-gray-400 transition-colors hover:text-sem-fg {page
                            ? 'p-1.5'
                            : 'p-1'}"
                        title={state.t("tutorial.bootstrap_search_clear")}
                        aria-label={state.t("tutorial.bootstrap_search_clear")}
                        onclick={() => (state.bootstrapListSearch = "")}
                    >
                        <MaterialDesignIcon iconName="close" class={page ? "size-5" : "size-[18px]"} />
                    </button>
                {/if}
            </div>
        {/if}

        <div class={page ? "grid max-w-6xl mx-auto grid-cols-1 items-start gap-6 lg:grid-cols-2" : "space-y-4"}>
            {#if state.sortedDiscoveredInterfaces.length > 0}
                <div
                    class="h-fit min-w-0 bg-emerald-500/5 dark:bg-emerald-500/10 rounded-3xl border border-emerald-500/20"
                >
                    <button
                        type="button"
                        class="flex w-full items-center justify-between gap-2 p-4 text-left {page
                            ? 'sm:px-5'
                            : 'sm:px-4'}"
                        aria-expanded={state.bootstrapDiscoveredSectionOpen}
                        onclick={() => (state.bootstrapDiscoveredSectionOpen = !state.bootstrapDiscoveredSectionOpen)}
                    >
                        <div class="flex min-w-0 items-center {page ? 'gap-2.5 text-base' : 'gap-2 text-sm'}">
                            <MaterialDesignIcon
                                iconName={state.bootstrapDiscoveredSectionOpen ? "chevron-up" : "chevron-down"}
                                class="size-4 shrink-0 text-gray-500"
                            />
                            <MaterialDesignIcon iconName="radar" class="text-emerald-500 {page ? 'size-[22px]' : ''}" />
                            <span class="font-bold text-sem-fg">{state.t("tutorial.bootstrap_discovered")}</span>
                        </div>
                    </button>
                    {#if state.bootstrapDiscoveredSectionOpen}
                        <div class={page ? "px-4 pb-5 sm:px-5" : "px-4 pb-4"}>
                            {#if state.bootstrapListSearch && state.filteredDiscoveredForBootstrap.length === 0}
                                <p class="{page ? 'text-sm' : 'text-xs'} text-sem-fg-muted">
                                    {state.t("tutorial.bootstrap_search_no_match")}
                                </p>
                            {:else}
                                <div
                                    class="space-y-2 overflow-y-auto pr-2 pt-1 custom-scrollbar {page
                                        ? 'max-h-[480px]'
                                        : 'max-h-[260px]'}"
                                >
                                    {#each state.filteredDiscoveredForBootstrap as iface (iface.discovery_hash || iface.name)}
                                        <label
                                            class="flex cursor-pointer items-center gap-3 rounded-xl border bg-white p-3 transition-all dark:bg-zinc-800 {state.isBootstrapSelected(
                                                discoveredKey(iface)
                                            )
                                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                                : 'border-gray-100 dark:border-zinc-700 hover:border-emerald-400'}"
                                        >
                                            <input
                                                type="checkbox"
                                                class="h-4 w-4 accent-emerald-500"
                                                checked={state.isBootstrapSelected(discoveredKey(iface))}
                                                onchange={() => state.toggleBootstrap(discoveredKey(iface))}
                                            />
                                            <MaterialDesignIcon
                                                iconName={state.getDiscoveryIcon(iface)}
                                                class="h-5 w-5 shrink-0 text-emerald-500"
                                            />
                                            <div class="min-w-0 flex-1">
                                                <div class="truncate text-sm font-bold text-sem-fg">
                                                    {iface.name}
                                                </div>
                                                <div class="truncate font-mono text-[10px] text-sem-fg-muted">
                                                    {#if iface.reachable_on}
                                                        <span
                                                            >{iface.reachable_on}{#if iface.port}:{iface.port}{/if}</span
                                                        >
                                                    {:else}
                                                        <span>{iface.type}</span>
                                                    {/if}
                                                    <span class="ml-2 capitalize">{iface.status}</span>
                                                </div>
                                            </div>
                                        </label>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
            {/if}

            <div
                class="h-fit min-w-0 rounded-3xl border border-gray-100 bg-gray-50 p-0 dark:border-zinc-800 dark:bg-zinc-900 {page &&
                state.sortedDiscoveredInterfaces.length === 0
                    ? 'lg:col-span-2'
                    : ''}"
            >
                <div class="flex items-center justify-between gap-2 p-4 pr-2 {page ? 'sm:px-5' : 'sm:px-4'}">
                    <button
                        type="button"
                        class="flex min-w-0 flex-1 items-center text-left {page
                            ? 'gap-2.5 text-base'
                            : 'gap-2 text-sm'}"
                        aria-expanded={state.bootstrapCommunitySectionOpen}
                        onclick={() => (state.bootstrapCommunitySectionOpen = !state.bootstrapCommunitySectionOpen)}
                    >
                        <MaterialDesignIcon
                            iconName={state.bootstrapCommunitySectionOpen ? "chevron-up" : "chevron-down"}
                            class="size-4 shrink-0 text-gray-500"
                        />
                        <MaterialDesignIcon iconName="web" class="text-blue-500 {page ? 'size-[22px]' : ''}" />
                        <span class="font-bold text-sem-fg">{state.t("tutorial.bootstrap_community")}</span>
                    </button>
                </div>
                {#if state.bootstrapCommunitySectionOpen}
                    <div class={page ? "px-4 pb-5 sm:px-5" : "px-4 pb-4"}>
                        {#if state.bootstrapListSearch && state.communityInterfaces.length > 0 && state.filteredCommunityForBootstrap.length === 0}
                            <p class="{page ? 'text-sm' : 'text-xs'} text-sem-fg-muted">
                                {state.t("tutorial.bootstrap_search_no_match")}
                            </p>
                        {:else}
                            <div
                                class="space-y-2 overflow-y-auto pr-2 pt-1 custom-scrollbar {page
                                    ? 'max-h-[480px]'
                                    : 'max-h-[260px]'}"
                            >
                                {#each state.filteredCommunityForBootstrap as iface (iface.name)}
                                    <label
                                        class="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 transition-all dark:border-zinc-700 dark:bg-zinc-800 {state.isBootstrapSelected(
                                            `comm:${iface.name}`
                                        )
                                            ? 'border-blue-500 bg-sem-surface-muted'
                                            : 'hover:border-blue-400'}"
                                    >
                                        <input
                                            type="checkbox"
                                            class="h-4 w-4 accent-blue-500"
                                            checked={state.isBootstrapSelected(`comm:${iface.name}`)}
                                            onchange={() => state.toggleBootstrap(`comm:${iface.name}`)}
                                        />
                                        <MaterialDesignIcon
                                            iconName="server-network"
                                            class="text-blue-500 {page ? 'size-[22px]' : 'size-5'}"
                                        />
                                        <div class="min-w-0 flex-1">
                                            <div class="truncate text-sm font-bold text-sem-fg">
                                                {iface.name}
                                            </div>
                                            <div class="truncate font-mono text-[10px] text-sem-fg-muted">
                                                {iface.target_host}{#if iface.target_port}:{iface.target_port}{/if}
                                            </div>
                                        </div>
                                        {#if iface.online}
                                            <span
                                                class="shrink-0 text-[9px] font-bold uppercase tracking-widest text-green-500"
                                                >{state.t("tutorial.online")}</span
                                            >
                                        {/if}
                                    </label>
                                {/each}
                                {#if state.loadingInterfaces}
                                    <div class="flex justify-center py-3">
                                        <MaterialDesignIcon
                                            iconName="loading"
                                            class="size-6 animate-spin text-blue-500"
                                        />
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>

        <div
            class="flex flex-col sm:flex-row items-center justify-between {page
                ? 'gap-4 max-w-6xl mx-auto pt-4'
                : 'gap-3 pt-2'}"
        >
            <p class="{page ? 'text-sm' : 'text-xs'} text-sem-fg-muted">
                {state.t("tutorial.bootstrap_selected", { count: state.selectedBootstrapCount })}
            </p>
            <div class="flex {page ? 'gap-3' : 'gap-2'}">
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary"
                    disabled={state.bootstrapActionBusy}
                    onclick={() => state.skipBootstraps()}
                >
                    {state.t("tutorial.bootstrap_skip")}
                </button>
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-success"
                    disabled={state.bootstrapActionBusy || state.selectedBootstrapCount === 0}
                    onclick={() => void state.confirmBootstraps()}
                >
                    {#if state.bootstrapActionBusy}
                        <MaterialDesignIcon
                            iconName="loading"
                            class="{page ? 'size-4' : 'size-3.5'} animate-spin text-blue-500"
                        />
                    {/if}
                    {state.t("tutorial.bootstrap_confirm")}
                </button>
            </div>
        </div>
    </div>
</div>
