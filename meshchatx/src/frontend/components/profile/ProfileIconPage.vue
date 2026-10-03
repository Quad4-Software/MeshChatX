<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 dark:bg-sem-surface">
        <div class="overflow-y-auto">
            <div class="max-w-4xl mx-auto p-4 space-y-6">
                <!-- Header with Preview -->
                <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border">
                    <div class="p-6 border-b border-sem-border">
                        <div class="flex items-center justify-between">
                            <div>
                                <h2 class="text-xl font-bold text-sem-fg">Profile Icon Customizer</h2>
                                <p class="text-sm text-sem-fg-muted mt-1">
                                    Customize your profile icon that appears in all your messages
                                </p>
                            </div>
                            <div class="flex items-center gap-3">
                                <button
                                    type="button"
                                    :disabled="!hasChanges || isSaving"
                                    class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    :class="
                                        hasChanges && !isSaving
                                            ? 'bg-sem-action-primary text-sem-action-primary-text border-sem-info hover:bg-sem-info dark:bg-sem-info dark:border-sem-accent dark:hover:bg-sem-info'
                                            : 'bg-sem-surface-muted text-sem-fg border-sem-border dark:bg-sem-surface text-sem-fg-muted dark:border-sem-border'
                                    "
                                    @click="saveChanges"
                                >
                                    <MaterialDesignIcon
                                        v-if="isSaving"
                                        icon-name="refresh"
                                        class="size-4 animate-spin"
                                    />
                                    <MaterialDesignIcon v-else icon-name="content-save" class="size-4" />
                                    {{ isSaving ? "Saving..." : "Save" }}
                                </button>
                                <button
                                    type="button"
                                    :disabled="!hasChanges || isSaving"
                                    class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-sem-border bg-sem-surface text-sem-fg-muted hover:bg-sem-surface-muted hover:bg-sem-surface-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    @click="resetChanges"
                                >
                                    <MaterialDesignIcon icon-name="refresh" class="size-4" />
                                    Reset
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="p-6">
                        <div class="flex flex-col items-center justify-center space-y-4">
                            <div class="text-sm font-medium text-sem-fg-muted">Preview</div>
                            <div class="p-8 bg-sem-surface-muted rounded-2xl">
                                <LxmfUserIcon
                                    :key="iconName + iconForegroundColour + iconBackgroundColour"
                                    :icon-name="iconName"
                                    :icon-foreground-colour="iconForegroundColour"
                                    :icon-background-colour="iconBackgroundColour"
                                    icon-class="size-24"
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
                                <label class="block text-sm font-medium text-sem-fg-muted mb-2">
                                    Background Color
                                </label>
                                <div class="flex items-center gap-3">
                                    <ColourPickerDropdown v-model:colour="iconBackgroundColour" />
                                    <div class="flex-1">
                                        <input
                                            v-model="iconBackgroundColour"
                                            type="text"
                                            class="w-full px-3 py-2 text-sm border border-sem-border rounded-lg bg-sem-surface text-sem-fg focus:ring-2 focus:ring-sem-accent focus:border-sem-accent"
                                            placeholder="#e5e7eb"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                            <div class="flex-1">
                                <label class="block text-sm font-medium text-sem-fg-muted mb-2"> Icon Color </label>
                                <div class="flex items-center gap-3">
                                    <ColourPickerDropdown v-model:colour="iconForegroundColour" />
                                    <div class="flex-1">
                                        <input
                                            v-model="iconForegroundColour"
                                            type="text"
                                            class="w-full px-3 py-2 text-sm border border-sem-border rounded-lg bg-sem-surface text-sem-fg focus:ring-2 focus:ring-sem-accent focus:border-sem-accent"
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
                        <SearchInput v-model="search" :placeholder="`Search ${iconNames.length} icons...`" />
                        <div
                            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 max-h-[500px] overflow-y-auto p-1"
                        >
                            <div
                                v-for="mdiIconName of searchedIconNames"
                                :key="mdiIconName"
                                class="flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-sem-surface-muted hover:border-sem-accent dark:hover:border-sem-accent"
                                :class="
                                    iconName === mdiIconName
                                        ? 'border-sem-accent bg-sem-surface-muted'
                                        : 'border-sem-border'
                                "
                                @click="onIconClick(mdiIconName)"
                            >
                                <LxmfUserIcon
                                    :key="
                                        mdiIconName +
                                        (iconName === mdiIconName ? iconForegroundColour + iconBackgroundColour : '')
                                    "
                                    :icon-name="mdiIconName"
                                    :icon-foreground-colour="
                                        iconName === mdiIconName ? iconForegroundColour : '#6b7280'
                                    "
                                    :icon-background-colour="
                                        iconName === mdiIconName ? iconBackgroundColour : '#e5e7eb'
                                    "
                                    icon-class="size-12"
                                />
                                <div
                                    class="mt-2 text-xs text-center text-sem-fg-muted truncate w-full"
                                    :title="mdiIconName"
                                >
                                    {{ mdiIconName }}
                                </div>
                            </div>
                        </div>
                        <div v-if="searchedIconNames.length === 0" class="text-center py-8 text-sm text-sem-fg-muted">
                            No icons match your search.
                        </div>
                        <div
                            v-if="searchedIconNames.length === maxSearchResults"
                            class="text-center py-2 text-xs text-sem-fg-muted"
                        >
                            Showing first {{ maxSearchResults }} results. Refine your search to see more.
                        </div>
                    </div>
                </div>

                <!-- Remove Icon Section -->
                <div class="bg-sem-surface rounded-xl shadow-xs border border-sem-border overflow-hidden">
                    <div class="p-4 border-b border-sem-border">
                        <h3 class="text-lg font-semibold text-sem-fg">Remove Icon</h3>
                    </div>
                    <div class="p-4">
                        <p class="text-sm text-sem-fg-muted mb-4">
                            Remove your profile icon. Anyone who has already received it will continue to see it until
                            you send them a new icon.
                        </p>
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-sem-danger dark:border-sem-danger bg-sem-surface text-sem-danger hover:bg-sem-danger/15 dark:hover:bg-sem-danger/15 transition-colors"
                            @click="removeProfileIcon"
                        >
                            <MaterialDesignIcon icon-name="delete-outline" class="size-4" />
                            Remove Icon
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { useConfigStore } from "../../js/stores/configStore";

