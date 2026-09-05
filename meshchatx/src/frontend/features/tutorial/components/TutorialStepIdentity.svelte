<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 2. Pick a fresh identity or restore an identity key.
     * The file picker takes key material only, never a database zip, so the
     * accept list stays broad and the hint says history is not restored.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state: tutorial }: Props = $props();

    const page = $derived(tutorial.isPage);

    let identityImportFileInput: HTMLInputElement | undefined = $state();

    const modeCards = [
        {
            mode: "new" as const,
            icon: "account-plus-outline",
            color: "text-blue-500",
            titleKey: "tutorial.identity_new",
            descKey: "tutorial.identity_new_desc",
        },
        {
            mode: "import" as const,
            icon: "file-import-outline",
            color: "text-indigo-500",
            titleKey: "tutorial.identity_import",
            descKey: "tutorial.identity_import_desc",
        },
    ];
</script>

<div class={page ? "space-y-8 py-8" : "space-y-6"} data-tutorial-step="identity">
    <div class="text-center {page ? 'space-y-3' : 'space-y-2'}">
        <h2 class="{page ? 'text-3xl font-black' : 'text-2xl font-bold'} text-sem-fg">
            {tutorial.t("tutorial.identity_title")}
        </h2>
        <p class="text-sem-fg-muted {page ? 'text-lg max-w-3xl mx-auto' : 'text-base'}">
            {tutorial.t(page ? "tutorial.identity_desc_page" : "tutorial.identity_desc")}
        </p>
    </div>

    <input
        bind:this={identityImportFileInput}
        type="file"
        accept=".bin,.key,.identity,application/octet-stream,*/*"
        class="hidden"
        onchange={(event) => tutorial.onIdentityImportFileChange(event)}
    />

    <div class="grid grid-cols-1 {page ? 'md:grid-cols-2 gap-6 max-w-5xl mx-auto' : 'gap-3'}">
        {#each modeCards as card (card.mode)}
            <button
                type="button"
                class="text-left flex items-start {page
                    ? 'gap-5 p-7 rounded-3xl'
                    : 'gap-4 p-5 rounded-2xl'} border-2 transition-all {tutorial.identityMode === card.mode
                    ? 'border-blue-500 bg-blue-500/5'
                    : 'border-sem-border hover:border-blue-400'}"
                onclick={() => tutorial.setIdentityMode(card.mode)}
            >
                <MaterialDesignIcon iconName={card.icon} class="{page ? 'size-[52px]' : 'size-[34px]'} {card.color}" />
                <div>
                    <div class="font-bold text-sem-fg {page ? 'text-xl' : ''}">
                        {tutorial.t(card.titleKey)}
                    </div>
                    <div class="text-sm text-sem-fg-muted {page ? 'mt-1' : ''}">
                        {tutorial.t(card.descKey)}
                    </div>
                </div>
            </button>
        {/each}
    </div>

    <div
        class="border border-sem-border {page
            ? 'rounded-3xl max-w-4xl mx-auto p-6 space-y-4'
            : 'rounded-2xl p-4 space-y-3'}"
    >
        <label
            for="tutorial-identity-name"
            class="block {page ? 'text-base' : 'text-sm'} font-semibold {page
                ? 'text-sem-fg'
                : 'text-sem-fg-secondary'}"
        >
            {tutorial.t("tutorial.identity_set_name")}
        </label>
        <input
            id="tutorial-identity-name"
            bind:value={tutorial.identityName}
            type="text"
            placeholder={tutorial.defaultUsername}
            class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-sem-surface text-sem-fg {page
                ? 'px-4 py-3 text-base'
                : 'px-3 py-2 text-sm'}"
        />

        {#if tutorial.identityMode === "import"}
            <div class="{page ? 'space-y-4 pt-3' : 'space-y-3 pt-2'} border-t border-sem-border">
                <p class="{page ? 'text-sm' : 'text-xs'} text-sem-fg-muted">
                    {tutorial.t("tutorial.identity_import_key_only_hint")}
                </p>
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary w-full justify-center"
                    disabled={tutorial.identityImportInProgress}
                    onclick={() => identityImportFileInput?.click()}
                >
                    {tutorial.identityImportFile
                        ? tutorial.identityImportFile.name
                        : tutorial.t("tutorial.identity_upload_file")}
                </button>
                <textarea
                    bind:value={tutorial.identityImportBase32}
                    rows={page ? 4 : 3}
                    class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-sem-surface font-mono text-sem-fg {page
                        ? 'px-4 py-3 text-sm'
                        : 'px-3 py-2 text-xs'}"
                    placeholder={tutorial.t("tutorial.identity_base32_placeholder")}
                    disabled={Boolean(tutorial.identityImportFile) || tutorial.identityImportInProgress}
                    oninput={() => tutorial.onIdentityImportBase32Input()}></textarea>
                {#if tutorial.identityImportFile && tutorial.identityImportBase32.trim()}
                    <p class="{page ? 'text-sm' : 'text-xs'} text-amber-600 dark:text-amber-400">
                        {tutorial.t("tutorial.identity_file_overrides_base32")}
                    </p>
                {/if}
            </div>
        {/if}

        {#if tutorial.identityImportError}
            <p role="alert" class="text-sm text-red-600 dark:text-red-400">
                {tutorial.identityImportError}
            </p>
        {/if}
    </div>
</div>
