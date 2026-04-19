<template>
    <div class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center gap-2">
            <button
                type="button"
                class="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm font-medium flex items-center gap-1"
                @click="openCreatePack"
            >
                <MaterialDesignIcon icon-name="folder-plus-outline" class="size-4" />
                {{ $t("sticker_packs.create") }}
            </button>
            <button
                type="button"
                class="rounded-xl border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm hover:border-teal-500 flex items-center gap-1"
                @click="triggerInstallInput"
            >
                <MaterialDesignIcon icon-name="package-down" class="size-4" />
                {{ $t("sticker_packs.install_from_file") }}
            </button>
            <input
                ref="installFileInput"
                type="file"
                accept=".json,application/json"
                class="hidden"
                @change="onInstallFile"
            />
        </div>

        <div v-if="packs.length === 0" class="text-sm text-gray-500 dark:text-zinc-400">
            {{ $t("sticker_packs.empty") }}
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
                v-for="pack in packs"
                :key="pack.id"
                class="rounded-xl border border-gray-200 dark:border-zinc-700 p-3 bg-white/60 dark:bg-zinc-800/60 flex flex-col gap-2"
            >
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <div class="font-semibold text-gray-800 dark:text-zinc-100 truncate">
                            {{ pack.title }}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                            {{
                                $t("sticker_packs.count_label", {
                                    count: pack.sticker_count,
                                })
                            }}
                            &middot;
                            {{ $t(`sticker_packs.type_${pack.pack_type}`) }}
                        </div>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <button
                            type="button"
                            class="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-600 dark:text-zinc-300"
                            :title="$t('sticker_packs.export')"
                            @click="exportPack(pack)"
                        >
                            <MaterialDesignIcon icon-name="export" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="rounded-lg p-1.5 hover:bg-red-50 dark:hover:bg-red-950/30 text-red-600"
                            :title="$t('sticker_packs.delete')"
                            @click="deletePack(pack)"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                        </button>
                    </div>
                </div>
                <div v-if="pack.stickers && pack.stickers.length > 0" class="grid grid-cols-6 gap-1.5 mt-1">
                    <StickerView
                        v-for="s in pack.stickers.slice(0, 12)"
                        :key="s.id"
                        :src="stickerImageUrl(s.id)"
                        :image-type="s.image_type"
                        size="xs"
                        class="rounded border border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900"
                    />
                </div>
                <div v-else class="text-xs text-gray-500 dark:text-zinc-400 italic mt-1">
                    {{ $t("sticker_packs.empty_pack") }}
                </div>
            </div>
        </div>

        <div
            v-if="createOpen"
            class="fixed inset-0 z-[150] flex items-center justify-center bg-black/60 p-4"
            @click.self="createOpen = false"
        >
            <div
                class="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl border border-gray-200 dark:border-zinc-700"
            >
                <header class="px-4 py-3 border-b border-gray-200 dark:border-zinc-700 font-semibold">
                    {{ $t("sticker_packs.create_title") }}
                </header>
                <div class="p-4 flex flex-col gap-3">
                    <input
                        v-model="newPackTitle"
                        type="text"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800"
                        :placeholder="$t('sticker_packs.field_title')"
                        maxlength="80"
                    />
                    <input
                        v-model="newPackShortName"
                        type="text"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800"
                        :placeholder="$t('sticker_packs.field_short_name')"
                        maxlength="32"
                    />
                    <textarea
                        v-model="newPackDescription"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800"
                        :placeholder="$t('sticker_packs.field_description')"
                        rows="2"
                        maxlength="280"
                    />
                    <select
                        v-model="newPackType"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800"
                    >
                        <option value="static">{{ $t("sticker_packs.type_static") }}</option>
                        <option value="animated">{{ $t("sticker_packs.type_animated") }}</option>
                        <option value="video">{{ $t("sticker_packs.type_video") }}</option>
                        <option value="mixed">{{ $t("sticker_packs.type_mixed") }}</option>
                    </select>
                    <label class="flex items-center gap-2 text-sm">
                        <input v-model="newPackStrict" type="checkbox" />
                        {{ $t("sticker_packs.strict_label") }}
                    </label>
                </div>
                <footer
                    class="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900/50"
                >
                    <button
                        type="button"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm"
                        @click="createOpen = false"
                    >
                        {{ $t("common.cancel") }}
                    </button>
                    <button
                        type="button"
                        class="rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm"
                        :disabled="!newPackTitle"
                        @click="confirmCreatePack"
                    >
                        {{ $t("sticker_packs.create") }}
                    </button>
                </footer>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import StickerView from "./StickerView.vue";
