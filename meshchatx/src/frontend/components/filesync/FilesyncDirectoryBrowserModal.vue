<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="open"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        @click.self="$emit('close')"
    >
        <div
            class="flex w-full max-w-lg max-h-[min(36rem,90vh)] flex-col rounded-2xl border border-sem-border-card bg-sem-surface shadow-xl"
            role="dialog"
            :aria-label="$t('rns_filesync.browser_title')"
        >
            <div class="flex items-center justify-between gap-2 border-b border-sem-border px-5 py-4">
                <h2 class="text-lg font-semibold text-sem-fg">{{ $t("rns_filesync.browser_title") }}</h2>
                <button
                    type="button"
                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface-muted"
                    :title="$t('common.close')"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>

            <div class="px-5 pt-3 space-y-2">
                <p class="text-xs text-sem-fg-muted">{{ $t("rns_filesync.browser_hint") }}</p>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="secondary-chip px-2.5 py-1.5 text-xs shrink-0"
                        :disabled="busy || !parent"
                        :title="$t('rns_filesync.browser_up')"
                        @click="goParent"
                    >
                        <MaterialDesignIcon icon-name="arrow-up" class="w-4 h-4" />
                        {{ $t("rns_filesync.browser_up") }}
                    </button>
                    <div class="input-field flex-1 min-w-0 !py-2 font-mono text-xs truncate" :title="current">
                        {{ current || "..." }}
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar px-5 py-3">
                <div v-if="busy && directories.length === 0" class="py-8 text-center text-sm text-sem-fg-muted">
                    {{ $t("rns_filesync.browser_loading") }}
                </div>
                <div v-else-if="directories.length === 0" class="py-8 text-center text-sm text-sem-fg-muted">
                    {{ $t("rns_filesync.browser_empty") }}
                </div>
                <ul v-else class="space-y-1">
                    <li v-for="entry in directories" :key="entry.path">
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 rounded-lg border border-sem-border px-3 py-2 text-left text-sm transition-colors hover:bg-sem-surface-muted"
                            @click="enterDirectory(entry.path)"
                        >
                            <MaterialDesignIcon
                                icon-name="folder"
                                class="w-5 h-5 shrink-0 text-emerald-600 dark:text-emerald-400"
                            />
                            <span class="min-w-0 truncate">{{ entry.name }}</span>
                        </button>
                    </li>
                </ul>
            </div>

            <div class="border-t border-sem-border px-5 py-3 space-y-3">
                <div class="flex flex-col sm:flex-row gap-2">
                    <input
                        v-model="newFolderName"
                        type="text"
                        class="input-field flex-1 min-w-0 !py-2 text-sm"
                        :placeholder="$t('rns_filesync.browser_new_placeholder')"
                        :disabled="busy"
                        @keydown.enter.prevent="createFolder"
                    />
                    <button
                        type="button"
                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                        :disabled="busy || !newFolderName.trim()"
                        @click="createFolder"
                    >
                        <MaterialDesignIcon icon-name="folder-plus-outline" class="w-4 h-4" />
                        {{ $t("rns_filesync.browser_new") }}
                    </button>
                </div>
                <div class="flex justify-end gap-2">
                    <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="$emit('close')">
                        {{ $t("common.cancel") }}
                    </button>
                    <button
                        type="button"
                        class="primary-chip px-4 py-2 text-sm"
                        :disabled="busy || !current"
                        @click="confirmSelection"
                    >
                        {{ $t("rns_filesync.browser_select") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "FilesyncDirectoryBrowserModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        open: {
            type: Boolean,
            default: false,
        },
        initialPath: {
            type: String,
            default: "",
        },
    },
    emits: ["close", "select"],
    data() {
        return {
            busy: false,
            root: "",
            current: "",
            parent: null,
            directories: [],
            newFolderName: "",
        };
    },
    watch: {
        open: {
            immediate: true,
            async handler(isOpen) {
                if (!isOpen) {
                    return;
                }
                this.newFolderName = "";
                const start = String(this.initialPath || "").trim();
                const loaded = await this.load(start || undefined);
                if (!loaded && start) {
                    await this.load(undefined);
                }
            },
        },
    },
    methods: {
        async load(path) {
            this.busy = true;
            try {
                const url = path
                    ? `/api/v1/filesync/directories?path=${encodeURIComponent(path)}`
                    : "/api/v1/filesync/directories";
                const response = await window.api.get(url);
                const data = response?.data || {};
                this.root = data.root || "";
                this.current = data.current || "";
                this.parent = data.parent || null;
                this.directories = Array.isArray(data.directories) ? data.directories : [];
                return true;
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
                return false;
            } finally {
                this.busy = false;
            }
        },
        async enterDirectory(path) {
            await this.load(path);
        },
        async goParent() {
            if (!this.parent) {
                return;
            }
            await this.load(this.parent);
        },
        async createFolder() {
            const name = String(this.newFolderName || "").trim();
            if (!name) {
                return;
            }
            this.busy = true;
            try {
                const response = await window.api.post("/api/v1/filesync/directories", {
                    parent: this.current,
                    name,
                });
                const created = response?.data?.path;
                this.newFolderName = "";
                ToastUtils.success(this.$t("rns_filesync.browser_created"));
                if (created) {
                    await this.load(created);
                } else {
                    await this.load(this.current);
                }
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        confirmSelection() {
            const path = String(this.current || "").trim();
            if (!path) {
                return;
            }
            this.$emit("select", path);
            this.$emit("close");
        },
    },
};
</script>
