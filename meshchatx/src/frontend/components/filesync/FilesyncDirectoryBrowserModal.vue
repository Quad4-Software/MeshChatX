<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="open"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        @click.self="emit('close')"
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
                    @click="emit('close')"
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
                    <div class="input-field flex-1 min-w-0 py-2! font-mono text-xs truncate" :title="current">
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
                            <MaterialDesignIcon icon-name="folder" class="w-5 h-5 shrink-0 text-sem-success" />
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
                        class="input-field flex-1 min-w-0 py-2! text-sm"
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
                    <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="emit('close')">
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

<script setup lang="ts">
import { ref, watch } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import { apiPath } from "../../js/constants";
import { useTranslateUi } from "../../js/localeLoader";

defineOptions({ name: "FilesyncDirectoryBrowserModal" });

const props = withDefaults(
    defineProps<{
        open?: boolean;
        initialPath?: string;
    }>(),
    {
        open: false,
        initialPath: "",
    }
);

const emit = defineEmits<{
    close: [];
    select: [path: string];
}>();

interface DirectoryEntry {
    name: string;
    path: string;
}

const t = useTranslateUi();

const busy = ref(false);
const root = ref("");
const current = ref("");
const parent = ref<string | null>(null);
const directories = ref<DirectoryEntry[]>([]);
const newFolderName = ref("");

let loadSeq = 0;

async function load(path?: string): Promise<boolean> {
    const requestId = (loadSeq = loadSeq + 1);
    busy.value = true;
    try {
        const url = path
            ? apiPath(`/filesync/directories?path=${encodeURIComponent(path)}`)
            : apiPath("/filesync/directories");
        const response = await window.api.get(url);
        if (requestId !== loadSeq) {
            return false;
        }
        const data = response?.data || {};
        root.value = data.root || "";
        current.value = data.current || "";
        parent.value = data.parent || null;
        directories.value = Array.isArray(data.directories) ? data.directories : [];
        return true;
    } catch (err: any) {
        if (requestId === loadSeq) {
            ToastUtils.error(err?.message || t("rns_filesync.error"));
        }
        return false;
    } finally {
        if (requestId === loadSeq) {
            busy.value = false;
        }
    }
}

async function enterDirectory(path: string) {
    await load(path);
}

async function goParent() {
    if (!parent.value) {
        return;
    }
    await load(parent.value);
}

async function createFolder() {
    const name = String(newFolderName.value || "").trim();
    if (!name) {
        return;
    }
    busy.value = true;
    try {
        const response = await window.api.post(apiPath("/filesync/directories"), {
            parent: current.value,
            name,
        });
        const created = response?.data?.path;
        newFolderName.value = "";
        ToastUtils.success(t("rns_filesync.browser_created"));
        if (created) {
            await load(created);
        } else {
            await load(current.value);
        }
    } catch (err: any) {
        ToastUtils.error(err?.message || t("rns_filesync.error"));
    } finally {
        busy.value = false;
    }
}

function confirmSelection() {
    const path = String(current.value || "").trim();
    if (!path) {
        return;
    }
    emit("select", path);
    emit("close");
}

watch(
    () => props.open,
    async (isOpen) => {
        if (!isOpen) {
            return;
        }
        newFolderName.value = "";
        const start = String(props.initialPath || "").trim();
        const loaded = await load(start || undefined);
        if (!loaded && start) {
            await load(undefined);
        }
    },
    { immediate: true }
);
</script>