import ToastUtils from "../../js/ToastUtils.js";
import DialogUtils from "../../js/DialogUtils.js";

export default {
    name: "StickerPacksManager",
    components: { MaterialDesignIcon, StickerView },
    data() {
        return {
            packs: [],
            createOpen: false,
            newPackTitle: "",
            newPackShortName: "",
            newPackDescription: "",
            newPackType: "mixed",
            newPackStrict: true,
        };
    },
    mounted() {
        this.loadPacks();
    },
    methods: {
        async loadPacks() {
            try {
                const r = await window.api.get("/api/v1/sticker-packs");
                this.packs = r.data?.packs || [];
            } catch (e) {
                console.error(e);
                this.packs = [];
            }
        },
        stickerImageUrl(id) {
            return `/api/v1/stickers/${id}/image`;
        },
        openCreatePack() {
            this.newPackTitle = "";
            this.newPackShortName = "";
            this.newPackDescription = "";
            this.newPackType = "mixed";
            this.newPackStrict = true;
            this.createOpen = true;
        },
        async confirmCreatePack() {
            try {
                await window.api.post("/api/v1/sticker-packs", {
                    title: this.newPackTitle,
                    short_name: this.newPackShortName || null,
                    description: this.newPackDescription || null,
                    pack_type: this.newPackType,
                    is_strict: this.newPackStrict,
                });
                this.createOpen = false;
                ToastUtils.success(this.$t("sticker_packs.created"));
                await this.loadPacks();
            } catch (e) {
                const err = e?.response?.data?.error || "create_failed";
                ToastUtils.error(`${this.$t("sticker_packs.create_failed")}: ${err}`);
            }
        },
        async exportPack(pack) {
            try {
                const r = await window.api.get(`/api/v1/sticker-packs/${pack.id}/export`);
                const blob = new Blob([JSON.stringify(r.data, null, 2)], {
                    type: "application/json",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                const safe =
                    (pack.short_name || pack.title || "pack").toLowerCase().replace(/[^a-z0-9_-]+/g, "_") || "pack";
                a.href = url;
                a.download = `${safe}.meshchatxpack.json`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
                ToastUtils.success(this.$t("sticker_packs.exported"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("sticker_packs.export_failed"));
            }
        },
        async deletePack(pack) {
            const confirmed = await DialogUtils.confirm(this.$t("sticker_packs.confirm_delete", { title: pack.title }));
            if (!confirmed) return;
            try {
                await window.api.delete(`/api/v1/sticker-packs/${pack.id}?with_stickers=true`);
                ToastUtils.success(this.$t("sticker_packs.deleted"));
                await this.loadPacks();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("sticker_packs.delete_failed"));
            }
        },
        triggerInstallInput() {
            this.$refs.installFileInput?.click();
        },
        async onInstallFile(event) {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            try {
                const text = await file.text();
                const doc = JSON.parse(text);
                const r = await window.api.post("/api/v1/sticker-packs/install", { ...doc, replace_duplicates: false });
                const data = r.data || {};
                ToastUtils.success(
                    this.$t("sticker_packs.installed", {
                        imported: data.imported || 0,
                    })
                );
                await this.loadPacks();
            } catch (e) {
                const err = e?.response?.data?.error || "install_failed";
                ToastUtils.error(`${this.$t("sticker_packs.install_failed")}: ${err}`);
            }
        },
    },
};
</script>
