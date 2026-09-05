<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import { buildMdiIconNames } from "../../js/mdiIconNames.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { mergeGlobalConfig } from "../../js/GlobalState.js";
    import { t } from "../../js/i18n.js";
    import LxmfUserIcon from "../../ui/svelte/LxmfUserIcon.svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ColourPickerDropdown from "./components/ColourPickerDropdown.svelte";
    import {
        DEFAULT_BACKGROUND_COLOUR,
        DEFAULT_FOREGROUND_COLOUR,
        DEFAULT_MAX_SEARCH_RESULTS,
        filterIconNames,
    } from "./lib/profileIcon.js";

    let iconName = $state<string | null>(null);
    let iconForegroundColour = $state<string | null>(null);
    let iconBackgroundColour = $state<string | null>(null);

    let originalIconName = $state<string | null>(null);
    let originalIconForegroundColour = $state<string | null>(null);
    let originalIconBackgroundColour = $state<string | null>(null);

    let search = $state("");
    let iconNames = $state<string[]>([]);
    let isSaving = $state(false);
    let autoSaveTimeout: ReturnType<typeof setTimeout> | null = null;
    let initialConfigLoaded = $state(false);

    const searchedIconNames = $derived(filterIconNames(iconNames, search, DEFAULT_MAX_SEARCH_RESULTS));

    const hasChanges = $derived(
        iconName !== originalIconName ||
            iconForegroundColour !== originalIconForegroundColour ||
            iconBackgroundColour !== originalIconBackgroundColour
    );

    function saveOriginalValues(): void {
        originalIconName = iconName;
        originalIconForegroundColour = iconForegroundColour;
        originalIconBackgroundColour = iconBackgroundColour;
    }

    function debouncedAutoSave(): void {
        if (!initialConfigLoaded) return;
        if (autoSaveTimeout) {
            clearTimeout(autoSaveTimeout);
        }
        autoSaveTimeout = setTimeout(() => {
            if (hasChanges && iconName && iconForegroundColour && iconBackgroundColour) {
                void saveChanges(true);
            }
        }, 1000);
    }

    async function getConfig(): Promise<void> {
        try {
            const response = await window.api.get("/api/v1/config");
            const next = response.data?.config as Record<string, unknown> | undefined;
            if (next && typeof next === "object") {
                mergeGlobalConfig(next);
                iconName = (next.lxmf_user_icon_name as string) || null;
                iconForegroundColour = (next.lxmf_user_icon_foreground_colour as string) || DEFAULT_FOREGROUND_COLOUR;
                iconBackgroundColour = (next.lxmf_user_icon_background_colour as string) || DEFAULT_BACKGROUND_COLOUR;
                saveOriginalValues();
                initialConfigLoaded = true;
            }
        } catch (e) {
            ToastUtils.error(t("messages.failed_load_config"));
            console.error(e);
        }
    }

    async function updateConfig(configPatch: Record<string, string | null>, silent: boolean = false): Promise<boolean> {
        try {
            const response = await window.api.patch("/api/v1/config", configPatch);
            const next = response.data?.config as Record<string, unknown> | undefined;
            if (!next || typeof next !== "object") {
                return false;
            }
            mergeGlobalConfig(next);
            iconName = (next.lxmf_user_icon_name as string) || null;
            iconForegroundColour = (next.lxmf_user_icon_foreground_colour as string) || DEFAULT_FOREGROUND_COLOUR;
            iconBackgroundColour = (next.lxmf_user_icon_background_colour as string) || DEFAULT_BACKGROUND_COLOUR;
            GlobalEmitter.emit("config-updated", next);
            saveOriginalValues();

            if (!silent) {
                ToastUtils.success(t("messages.profile_icon_saved"));
            }
            return true;
        } catch (e) {
            if (!silent) {
                ToastUtils.error(t("messages.failed_save_profile_icon"));
            }
            console.error(e);
            return false;
        }
    }

    async function saveChanges(silent: boolean = false): Promise<void> {
        if (!hasChanges) {
            return;
        }

        if (!iconForegroundColour || !iconBackgroundColour) {
            ToastUtils.warning(t("messages.select_colors_warning"));
            return;
        }

        if (!iconName) {
            ToastUtils.warning(t("messages.select_icon_warning"));
            return;
        }

        isSaving = true;
        try {
            await updateConfig(
                {
                    lxmf_user_icon_name: iconName,
                    lxmf_user_icon_foreground_colour: iconForegroundColour,
                    lxmf_user_icon_background_colour: iconBackgroundColour,
                },
                silent
            );
        } finally {
            isSaving = false;
        }
    }

    function resetChanges(): void {
        if (!hasChanges) {
            return;
        }
        iconName = originalIconName;
        iconForegroundColour = originalIconForegroundColour;
        iconBackgroundColour = originalIconBackgroundColour;
        ToastUtils.info(t("messages.changes_reset"));
    }

    function onIconClick(name: string): void {
        iconName = name;
        debouncedAutoSave();
    }

    function onBackgroundColourChange(val: string): void {
        iconBackgroundColour = val;
        debouncedAutoSave();
    }

    function onForegroundColourChange(val: string): void {
        iconForegroundColour = val;
        debouncedAutoSave();
    }

    async function removeProfileIcon(): Promise<void> {
        isSaving = true;
        try {
            const success = await updateConfig({
                lxmf_user_icon_name: null,
                lxmf_user_icon_foreground_colour: null,
                lxmf_user_icon_background_colour: null,
            });
            if (success) {
                ToastUtils.success(t("messages.profile_icon_removed"));
            }
        } finally {
            isSaving = false;
        }
    }

    onMount(() => {
        void getConfig();
        iconNames = buildMdiIconNames();
    });

    onDestroy(() => {
        if (autoSaveTimeout) {
            clearTimeout(autoSaveTimeout);
        }
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas dark:bg-zinc-950">
    <div class="overflow-y-auto">
        <div class="max-w-4xl mx-auto p-4 space-y-6">
            <!-- Header with Preview -->
            <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border">
                <div class="p-6 border-b border-sem-border">
                    <div class="flex items-center justify-between flex-wrap gap-4">
                        <div>
                            <h2 class="text-xl font-bold text-sem-fg">Profile Icon Customizer</h2>
                            <p class="text-sm text-sem-fg-muted mt-1">
                                Customize your profile icon that appears in all your messages
                            </p>
                        </div>
                        <div class="flex items-center gap-3">
                            <button
                                type="button"
                                disabled={!hasChanges || isSaving}
                                class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed {hasChanges &&
                                !isSaving
                                    ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:border-blue-500 dark:hover:bg-blue-600'
                                    : 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-zinc-800 text-sem-fg-muted dark:border-zinc-700'}"
                                onclick={() => saveChanges(false)}
                            >
                                {#if isSaving}
                                    <MaterialDesignIcon iconName="refresh" class="size-4 animate-spin" />
                                {:else}
                                    <MaterialDesignIcon iconName="content-save" class="size-4" />
                                {/if}
                                {isSaving ? "Saving..." : "Save"}
                            </button>
                            <button
                                type="button"
                                disabled={!hasChanges || isSaving}
                                class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-sem-fg-muted hover:bg-gray-50 hover:bg-sem-surface-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                onclick={resetChanges}
                            >
                                <MaterialDesignIcon iconName="refresh" class="size-4" />
                                Reset
                            </button>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="flex flex-col items-center justify-center space-y-4">
                        <div class="text-sm font-medium text-sem-fg-muted">Preview</div>
                        <div class="p-8 bg-gray-50 dark:bg-zinc-800 rounded-2xl">
                            <LxmfUserIcon
                                iconName={iconName || ""}
                                iconForegroundColour={iconForegroundColour || ""}
                                iconBackgroundColour={iconBackgroundColour || ""}
                                iconClass="size-24"
                            />
                        </div>
                        <div class="text-xs text-sem-fg-muted text-center max-w-md">
                            This is how your icon will appear to others when you send messages
                        </div>
                    </div>
                </div>
            </div>

            <!-- Color Selection -->
            <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border">
                <div class="p-4 border-b border-sem-border">
                    <h3 class="text-lg font-semibold text-sem-fg">Colors</h3>
                </div>
                <div class="p-4 space-y-4">
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex-1">
                            <label for="profile-bg-color" class="block text-sm font-medium text-sem-fg-muted mb-2">
                                Background Color
                            </label>
                            <div class="flex items-center gap-3">
                                <ColourPickerDropdown
                                    colour={iconBackgroundColour || ""}
                                    onchange={onBackgroundColourChange}
                                />
                                <div class="flex-1">
                                    <input
                                        id="profile-bg-color"
                                        bind:value={iconBackgroundColour}
                                        oninput={() => debouncedAutoSave()}
                                        type="text"
                                        class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="#e5e7eb"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex-1">
                            <label for="profile-fg-color" class="block text-sm font-medium text-sem-fg-muted mb-2">
                                Icon Color
                            </label>
                            <div class="flex items-center gap-3">
                                <ColourPickerDropdown
                                    colour={iconForegroundColour || ""}
                                    onchange={onForegroundColourChange}
                                />
                                <div class="flex-1">
                                    <input
                                        id="profile-fg-color"
                                        bind:value={iconForegroundColour}
                                        oninput={() => debouncedAutoSave()}
                                        type="text"
                                        class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="#6b7280"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Icon Selection -->
            <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border overflow-hidden">
                <div class="p-4 border-b border-sem-border">
                    <h3 class="text-lg font-semibold text-sem-fg">Icon</h3>
                </div>
                <div class="p-4 space-y-4">
                    <div class="relative">
                        <input
                            bind:value={search}
                            type="text"
                            placeholder="Search {iconNames.length} icons..."
                            class="w-full px-4 py-3 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-sem-fg placeholder-gray-400 dark:placeholder-zinc-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <MaterialDesignIcon
                            iconName="magnify"
                            class="absolute right-3 top-1/2 -translate-y-1/2 size-5 text-sem-fg-muted pointer-events-none"
                        />
                    </div>
                    <div
                        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 max-h-[500px] overflow-y-auto p-1"
                    >
                        {#each searchedIconNames as mdiIconName (mdiIconName)}
                            <button
                                type="button"
                                class="flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-sem-surface-muted hover:border-blue-500 dark:hover:border-blue-500 {iconName ===
                                mdiIconName
                                    ? 'border-blue-500 bg-sem-surface-muted'
                                    : 'border-sem-border'}"
                                onclick={() => onIconClick(mdiIconName)}
                            >
                                <LxmfUserIcon
                                    iconName={mdiIconName}
                                    iconForegroundColour={iconName === mdiIconName
                                        ? iconForegroundColour || DEFAULT_FOREGROUND_COLOUR
                                        : "#6b7280"}
                                    iconBackgroundColour={iconName === mdiIconName
                                        ? iconBackgroundColour || DEFAULT_BACKGROUND_COLOUR
                                        : "#e5e7eb"}
                                    iconClass="size-12"
                                />
                                <div
                                    class="mt-2 text-xs text-center text-sem-fg-muted truncate w-full"
                                    title={mdiIconName}
                                >
                                    {mdiIconName}
                                </div>
                            </button>
                        {/each}
                    </div>
                    {#if searchedIconNames.length === 0}
                        <div class="text-center py-8 text-sm text-sem-fg-muted">No icons match your search.</div>
                    {/if}
                    {#if searchedIconNames.length === DEFAULT_MAX_SEARCH_RESULTS}
                        <div class="text-center py-2 text-xs text-sem-fg-muted">
                            Showing first {DEFAULT_MAX_SEARCH_RESULTS} results. Refine your search to see more.
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Remove Icon Section -->
            <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border overflow-hidden">
                <div class="p-4 border-b border-sem-border">
                    <h3 class="text-lg font-semibold text-sem-fg">Remove Icon</h3>
                </div>
                <div class="p-4">
                    <p class="text-sm text-sem-fg-muted mb-4">
                        Remove your profile icon. Anyone who has already received it will continue to see it until you
                        send them a new icon.
                    </p>
                    <button
                        type="button"
                        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-red-300 dark:border-red-800 bg-white dark:bg-zinc-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        onclick={removeProfileIcon}
                    >
                        <MaterialDesignIcon iconName="delete-outline" class="size-4" />
                        Remove Icon
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