import * as mdi from "@mdi/js";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import ColourPickerDropdown from "../ColourPickerDropdown.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SearchInput from "../SearchInput.vue";
import GlobalEmitter from "../../js/GlobalEmitter";
import { apiPath, EMITTER_EVENTS } from "../../js/constants";

export default {
    name: "ProfileIconPage",
    components: {
        ColourPickerDropdown,
        LxmfUserIcon,
        MaterialDesignIcon,
        SearchInput,
    },
    data() {
        return {
            config: null,
            iconName: null,
            iconForegroundColour: null,
            iconBackgroundColour: null,

            originalIconName: null,
            originalIconForegroundColour: null,
            originalIconBackgroundColour: null,

            search: "",
            maxSearchResults: 200,
            iconNames: [],

            isSaving: false,
            autoSaveTimeout: null,
        };
    },
    computed: {
        searchedIconNames() {
            const searchLower = this.search.toLowerCase();
            return this.iconNames
                .filter((iconName) => {
                    return iconName.toLowerCase().includes(searchLower);
                })
                .slice(0, this.maxSearchResults);
        },
        hasChanges() {
            return (
                this.iconName !== this.originalIconName ||
                this.iconForegroundColour !== this.originalIconForegroundColour ||
                this.iconBackgroundColour !== this.originalIconBackgroundColour
            );
        },
    },
    watch: {
        config: {
            handler() {
                if (this.config) {
                    this.iconName = this.config.lxmf_user_icon_name || null;
                    this.iconForegroundColour = this.config.lxmf_user_icon_foreground_colour || "#6b7280";
                    this.iconBackgroundColour = this.config.lxmf_user_icon_background_colour || "#e5e7eb";

                    this.saveOriginalValues();
                }
            },
            immediate: true,
        },
        iconForegroundColour() {
            this.debouncedAutoSave();
        },
        iconBackgroundColour() {
            this.debouncedAutoSave();
        },
        iconName() {
            this.debouncedAutoSave();
        },
    },
    mounted() {
        this.getConfig();

        this.iconNames = Object.keys(mdi).map((mdiIcon) => {
            return mdiIcon
                .replace(/^mdi/, "")
                .replace(/([a-z])([A-Z])/g, "$1-$2")
                .toLowerCase();
        });
    },
    beforeUnmount() {
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }
    },
    methods: {
        saveOriginalValues() {
            this.originalIconName = this.iconName;
            this.originalIconForegroundColour = this.iconForegroundColour;
            this.originalIconBackgroundColour = this.iconBackgroundColour;
        },
        debouncedAutoSave() {
            if (this.autoSaveTimeout) {
                clearTimeout(this.autoSaveTimeout);
            }

            this.autoSaveTimeout = setTimeout(() => {
                if (this.hasChanges && this.iconName && this.iconForegroundColour && this.iconBackgroundColour) {
                    this.saveChanges(true);
                }
            }, 1000);
        },
        async getConfig() {
            try {
                const response = await window.api.get(apiPath("/config"));
                const next = response.data?.config;
                if (next && typeof next === "object") {
                    this.config = next;
                    useConfigStore().mergeConfig(next);
                }
            } catch (e) {
                ToastUtils.error(this.$t("messages.failed_load_config"));
                console.error(e);
            }
        },
        async updateConfig(config, silent = false) {
            try {
                const response = await window.api.patch(apiPath("/config"), config);
                const next = response.data?.config;
                if (!next || typeof next !== "object") {
                    return false;
                }
                useConfigStore().mergeConfig(next);
                this.config = next;
                GlobalEmitter.emit(EMITTER_EVENTS.CONFIG_UPDATED, next);
                this.saveOriginalValues();

                if (!silent) {
                    ToastUtils.success(this.$t("messages.profile_icon_saved"));
                }
                return true;
            } catch (e) {
                if (!silent) {
                    ToastUtils.error(this.$t("messages.failed_save_profile_icon"));
                }
                console.error(e);
                return false;
            }
        },
        async saveChanges(silent = false) {
            if (!this.hasChanges) {
                return;
            }

            if (!this.iconForegroundColour || !this.iconBackgroundColour) {
                ToastUtils.warning(this.$t("messages.select_colors_warning"));
                return;
            }

            if (!this.iconName) {
                ToastUtils.warning(this.$t("messages.select_icon_warning"));
                return;
            }

            this.isSaving = true;

            try {
                const success = await this.updateConfig(
                    {
                        lxmf_user_icon_name: this.iconName,
                        lxmf_user_icon_foreground_colour: this.iconForegroundColour,
                        lxmf_user_icon_background_colour: this.iconBackgroundColour,
                    },
                    silent
                );

                if (success && !silent) {
                    ToastUtils.success(this.$t("messages.profile_icon_saved"));
                }
            } finally {
                this.isSaving = false;
            }
        },
        resetChanges() {
            if (!this.hasChanges) {
                return;
            }

            this.iconName = this.originalIconName;
            this.iconForegroundColour = this.originalIconForegroundColour;
            this.iconBackgroundColour = this.originalIconBackgroundColour;

            ToastUtils.info(this.$t("messages.changes_reset"));
        },
        onIconClick(iconName) {
            this.iconName = iconName;
        },
        async removeProfileIcon() {
            this.isSaving = true;

            try {
                const success = await this.updateConfig({
                    lxmf_user_icon_name: null,
                    lxmf_user_icon_foreground_colour: null,
                    lxmf_user_icon_background_colour: null,
                });

                if (success) {
                    ToastUtils.success(this.$t("messages.profile_icon_removed"));
                }
            } finally {
                this.isSaving = false;
            }
        },
    },
};
</script>
