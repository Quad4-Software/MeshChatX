<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import StickerView from "./StickerView.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import { t } from "../../../js/i18n.js";

    let packs = $state<any[]>([]);
    let createOpen = $state(false);
    let newPackTitle = $state("");
    let newPackShortName = $state("");
    let newPackDescription = $state("");
    let newPackType = $state("mixed");
    let newPackStrict = $state(true);

    let installFileInput = $state<HTMLInputElement | null>(null);

    async function loadPacks(): Promise<void> {
        try {
            const r = await window.api.get("/api/v1/sticker-packs");
            packs = r.data?.packs || [];
        } catch (e) {
            console.error(e);
            packs = [];
        }
    }

    function stickerImageUrl(id: string): string {
        return `/api/v1/stickers/${id}/image`;
    }

    function openCreatePack(): void {
        newPackTitle = "";
        newPackShortName = "";
        newPackDescription = "";
        newPackType = "mixed";
        newPackStrict = true;
        createOpen = true;
    }

    async function confirmCreatePack(): Promise<void> {
        try {
            await window.api.post("/api/v1/sticker-packs", {
                title: newPackTitle,
                short_name: newPackShortName || null,
                description: newPackDescription || null,
                pack_type: newPackType,
                is_strict: newPackStrict,
            });
            createOpen = false;
            ToastUtils.success(t("sticker_packs.created"));
            await loadPacks();
        } catch (e: any) {
            const err = e?.response?.data?.error || "create_failed";
            ToastUtils.error(`${t("sticker_packs.create_failed")}: ${err}`);
        }
    }

    async function exportPack(pack: any): Promise<void> {
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
            ToastUtils.success(t("sticker_packs.exported"));
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("sticker_packs.export_failed"));
        }
    }

    async function deletePack(pack: any): Promise<void> {
        const confirmed = await DialogUtils.confirm(t("sticker_packs.confirm_delete", { title: pack.title }));
        if (!confirmed) return;
        try {
            await window.api.delete(`/api/v1/sticker-packs/${pack.id}?with_stickers=true`);
            ToastUtils.success(t("sticker_packs.deleted"));
            await loadPacks();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("sticker_packs.delete_failed"));
        }
    }

    function triggerInstallInput(): void {
        installFileInput?.click();
    }

    async function onInstallFile(event: Event): Promise<void> {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        target.value = "";
        if (!file) return;
        try {
            const text = await file.text();
            const doc = JSON.parse(text);
            const r = await window.api.post("/api/v1/sticker-packs/install", { ...doc, replace_duplicates: false });
            const data = r.data || {};
            ToastUtils.success(
                t("sticker_packs.installed", {
                    imported: data.imported || 0,
                })
            );
            await loadPacks();
        } catch (e: any) {
            const err = e?.response?.data?.error || "install_failed";
            ToastUtils.error(`${t("sticker_packs.install_failed")}: ${err}`);
        }
    }

    onMount(() => {
        loadPacks();
    });
</script>

