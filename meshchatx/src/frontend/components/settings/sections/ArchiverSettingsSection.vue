<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Browsing</div>
                <h2>Page Archiver</h2>
                <p>Automatically save copies of visited NomadNetwork pages.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="page-archiver-enabled"
                    :model-value="config.page_archiver_enabled"
                    @update:model-value="$emit('enabled-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Enable Archiver</span>
                    <span class="setting-toggle__description"
                        >Automatically archive pages for offline viewing and fallback.</span
                    >
                </span>
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Max Versions per Page</div>
                    <input
                        :value="config.page_archiver_max_versions"
                        type="number"
                        min="1"
                        max="50"
                        class="input-field"
                        @input="
                            $emit('config-change', {
                                page_archiver_max_versions: Number($event.target.value),
                            })
                        "
                    />
                    <div class="text-xs text-gray-600 dark:text-gray-400">How many versions of each page to keep.</div>
                </div>
                <div class="space-y-2">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Max Total Storage (GB)</div>
                    <input
                        :value="config.archives_max_storage_gb"
                        type="number"
                        min="1"
                        class="input-field"
                        @input="
                            $emit('config-change', {
                                archives_max_storage_gb: Number($event.target.value),
                            })
                        "
                    />
                    <div class="text-xs text-gray-600 dark:text-gray-400">Total storage for all archived pages.</div>
                </div>
            </div>
            <button
                type="button"
                class="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-semibold text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/40 transition"
                @click="$emit('flush')"
            >
                <MaterialDesignIcon icon-name="delete-sweep" class="w-4 h-4" />
                Flush All Archived Pages
            </button>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "ArchiverSettingsSection",
    components: {
        Toggle,
        MaterialDesignIcon,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        config: {
            type: Object,
            required: true,
        },
    },
    emits: ["enabled-change", "config-change", "flush"],
};
</script>
