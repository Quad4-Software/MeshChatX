<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 dark:bg-zinc-950">
        <div class="overflow-y-auto">
            <div class="max-w-4xl mx-auto p-4 space-y-6">
                <!-- Header with Preview -->
                <div class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800">
                    <div class="p-6 border-b border-gray-200 dark:border-zinc-800">
                        <div class="flex items-center justify-between">
                            <div>
                                <h2 class="text-xl font-bold text-gray-900 dark:text-white">Profile Icon Customizer</h2>
                                <p class="text-sm text-gray-500 dark:text-zinc-400 mt-1">
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
                                            ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:border-blue-500 dark:hover:bg-blue-600'
                                            : 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700'
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
                                    class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                            <div class="text-sm font-medium text-gray-700 dark:text-zinc-300">Preview</div>
                            <div class="p-8 bg-gray-50 dark:bg-zinc-800 rounded-2xl">
                                <LxmfUserIcon
                                    :key="iconName + iconForegroundColour + iconBackgroundColour"
                                    :icon-name="iconName"
                                    :icon-foreground-colour="iconForegroundColour"
                                    :icon-background-colour="iconBackgroundColour"
                                    icon-class="size-24"
                                />
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-400 text-center max-w-md">
                                This is how your icon will appear to others when you send messages
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Color Selection -->
                <div class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800">
                    <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Colors</h3>
                    </div>
                    <div class="p-4 space-y-4">
                        <div class="flex items-center justify-between gap-4">
                            <div class="flex-1">
                                <label class="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2">
                                    Background Color
                                </label>
                                <div class="flex items-center gap-3">
                                    <ColourPickerDropdown v-model:colour="iconBackgroundColour" />
                                    <div class="flex-1">
                                        <input
                                            v-model="iconBackgroundColour"
                                            type="text"
                                            class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            placeholder="#e5e7eb"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                            <div class="flex-1">
                                <label class="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2">
                                    Icon Color
                                </label>
                                <div class="flex items-center gap-3">
                                    <ColourPickerDropdown v-model:colour="iconForegroundColour" />
                                    <div class="flex-1">
                                        <input
                                            v-model="iconForegroundColour"
                                            type="text"
                                            class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            placeholder="#6b7280"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Icon Selection -->
                <div
                    class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                >
                    <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Icon</h3>
                    </div>
                    <div class="p-4 space-y-4">
                        <div class="relative">
                            <input
                                v-model="search"
                                type="text"
                                :placeholder="`Search ${iconNames.length} icons...`"
                                class="w-full px-4 py-3 text-sm border border-gray-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <MaterialDesignIcon
                                icon-name="magnify"
                                class="absolute right-3 top-1/2 -translate-y-1/2 size-5 text-gray-400 dark:text-zinc-500 pointer-events-none"
                            />
                        </div>
                        <div
                            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 max-h-[500px] overflow-y-auto p-1"
                        >
                            <div
                                v-for="mdiIconName of searchedIconNames"
                                :key="mdiIconName"
                                class="flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-gray-50 dark:hover:bg-zinc-800 hover:border-blue-500 dark:hover:border-blue-500"
                                :class="
                                    iconName === mdiIconName
                                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                        : 'border-gray-200 dark:border-zinc-700'
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
                                    class="mt-2 text-xs text-center text-gray-600 dark:text-zinc-400 truncate w-full"
                                    :title="mdiIconName"
                                >
                                    {{ mdiIconName }}
                                </div>
                            </div>
                        </div>
                        <div
                            v-if="searchedIconNames.length === 0"
                            class="text-center py-8 text-sm text-gray-500 dark:text-zinc-400"
                        >
                            No icons match your search.
                        </div>
                        <div
                            v-if="searchedIconNames.length === maxSearchResults"
                            class="text-center py-2 text-xs text-gray-500 dark:text-zinc-400"
                        >
                            Showing first {{ maxSearchResults }} results. Refine your search to see more.
                        </div>
                    </div>
                </div>

                <!-- Remove Icon Section -->
                <div
                    class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                >
                    <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Remove Icon</h3>
                    </div>
                    <div class="p-4">
                        <p class="text-sm text-gray-600 dark:text-zinc-400 mb-4">
                            Remove your profile icon. Anyone who has already received it will continue to see it until
                            you send them a new icon.
                        </p>
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-red-300 dark:border-red-800 bg-white dark:bg-zinc-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
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
import * as mdi from "@mdi/js";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import ColourPickerDropdown from "../ColourPickerDropdown.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";

export default {
    name: "ProfileIconPage",
    components: {
        ColourPickerDropdown,
        LxmfUserIcon,
        MaterialDesignIcon,
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
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                ToastUtils.error(this.$t("messages.failed_load_config"));
                console.error(e);
            }
        },
        async updateConfig(config, silent = false) {
            try {
                const response = await window.axios.patch("/api/v1/config", config);
                this.config = response.data.config;
                GlobalState.config = response.data.config;
                GlobalEmitter.emit("config-updated", response.data.config);
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
