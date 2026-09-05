<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 6. Entry points into the docs and the authoring and exploration
     * pages. Docs links point at the bundled copies, not a hosted site.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    interface SmallCard {
        route: string;
        icon: string;
        color: string;
        titleKey: string;
        descKey: string;
    }

    const smallCards: SmallCard[] = [
        {
            route: "nomadnetwork",
            icon: "earth",
            color: "text-purple-500",
            titleKey: "tutorial.paper_messages",
            descKey: "tutorial.paper_messages_desc",
        },
        {
            route: "messages",
            icon: "message-text-outline",
            color: "text-green-500",
            titleKey: "tutorial.send_messages",
            descKey: "tutorial.send_messages_desc",
        },
        {
            route: "network-visualiser",
            icon: "hub",
            color: "text-teal-500",
            titleKey: "tutorial.explore_nodes",
            descKey: "tutorial.explore_nodes_desc",
        },
        {
            route: "call",
            icon: "phone-in-talk-outline",
            color: "text-red-500",
            titleKey: "tutorial.voice_calls",
            descKey: "tutorial.voice_calls_desc",
        },
    ];

    const bigCardClass = $derived(
        page
            ? "flex w-full flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation"
            : "flex w-full items-start gap-4 p-4 rounded-2xl bg-sem-surface-muted text-left border border-sem-border touch-manipulation"
    );

    const linkCardClass = $derived(
        page
            ? "flex w-full cursor-pointer flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 transition-colors dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation"
            : "flex w-full cursor-pointer items-start gap-4 p-4 rounded-2xl bg-sem-surface-muted text-left border border-sem-border transition-colors touch-manipulation min-h-[4.5rem]"
    );
</script>

