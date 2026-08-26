<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <p class="text-sm text-sem-fg-muted">{{ $t("rns_filesync.manager_help") }}</p>

        <div class="flex flex-wrap items-center gap-2">
            <button
                type="button"
                class="secondary-chip px-3 py-1.5 text-sm"
                :disabled="busy || currentPath === ''"
                :title="$t('rns_filesync.browser_up')"
                @click="goUp"
            >
                <MaterialDesignIcon icon-name="arrow-up" class="w-4 h-4" />
                {{ $t("rns_filesync.browser_up") }}
            </button>
            <button type="button" class="secondary-chip px-3 py-1.5 text-sm" :disabled="busy" @click="refresh">
                {{ $t("rns_filesync.refresh") }}
            </button>
            <button type="button" class="secondary-chip px-3 py-1.5 text-sm" :disabled="busy" @click="triggerUpload">
                <MaterialDesignIcon icon-name="upload" class="w-4 h-4" />
                {{ $t("rns_filesync.upload") }}
            </button>
            <button
                type="button"
                class="secondary-chip px-3 py-1.5 text-sm"
                :disabled="busy || !syncDirectory"
                @click="$emit('open-folder')"
            >
                <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                {{ $t("rns_filesync.open_folder") }}
            </button>
            <input ref="fileInput" type="file" class="hidden" @change="onUploadSelected" />
        </div>

        <div class="input-field py-2! font-mono text-xs truncate" :title="breadcrumbLabel">
            {{ breadcrumbLabel }}
        </div>

        <div class="flex flex-col sm:flex-row gap-2">
            <input
                v-model="newFolderName"
                type="text"
                class="input-field flex-1 min-w-0 text-sm"
                :placeholder="$t('rns_filesync.browser_new_placeholder')"
                :disabled="busy"
                @keydown.enter.prevent="createFolder"
            />
            <button
                type="button"
                class="secondary-chip px-3 py-2 text-sm shrink-0"
                :disabled="busy || !newFolderName.trim()"
                @click="createFolder"
            >
                <MaterialDesignIcon icon-name="folder-plus-outline" class="w-4 h-4" />
                {{ $t("rns_filesync.browser_new") }}
            </button>
        </div>

        <div v-if="busy && entries.length === 0" class="text-sm text-sem-fg-muted">
            {{ $t("rns_filesync.manager_loading") }}
        </div>
        <div v-else-if="entries.length === 0" class="text-sm text-sem-fg-muted">
            {{ $t("rns_filesync.manager_empty") }}
        </div>
        <ul v-else class="space-y-2">
            <li
                v-for="entry in entries"
                :key="entry.path"
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
            >
                <button
                    v-if="entry.type === 'dir'"
                    type="button"
                    class="min-w-0 flex items-center gap-2 text-left text-sm text-sem-fg hover:text-emerald-600 dark:hover:text-emerald-400"
                    @click="enterDir(entry.path)"
                >
                    <MaterialDesignIcon
                        icon-name="folder"
                        class="w-5 h-5 shrink-0 text-emerald-600 dark:text-emerald-400"
                    />
                    <span class="break-all">{{ entry.name }}</span>
                </button>
                <div v-else class="min-w-0 flex items-center gap-2 text-sm text-sem-fg">
                    <MaterialDesignIcon icon-name="file-outline" class="w-5 h-5 shrink-0 text-sem-fg-muted" />
                    <div class="min-w-0">
                        <div class="break-all">{{ entry.name }}</div>
                        <div class="text-xs text-sem-fg-muted mt-0.5">
                            {{ formatFileSize(entry.size) }}
                        </div>
                    </div>
                </div>
                <div class="flex flex-wrap gap-2 shrink-0">
                    <button
                        v-if="entry.type === 'file'"
                        type="button"
                        class="secondary-chip px-3 py-1.5 text-sm"
                        :disabled="busy"
                        @click="downloadEntry(entry)"
                    >
                        {{ $t("rns_filesync.download_local") }}
                    </button>
                    <button
                        type="button"
                        class="secondary-chip px-3 py-1.5 text-sm text-red-600 dark:text-red-300"
                        :disabled="busy"
                        @click="deleteEntry(entry)"
                    >
                        {{ $t("rns_filesync.delete") }}
                    </button>
                </div>
            </li>
        </ul>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DownloadUtils from "../../js/DownloadUtils";
