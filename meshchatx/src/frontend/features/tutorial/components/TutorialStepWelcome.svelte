<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 1. Welcome banner, the storage migration and Android storage
     * prompts that only a first run can answer, and the feature grid.
     */
    import logoUrl from "../../../assets/images/logo.png";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    interface FeatureCard {
        icon: string;
        color: string;
        titleKey: string;
        descKey: string;
        descPageKey: string;
    }

    const storageChoices = [
        {
            value: "external",
            titleKey: "android_storage.setup_external_title",
            descKey: "android_storage.setup_external_desc",
        },
        {
            value: "internal",
            titleKey: "android_storage.setup_internal_title",
            descKey: "android_storage.setup_internal_desc",
        },
    ];

    const featureCards: FeatureCard[] = [
        {
            icon: "shield-lock",
            color: "text-blue-500",
            titleKey: "tutorial.security",
            descKey: "tutorial.security_desc",
            descPageKey: "tutorial.security_desc_page",
        },
        {
            icon: "map-marker-path",
            color: "text-purple-500",
            titleKey: "tutorial.maps",
            descKey: "tutorial.maps_desc",
            descPageKey: "tutorial.maps_desc_page",
        },
        {
            icon: "phone",
            color: "text-green-500",
            titleKey: "tutorial.voice",
            descKey: "tutorial.voice_desc",
            descPageKey: "tutorial.voice_desc_page",
        },
        {
            icon: "tools",
            color: "text-orange-500",
            titleKey: "tutorial.tools",
            descKey: "tutorial.tools_desc",
            descPageKey: "tutorial.tools_desc_page",
        },
        {
            icon: "database-search",
            color: "text-teal-500",
            titleKey: "tutorial.archiver",
            descKey: "tutorial.archiver_desc",
            descPageKey: "tutorial.archiver_desc_page",
        },
        {
            icon: "account-cancel",
            color: "text-amber-500",
            titleKey: "tutorial.banishment",
            descKey: "tutorial.banishment_desc",
            descPageKey: "tutorial.banishment_desc",
        },
        {
            icon: "keyboard-outline",
            color: "text-red-500",
            titleKey: "tutorial.palette",
            descKey: "tutorial.palette_desc",
            descPageKey: "tutorial.palette_desc_page",
        },
        {
            icon: "translate",
            color: "text-cyan-500",
            titleKey: "tutorial.i18n",
            descKey: "tutorial.i18n_desc",
            descPageKey: "tutorial.i18n_desc_page",
        },
    ];
</script>

<div
    class="flex flex-col items-center text-center {page ? 'space-y-8 py-10' : 'space-y-6'}"
    data-tutorial-step="welcome"