<div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
        <button
            type="button"
            class="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm font-medium flex items-center gap-1 cursor-pointer"
            onclick={openCreatePack}
        >
            <MaterialDesignIcon iconName="folder-plus-outline" class="size-4" />
            {t("sticker_packs.create")}
        </button>
        <button
            type="button"
            class="rounded-xl border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm hover:border-teal-500 flex items-center gap-1 cursor-pointer"
            onclick={triggerInstallInput}
        >
            <MaterialDesignIcon iconName="package-down" class="size-4" />
            {t("sticker_packs.install_from_file")}
        </button>
        <input
            bind:this={installFileInput}
            type="file"
            accept=".json,application/json"
            class="hidden"
            onchange={onInstallFile}
        />
    </div>

    {#if packs.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("sticker_packs.empty")}
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            {#each packs as pack (pack.id)}
                <div
                    class="rounded-xl border border-sem-border p-3 bg-white/60 dark:bg-zinc-800/60 flex flex-col gap-2"
                >
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="font-semibold text-sem-fg truncate">
                                {pack.title}
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                {t("sticker_packs.count_label", {
                                    count: pack.sticker_count,
                                })}
                                &middot;
                                {t(`sticker_packs.type_${pack.pack_type}`)}
                            </div>
                        </div>
                        <div class="flex items-center gap-1 shrink-0">
                            <button
                                type="button"
                                class="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-sem-surface-muted text-sem-fg-muted cursor-pointer"
                                title={t("sticker_packs.export")}
                                onclick={() => exportPack(pack)}
                            >
                                <MaterialDesignIcon iconName="export" class="size-4" />
                            </button>
                            <button
                                type="button"
                                class="rounded-lg p-1.5 hover:bg-red-50 dark:hover:bg-red-950/30 text-red-600 cursor-pointer"
                                title={t("sticker_packs.delete")}
                                onclick={() => deletePack(pack)}
                            >
                                <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                            </button>
                        </div>
                    </div>
                    {#if pack.stickers && pack.stickers.length > 0}
                        <div class="grid grid-cols-6 gap-1.5 mt-1">
                            {#each pack.stickers.slice(0, 12) as s (s.id)}
                                <StickerView
                                    src={stickerImageUrl(s.id)}
                                    imageType={s.image_type}
                                    size="xs"
                                    class="rounded-sm border border-sem-border bg-sem-surface-muted"
                                />
                            {/each}
                        </div>
                    {:else}
                        <div class="text-xs text-sem-fg-muted italic mt-1">
                            {t("sticker_packs.empty_pack")}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    {#if createOpen}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="fixed inset-0 z-150 flex items-center justify-center bg-black/60 p-4"
            onclick={(e) => {
                if (e.target === e.currentTarget) createOpen = false;
            }}
        >
            <div class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl border border-sem-border">
                <header class="px-4 py-3 border-b border-sem-border font-semibold text-sem-fg">
                    {t("sticker_packs.create_title")}
                </header>
                <div class="p-4 flex flex-col gap-3">
                    <input
                        bind:value={newPackTitle}
                        type="text"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800 text-sem-fg"
                        placeholder={t("sticker_packs.field_title")}
                        maxlength={80}
                    />
                    <input
                        bind:value={newPackShortName}
                        type="text"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800 text-sem-fg"
                        placeholder={t("sticker_packs.field_short_name")}
                        maxlength={32}
                    />
                    <textarea
                        bind:value={newPackDescription}
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800 text-sem-fg"
                        placeholder={t("sticker_packs.field_description")}
                        rows={2}
                        maxlength={280}></textarea>
                    <select
                        bind:value={newPackType}
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-2 py-1.5 bg-white dark:bg-zinc-800 text-sem-fg"
                    >
                        <option value="static">{t("sticker_packs.type_static")}</option>
                        <option value="animated">{t("sticker_packs.type_animated")}</option>
                        <option value="video">{t("sticker_packs.type_video")}</option>
                        <option value="mixed">{t("sticker_packs.type_mixed")}</option>
                    </select>
                    <label class="flex items-center gap-2 text-sm text-sem-fg cursor-pointer">
                        <input bind:checked={newPackStrict} type="checkbox" />
                        {t("sticker_packs.strict_label")}
                    </label>
                </div>
                <footer
                    class="flex items-center justify-end gap-2 px-4 py-3 border-t border-sem-border bg-sem-surface-muted/50"
                >
                    <button
                        type="button"
                        class="rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm cursor-pointer"
                        onclick={() => (createOpen = false)}
                    >
                        {t("common.cancel")}
                    </button>
                    <button
                        type="button"
                        class="rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={!newPackTitle}
                        onclick={confirmCreatePack}
                    >
                        {t("sticker_packs.create")}
                    </button>
                </footer>
            </div>
        </div>
    {/if}
</div>