<div class={page ? "space-y-8 py-10" : "space-y-6"} data-tutorial-step="learn">
    <div class="text-center {page ? 'space-y-4' : 'space-y-2'}">
        <h2 class="{page ? 'text-4xl font-black' : 'text-2xl font-bold'} text-sem-fg">
            {state.t("tutorial.learn_create")}
        </h2>
        <p class="text-sem-fg-muted {page ? 'text-xl max-w-2xl mx-auto' : ''}">
            {state.t(page ? "tutorial.learn_create_desc_page" : "tutorial.learn_create_desc")}
        </p>
    </div>

    <div class={page ? "space-y-8 px-2 sm:px-0" : "space-y-6"}>
        <div class="flex w-full flex-col {page ? 'gap-5 max-w-2xl' : 'gap-4 max-w-xl'} mx-auto">
            <div class={bigCardClass}>
                <div class="flex gap-4 sm:gap-5">
                    <MaterialDesignIcon
                        iconName="book-open-variant"
                        class="{page ? 'size-14' : 'size-8'} text-blue-500 shrink-0"
                    />
                    <div class="min-w-0 flex-1 text-left">
                        <div class="font-bold text-sem-fg {page ? 'text-xl sm:text-2xl mb-2' : ''}">
                            {state.t("tutorial.documentation")}
                        </div>
                        <p class={page ? "text-sem-fg-muted mb-6 text-base" : "text-sm text-sem-fg mb-2"}>
                            {state.t(page ? "tutorial.documentation_desc_page" : "tutorial.documentation_desc")}
                        </p>
                        <div class={page ? "flex flex-col gap-3" : "flex flex-wrap gap-2"}>
                            <a
                                href="/meshchatx-docs/index.html"
                                target="_blank"
                                rel="noreferrer"
                                class="bg-blue-600 text-white font-semibold shadow-xs transition-all hover:bg-blue-500 {page
                                    ? 'flex min-h-12 items-center justify-center rounded-xl px-4 py-3 text-base'
                                    : 'px-3 py-1 text-[10px] rounded-xl inline-block'}"
                            >
                                {state.t(page ? "tutorial.read_meshchatx_docs" : "tutorial.meshchatx_docs")}
                            </a>
                            <a
                                href={state.reticulumBundledDocsUrl}
                                target="_blank"
                                rel="noreferrer"
                                class="border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted font-semibold shadow-xs transition-all hover:bg-sem-surface-muted hover:border-blue-400 dark:hover:border-blue-500 {page
                                    ? 'flex min-h-12 items-center justify-center rounded-xl px-4 py-3 text-base'
                                    : 'px-3 py-1 text-[10px] rounded-xl inline-block'}"
                            >
                                {state.t(page ? "tutorial.reticulum_manual" : "tutorial.reticulum_docs")}
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class={bigCardClass}>
                <div class="flex gap-4 sm:gap-5">
                    <MaterialDesignIcon
                        iconName="file-document-edit-outline"
                        class="{page ? 'size-14' : 'size-8'} text-orange-500 shrink-0"
                    />
                    <div class="min-w-0 flex-1 text-left">
                        <div class="font-bold text-sem-fg {page ? 'text-xl sm:text-2xl mb-2' : ''}">
                            {state.t("tutorial.micron_editor")}
                        </div>
                        <p class={page ? "text-sem-fg-muted mb-6 text-base" : "text-sm text-sem-fg mb-2"}>
                            {state.t(page ? "tutorial.micron_editor_desc_page" : "tutorial.micron_editor_desc")}
                        </p>
                        <div class={page ? "flex flex-col gap-3 sm:flex-row" : "flex flex-wrap gap-2"}>
                            <button
                                type="button"
                                class={page
                                    ? "flex min-h-12 flex-1 items-center justify-center rounded-xl bg-orange-600 px-4 py-3 text-base font-semibold text-white transition-all hover:bg-orange-500"
                                    : "px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted font-semibold shadow-xs transition-all hover:bg-sem-surface-muted hover:border-blue-400 dark:hover:border-blue-500"}
                                onclick={() => state.gotoRoute("micron-editor")}
                            >
                                {state.t("tutorial.open_micron_editor")}
                            </button>
                            <button
                                type="button"
                                class={page
                                    ? "flex min-h-12 flex-1 items-center justify-center rounded-xl border border-gray-300 bg-white px-4 py-3 text-base font-semibold transition-all dark:border-zinc-700 dark:bg-zinc-800 text-sem-fg-muted hover:bg-sem-surface-muted"
                                    : "px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted font-semibold shadow-xs transition-all hover:bg-sem-surface-muted hover:border-blue-400 dark:hover:border-blue-500"}
                                onclick={() => state.gotoRoute("mesh-server")}
                            >
                                {state.t("tutorial.open_mesh_server")}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div
                class="{linkCardClass} hover:border-indigo-500"
                role="button"
                tabindex="0"
                onclick={() => state.gotoRoute("identities")}
                onkeydown={(event) => {
                    if (event.key === "Enter") {
                        state.gotoRoute("identities");
                    }
                }}
            >
                <div class="flex gap-4 sm:gap-5">
                    <MaterialDesignIcon
                        iconName="account-multiple-outline"
                        class="{page ? 'size-14' : 'size-8'} text-indigo-500 shrink-0"
                    />
                    <div class="min-w-0 flex-1 text-left">
                        <div class="font-bold text-sem-fg {page ? 'text-xl sm:text-2xl mb-2' : ''}">
                            {state.t("tutorial.identities_card_title")}
                        </div>
                        <p class="text-sem-fg-muted {page ? 'text-base' : 'text-sm'}">
                            {state.t(page ? "tutorial.identities_card_desc_page" : "tutorial.identities_card_desc")}
                        </p>
                    </div>
                </div>
            </div>

            <div
                class="{linkCardClass} hover:border-teal-500 {page ? 'min-h-[5rem]' : ''}"
                role="button"
                tabindex="0"
                onclick={() => state.gotoRoute("archives")}
                onkeydown={(event) => {
                    if (event.key === "Enter") {
                        state.gotoRoute("archives");
                    }
                }}
            >
                <div class="flex gap-4 sm:gap-5">
                    <MaterialDesignIcon
                        iconName="archive-outline"
                        class="{page ? 'size-14' : 'size-8'} text-teal-500 shrink-0"
                    />
                    <div class="min-w-0 flex-1 text-left">
                        <div class="font-bold text-sem-fg {page ? 'text-xl sm:text-2xl mb-2' : ''}">
                            {state.t("tutorial.archiver")}
                        </div>
                        <p class={page ? "text-sem-fg-muted text-base" : "text-sm text-sem-fg"}>
                            {state.t(page ? "tutorial.archiver_desc_page" : "tutorial.archiver_desc")}
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <p class="text-center font-semibold text-sem-fg-muted px-2 {page ? 'text-sm' : 'text-[11px] tracking-wide'}">
            {state.t("tutorial.learn_create_more")}
        </p>

        <div class="grid grid-cols-2 mx-auto {page ? 'gap-3 max-w-2xl px-1 sm:px-0' : 'gap-2 max-w-xl'}">
            {#each smallCards as card (card.route)}
                <div
                    class="flex cursor-pointer flex-col border border-gray-100 bg-gray-50 dark:border-zinc-800 dark:bg-zinc-900 transition-colors hover:border-blue-500 touch-manipulation {page
                        ? 'gap-2 rounded-2xl p-3 min-h-[6.5rem]'
                        : 'gap-1.5 rounded-xl p-2.5 min-h-[5.5rem]'}"
                    role="button"
                    tabindex="0"
                    onclick={() => state.gotoRoute(card.route)}
                    onkeydown={(event) => {
                        if (event.key === "Enter") {
                            state.gotoRoute(card.route);
                        }
                    }}
                >
                    <MaterialDesignIcon
                        iconName={card.icon}
                        class="{page ? 'size-7' : 'size-[22px]'} {card.color} shrink-0"
                    />
                    <div class="min-w-0">
                        <div class="font-bold text-sem-fg leading-tight {page ? 'text-xs sm:text-sm' : 'text-[11px]'}">
                            {state.t(card.titleKey)}
                        </div>
                        <div
                            class="text-sem-fg-muted leading-snug {page
                                ? 'text-[10px] sm:text-xs mt-1 line-clamp-4'
                                : 'text-[9px] line-clamp-3'}"
                        >
                            {state.t(card.descKey)}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    </div>
</div>