>
    <div class="relative">
        <div class="{page ? 'w-32 h-32' : 'w-24 h-24'} bg-blue-500/10 rounded-3xl rotate-12 absolute -inset-2"></div>
        <img src={logoUrl} alt="MeshChatX" class="{page ? 'w-32 h-32' : 'w-24 h-24'} relative z-10 p-2" />
    </div>
    <div class={page ? "space-y-4" : "space-y-2"}>
        <h1 class="{page ? 'text-5xl' : 'text-4xl'} font-black tracking-tight text-sem-fg">
            {state.t("tutorial.welcome")} <span class="text-blue-500">MeshChatX</span>
        </h1>
        <p class="{page ? 'text-xl max-w-2xl' : 'text-lg max-w-md'} text-sem-fg-muted mx-auto">
            {state.t("tutorial.welcome_desc")}
        </p>
    </div>

    {#if state.migrationOffer && state.migrationOffer.show_choice}
        <div
            class="w-full {page
                ? 'max-w-2xl p-5'
                : 'max-w-xl p-4'} mx-auto rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 text-left space-y-3"
        >
            <div class="font-semibold text-amber-950 dark:text-amber-100">
                {state.t("tutorial.migration_title")}
            </div>
            <p class="text-sm text-amber-950/90 dark:text-amber-100/90">
                {state.t("tutorial.migration_desc")}
            </p>
            <div class="flex flex-col sm:flex-row gap-2 justify-stretch sm:justify-end">
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-primary"
                    disabled={state.migrationBusy}
                    onclick={() => void state.migrationMigrate()}
                >
                    {state.t("tutorial.migration_migrate")}
                </button>
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary"
                    disabled={state.migrationBusy}
                    onclick={() => void state.migrationFresh()}
                >
                    {state.t("tutorial.migration_fresh")}
                </button>
            </div>
            {#if state.migrationBusy}
                <p class="text-xs text-center text-sem-fg-muted">
                    {state.t("tutorial.migration_working")}
                </p>
            {/if}
        </div>
    {/if}

    {#if state.androidStorageSetup && state.androidStorageSetup.needs_setup_choice}
        <div
            class="w-full {page
                ? 'max-w-2xl p-5'
                : 'max-w-xl p-4'} mx-auto rounded-2xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/90 dark:bg-blue-950/40 text-left space-y-3"
        >
            <div class="font-semibold text-blue-950 dark:text-blue-100">
                {state.t("android_storage.setup_title")}
            </div>
            <p class="text-sm text-blue-950/90 dark:text-blue-100/90">
                {state.t("android_storage.setup_desc")}
            </p>
            {#each storageChoices as choice (choice.value)}
                <label
                    class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer {state.androidStorageSetupChoice ===
                    choice.value
                        ? 'border-blue-500 bg-white/60 dark:bg-zinc-900/60'
                        : 'border-blue-200/60 dark:border-blue-900/40'}"
                >
                    <input
                        type="radio"
                        class="mt-1"
                        name="tutorial-android-storage-mode"
                        value={choice.value}
                        checked={state.androidStorageSetupChoice === choice.value}
                        onchange={() => (state.androidStorageSetupChoice = choice.value)}
                    />
                    <span>
                        <span class="font-medium text-sem-fg block">
                            {state.t(choice.titleKey)}
                        </span>
                        <span class="text-xs text-sem-fg-muted">
                            {state.t(choice.descKey)}
                        </span>
                    </span>
                </label>
            {/each}
            <div class="flex justify-stretch sm:justify-end">
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-primary"
                    disabled={state.androidStorageBusy || !state.androidStorageSetupChoice}
                    onclick={() => void state.applyAndroidStorageSetup()}
                >
                    {state.t("android_storage.setup_continue")}
                </button>
            </div>
            {#if state.androidStorageBusy}
                <p class="text-xs text-center text-sem-fg-muted">
                    {state.t("android_storage.working")}
                </p>
            {/if}
        </div>
    {/if}

    <div class="grid grid-cols-1 md:grid-cols-2 w-full {page ? 'lg:grid-cols-3 gap-6 mt-12' : 'gap-4 mt-8'}">
        {#each featureCards as card (card.titleKey)}
            <div
                class="flex items-start {page
                    ? 'gap-6 p-6 rounded-3xl hover:shadow-2xl'
                    : 'gap-4 p-4 rounded-2xl hover:shadow-xl'} bg-sem-surface-muted text-left border border-sem-border transition-all hover:scale-[1.03] hover:z-10"
            >
                <MaterialDesignIcon iconName={card.icon} class="{page ? 'size-10' : 'size-8'} {card.color}" />
                <div>
                    <div class="font-bold text-sem-fg {page ? 'text-xl' : ''}">
                        {state.t(card.titleKey)}
                    </div>
                    <div class="text-sem-fg {page ? '' : 'text-sm'}">
                        {state.t(page ? card.descPageKey : card.descKey)}
                    </div>
                </div>
            </div>
        {/each}
    </div>

    <div class="w-full flex justify-end items-center gap-2 text-sem-fg-muted {page ? 'mt-8 px-6' : 'mt-4 px-4'}">
        <MaterialDesignIcon iconName="plus" class={page ? "size-6" : "size-4"} />
        <span class="{page ? 'text-base' : 'text-xs'} font-bold uppercase tracking-widest">
            {state.t("tutorial.more_features")}
        </span>
    </div>
</div>