import DialogUtils from "../../js/DialogUtils";
import Utils from "../../js/Utils";

export default {
    name: "FilesyncFileManager",
    components: {
        MaterialDesignIcon,
    },
    props: {
        syncDirectory: {
            type: String,
            default: "",
        },
    },
    emits: ["open-folder"],
    data() {
        return {
            busy: false,
            currentPath: "",
            parentPath: null,
            entries: [],
            newFolderName: "",
        };
    },
    computed: {
        breadcrumbLabel() {
            if (!this.currentPath) {
                return this.$t("rns_filesync.manager_root");
            }
            return this.currentPath;
        },
    },
    watch: {
        syncDirectory() {
            this.currentPath = "";
            this.refresh();
        },
    },
    mounted() {
        this.refresh();
    },
    methods: {
        formatFileSize(bytes) {
            return Utils.formatBytes(bytes || 0);
        },
        joinPath(base, name) {
            const left = String(base || "").replace(/\/+$/, "");
            const right = String(name || "").replace(/^\/+/, "");
            if (!left) {
                return right;
            }
            if (!right) {
                return left;
            }
            return `${left}/${right}`;
        },
        async refresh() {
            this.busy = true;
            try {
                const params = {};
                if (this.currentPath) {
                    params.path = this.currentPath;
                }
                const response = await window.api.get("/api/v1/filesync/tree", { params });
                const data = response?.data || {};
                this.entries = Array.isArray(data.entries) ? data.entries : [];
                this.currentPath = data.current != null ? String(data.current) : "";
                this.parentPath = data.parent === undefined ? null : data.parent;
            } catch (err) {
                this.entries = [];
                ToastUtils.error(err?.response?.data?.message || err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        enterDir(path) {
            this.currentPath = String(path || "");
            this.refresh();
        },
        goUp() {
            if (this.parentPath === null || this.parentPath === undefined) {
                return;
            }
            this.currentPath = this.parentPath === "" ? "" : String(this.parentPath);
            this.refresh();
        },
        triggerUpload() {
            this.$refs.fileInput?.click();
        },
        async onUploadSelected(event) {
            const file = event?.target?.files?.[0];
            if (!file) {
                return;
            }
            this.busy = true;
            try {
                const formData = new FormData();
                formData.append("file", file);
                if (this.currentPath) {
                    formData.append("path", this.currentPath);
                }
                await window.api.post("/api/v1/filesync/upload", formData);
                ToastUtils.success(this.$t("rns_filesync.upload_done"));
                await this.refresh();
            } catch (err) {
                ToastUtils.error(err?.response?.data?.message || err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
                if (event?.target) {
                    event.target.value = "";
                }
            }
        },
        async createFolder() {
            const name = String(this.newFolderName || "").trim();
            if (!name) {
                return;
            }
            this.busy = true;
            try {
                const path = this.joinPath(this.currentPath, name);
                await window.api.post("/api/v1/filesync/mkdir", { path });
                ToastUtils.success(this.$t("rns_filesync.browser_created"));
                this.newFolderName = "";
                await this.refresh();
            } catch (err) {
                ToastUtils.error(err?.response?.data?.message || err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async downloadEntry(entry) {
            const path = entry?.path;
            if (!path) {
                return;
            }
            this.busy = true;
            try {
                const response = await window.api.get("/api/v1/filesync/content", {
                    params: { path },
                    responseType: "blob",
                });
                await DownloadUtils.downloadFromApiResponse(response, entry.name || "download");
                ToastUtils.success(this.$t("rns_filesync.download_local_done"));
            } catch (err) {
                ToastUtils.error(err?.response?.data?.message || err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async deleteEntry(entry) {
            const path = entry?.path;
            if (!path) {
                return;
            }
            const label = entry.name || path;
            if (!(await DialogUtils.confirm(this.$t("rns_filesync.delete_confirm", { name: label })))) {
                return;
            }
            this.busy = true;
            try {
                await window.api.delete("/api/v1/filesync/entry", { data: { path } });
                ToastUtils.success(this.$t("rns_filesync.delete_done"));
                await this.refresh();
            } catch (err) {
                ToastUtils.error(err?.response?.data?.message || err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
    },
};
</script>
