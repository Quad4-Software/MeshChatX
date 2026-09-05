<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { t } from "../../../js/i18n.js";

    import {
        type IdentityItem,
        copyIdentityBase32,
        copyToClipboard,
        downloadAllIdentitiesZip,
        downloadIdentityBackup,
        fetchIdentities,
        normalizeBase32,
        switchIdentityWorkflow,
    } from "../lib/identityService.js";

    let identities = $state<IdentityItem[]>([]);
    let isLoading = $state(false);
    let showCreateModal = $state(false);
    let showImportModal = $state(false);
    let newIdentityName = $state("");
    let isCreating = $state(false);
    let identityRestoreBase32 = $state("");
    let identityRestoreInProgress = $state(false);
    let identityRestoreMessage = $state("");
    let identityRestoreError = $state("");
    let expandedAddressHashes = $state<Record<string, boolean>>({});

    let identityFileInput: HTMLInputElement | undefined = $state();

    const currentIdentity = $derived(identities.find((i) => i.is_current) || null);
    const otherIdentities = $derived(identities.filter((i) => !i.is_current));

    function onIdentitySwitchAborted() {
        isCreating = false;
    }

    function onIdentitySwitched() {
        getIdentities();
        isCreating = false;
    }

    function toggleAddresses(hash: string) {
        expandedAddressHashes = {
            ...expandedAddressHashes,
            [hash]: !expandedAddressHashes[hash],
        };
    }

    async function copyAddress(value?: string) {
        await copyToClipboard(value);
    }

    async function getIdentities() {
        isLoading = true;
        try {
            identities = await fetchIdentities(window.api);
        } finally {
            isLoading = false;
        }
    }

    async function downloadIdentityFile() {
        await downloadIdentityBackup(window.api);
    }

    async function copyIdentityBase32Handler() {
        await copyIdentityBase32(window.api);
    }

    async function downloadAllIdentities() {
        await downloadAllIdentitiesZip(window.api);
    }

    async function maybeSwitchToRestoredIdentity(identity?: { hash?: string; display_name?: string }) {
        if (!identity?.hash) {
            return;
        }
        const switchNow = await DialogUtils.confirm(
            t("identities.switch_after_restore_confirm", {
                name: identity.display_name || identity.hash,
            })
        );
        if (!switchNow) {
            return;
        }
        await switchIdentity({
            hash: identity.hash,
            display_name: identity.display_name || identity.hash,
            is_current: false,
        });
    }

    async function restoreIdentityFile(file: File) {
        if (identityRestoreInProgress || !file) return;
        identityRestoreInProgress = true;
        identityRestoreMessage = "";
        identityRestoreError = "";
        try {
            const formData = new FormData();
            formData.append("file", file);
            const response = await window.api.post("/api/v1/identity/restore", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            const message = response.data?.message ?? t("identities.identity_restored");
            identityRestoreMessage = message;
            ToastUtils.success(message);
            await getIdentities();
            showImportModal = false;
            await maybeSwitchToRestoredIdentity(response.data?.identity);
        } catch (e: any) {
            const msg = e?.response?.data?.message || t("identities.identity_restore_failed");
            identityRestoreError = msg;
            ToastUtils.error(msg);
        } finally {
            identityRestoreInProgress = false;
        }
    }

    function onIdentityRestoreFileChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const files = target.files;
        const file = files?.[0] || null;
        identityRestoreError = "";
        identityRestoreMessage = "";
        if (!file) {
            target.value = "";
            return;
        }
        if (file.size === 0) {
            identityRestoreError = t("identities.identity_restore_empty_file");
            ToastUtils.error(identityRestoreError);
            target.value = "";
            return;
        }
        if (file.size > 65536) {
            identityRestoreError = t("identities.identity_restore_file_too_large");
            ToastUtils.error(identityRestoreError);
            target.value = "";
            return;
        }
        restoreIdentityFile(file);
        target.value = "";
    }

    async function restoreIdentityBase32() {
        const normalized = normalizeBase32(identityRestoreBase32);
        if (identityRestoreInProgress || !normalized) return;
        identityRestoreInProgress = true;
        identityRestoreMessage = "";
        identityRestoreError = "";
        try {
            const response = await window.api.post("/api/v1/identity/restore", {
                base32: normalized,
            });
            const message = response.data?.message ?? t("identities.identity_restored");
            identityRestoreMessage = message;
            identityRestoreBase32 = "";
            ToastUtils.success(message);
            await getIdentities();
            showImportModal = false;
            await maybeSwitchToRestoredIdentity(response.data?.identity);
        } catch (e: any) {
            const msg = e?.response?.data?.message || t("identities.identity_restore_failed");
            identityRestoreError = msg;
            ToastUtils.error(msg);
        } finally {
            identityRestoreInProgress = false;
        }
    }

    async function createIdentity() {
        if (!newIdentityName.trim()) {
            ToastUtils.warning(t("identities.enter_display_name_warning"));
            return;
        }

        isCreating = true;
        try {
            await window.api.post("/api/v1/identities/create", {
                display_name: newIdentityName.trim(),
            });
            ToastUtils.success(t("identities.created"));
            showCreateModal = false;
            newIdentityName = "";
            await getIdentities();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("identities.failed_create"));
        } finally {
            isCreating = false;
        }
    }

    async function switchIdentity(identity: IdentityItem) {
        await switchIdentityWorkflow(window.api, identity, (busy) => {
            isCreating = busy;
        });
    }

    async function deleteIdentity(identity: IdentityItem) {
        if (!(await DialogUtils.confirm(t("identities.delete_confirm", { name: identity.display_name })))) {
            return;
        }

        try {
            await window.api.delete(`/api/v1/identities/${identity.hash}`);
            ToastUtils.success(t("identities.deleted"));
            await getIdentities();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("identities.failed_delete"));
        }
    }

    onMount(() => {
        getIdentities();
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("identity-switching-abort", onIdentitySwitchAborted);
    });

    onDestroy(() => {
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        GlobalEmitter.off("identity-switching-abort", onIdentitySwitchAborted);
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg">
    <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6">
        <div class="space-y-0 w-full max-w-5xl mx-auto min-w-0">
            <div class="identities-section identities-section--hero">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div class="space-y-2 flex-1 min-w-0">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {t("identities.eyebrow")}
                        </div>
                        <h1 class="text-2xl sm:text-3xl font-black text-sem-fg tracking-tight">
                            {t("identities.title")}
                        </h1>
                        <p class="text-sm text-sem-fg-muted leading-relaxed max-w-xl">
                            {t("identities.manage")}
                        </p>
                    </div>
                    <div class="flex flex-wrap items-center gap-2 shrink-0">
                        <button
                            type="button"
                            class="primary-chip cursor-pointer"
                            onclick={() => (showCreateModal = true)}
                        >
                            <MaterialDesignIcon iconName="plus" class="size-4" />
                            <span class="hidden sm:inline">{t("identities.new_identity")}</span>
                        </button>
                        <button
                            type="button"
                            class="secondary-chip cursor-pointer"
                            onclick={() => (showImportModal = true)}
                        >
                            <MaterialDesignIcon iconName="file-import" class="size-4" />
                            <span class="hidden sm:inline">{t("identities.import")}</span>
                        </button>
                        <button
                            type="button"
                            class="secondary-chip cursor-pointer disabled:opacity-50"
                            disabled={identities.length === 0}
                            onclick={downloadAllIdentities}
                        >
                            <MaterialDesignIcon iconName="file-export" class="size-4" />
                            <span class="hidden sm:inline">{t("identities.export_all")}</span>
                        </button>
                    </div>
                </div>
            </div>

            <input
                bind:this={identityFileInput}
                type="file"
                accept=".bin,.key,.identity,application/octet-stream,*/*"
                class="hidden"
                onchange={onIdentityRestoreFileChange}
            />

            {#if isLoading && identities.length === 0}
                <div class="identities-section">
                    {#each [1, 2, 3, 4] as i (i)}
                        <div class="flex items-center gap-3 border-b border-gray-100 px-1 py-3 dark:border-zinc-800">
                            <div
                                class="size-10 sm:size-12 rounded-full bg-gray-200 dark:bg-zinc-700 animate-pulse shrink-0"
                            ></div>
                            <div class="flex-1 min-w-0 space-y-2">
                                <div class="h-4 w-32 bg-gray-200 dark:bg-zinc-700 rounded-sm animate-pulse"></div>
                                <div class="h-3 w-48 bg-sem-surface-muted rounded-sm animate-pulse"></div>
                            </div>
                        </div>
                    {/each}
                </div>
            {:else if currentIdentity}
                <div class="identities-section space-y-4">
                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                        {t("identities.active_identity")}
                    </div>
                    <div class="flex items-center gap-3 sm:gap-4">
                        <div class="size-10 sm:size-12 shrink-0">
                            <LxmfUserIcon
                                iconName={currentIdentity.icon_name}
                                iconForegroundColour={currentIdentity.icon_foreground_colour}
                                iconBackgroundColour={currentIdentity.icon_background_colour}
                                iconClass="w-full h-full"
                            />
                        </div>
                        <div class="min-w-0 flex-1">
                            <div class="flex flex-wrap items-center gap-2">
                                <h2 class="text-lg font-bold text-sem-fg truncate">
                                    {currentIdentity.display_name}
                                </h2>
                                <span
                                    class="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-[10px] font-semibold uppercase tracking-wide"
                                >
                                    {t("identities.current")}
                                </span>
                            </div>
                            {#if currentIdentity.message_count != null}
                                <p class="text-sm text-sem-fg-muted mt-0.5">
                                    {t("identities.message_count", { count: currentIdentity.message_count })}
                                </p>
                            {/if}
                        </div>
                    </div>

                    <div class="grid gap-3 sm:grid-cols-2">
                        <div class="address-card">
                            <div class="address-card__label">{t("app.identity_hash")}</div>
                            <div class="address-card__value monospace-field">{currentIdentity.hash}</div>
                            <button
                                type="button"
                                class="address-card__action cursor-pointer"
                                onclick={() => copyAddress(currentIdentity.hash)}
                            >
                                <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
                                {t("app.copy")}
                            </button>
                        </div>
                        {#if currentIdentity.lxmf_address}
                            <div class="address-card">
                                <div class="address-card__label">{t("app.lxmf_address")}</div>
                                <div class="address-card__value monospace-field">
                                    {currentIdentity.lxmf_address}
                                </div>
                                <button
                                    type="button"
                                    class="address-card__action cursor-pointer"
                                    onclick={() => copyAddress(currentIdentity.lxmf_address)}
                                >
                                    <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
                                    {t("app.copy")}
                                </button>
                            </div>
                        {/if}
                        {#if currentIdentity.lxst_address}
                            <div class="address-card">
                                <div class="address-card__label">{t("identities.lxst_address")}</div>
                                <div class="address-card__value monospace-field">
                                    {currentIdentity.lxst_address}
                                </div>
                                <button
                                    type="button"
                                    class="address-card__action cursor-pointer"
                                    onclick={() => copyAddress(currentIdentity.lxst_address)}
                                >
                                    <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
                                    {t("app.copy")}
                                </button>
                            </div>
                        {/if}
                    </div>

                    <div class="flex flex-wrap gap-2">
                        <button type="button" class="secondary-chip cursor-pointer" onclick={downloadIdentityFile}>
                            <MaterialDesignIcon iconName="file-export" class="size-4" />
                            {t("identities.export_key_file")}
                        </button>
                        <button type="button" class="secondary-chip cursor-pointer" onclick={copyIdentityBase32Handler}>
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                            {t("identities.copy_base32")}
                        </button>
                    </div>
                </div>
            {/if}

            {#if !isLoading && otherIdentities.length > 0}
                <div class="identities-section">
                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted mb-3">
                        {t("identities.other_identities")}
                    </div>
                    <div class="divide-y divide-gray-100 dark:divide-zinc-800">
                        {#each otherIdentities as identity (identity.hash)}
                            <div
                                class="identity-row group py-3 px-1 transition-colors hover:bg-gray-50/80 dark:hover:bg-zinc-900/70"
                            >
                                <div class="flex items-center gap-3">
                                    <div class="size-10 sm:size-12 shrink-0">
                                        <LxmfUserIcon
                                            iconName={identity.icon_name}
                                            iconForegroundColour={identity.icon_foreground_colour}
                                            iconBackgroundColour={identity.icon_background_colour}
                                            iconClass="w-full h-full"
                                        />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-semibold text-sem-fg truncate">
                                            {identity.display_name}
                                        </div>
                                        {#if identity.message_count != null}
                                            <p class="text-xs text-sem-fg-muted mt-0.5">
                                                {t("identities.message_count", { count: identity.message_count })}
                                            </p>
                                        {/if}
                                    </div>
                                    <div class="flex items-center gap-2 shrink-0">
                                        <button
                                            type="button"
                                            class="secondary-chip cursor-pointer"
                                            title={t("identities.switch")}
                                            onclick={() => switchIdentity(identity)}
                                        >
                                            <MaterialDesignIcon iconName="swap-horizontal" class="size-4" />
                                            <span class="hidden sm:inline">{t("identities.switch_label")}</span>
                                        </button>
                                        <button
                                            type="button"
                                            class="p-2 rounded-xl text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition cursor-pointer"
                                            title={t("identities.delete")}
                                            onclick={() => deleteIdentity(identity)}
                                        >
                                            <MaterialDesignIcon iconName="delete-outline" class="size-5" />
                                        </button>
                                    </div>
                                </div>
                                {#if identity.lxmf_address || identity.lxst_address || identity.hash}
                                    <div class="mt-2 pl-11 sm:pl-14">
                                        <button
                                            type="button"
                                            class="text-xs font-semibold text-sem-accent hover:underline cursor-pointer"
                                            onclick={() => toggleAddresses(identity.hash)}
                                        >
                                            {expandedAddressHashes[identity.hash]
                                                ? t("identities.hide_addresses")
                                                : t("identities.show_addresses")}
                                        </button>
                                        {#if expandedAddressHashes[identity.hash]}
                                            <div class="grid gap-2 mt-2 sm:grid-cols-2">
                                                <div class="address-card">
                                                    <div class="address-card__label">{t("app.identity_hash")}</div>
                                                    <div class="address-card__value monospace-field text-xs">
                                                        {identity.hash}
                                                    </div>
                                                    <button
                                                        type="button"
                                                        class="address-card__action cursor-pointer"
                                                        onclick={() => copyAddress(identity.hash)}
                                                    >
                                                        <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
                                                        {t("app.copy")}
                                                    </button>
                                                </div>
                                                {#if identity.lxmf_address}
                                                    <div class="address-card">
                                                        <div class="address-card__label">{t("app.lxmf_address")}</div>
                                                        <div class="address-card__value monospace-field text-xs">
                                                            {identity.lxmf_address}
                                                        </div>
                                                        <button
                                                            type="button"
                                                            class="address-card__action cursor-pointer"
                                                            onclick={() => copyAddress(identity.lxmf_address)}
                                                        >
                                                            <MaterialDesignIcon
                                                                iconName="content-copy"
                                                                class="w-4 h-4"
                                                            />
                                                            {t("app.copy")}
                                                        </button>
                                                    </div>
                                                {/if}
                                                {#if identity.lxst_address}
                                                    <div class="address-card">
                                                        <div class="address-card__label">
                                                            {t("identities.lxst_address")}
                                                        </div>
                                                        <div class="address-card__value monospace-field text-xs">
                                                            {identity.lxst_address}
                                                        </div>
                                                        <button
                                                            type="button"
                                                            class="address-card__action cursor-pointer"
                                                            onclick={() => copyAddress(identity.lxst_address)}
                                                        >
                                                            <MaterialDesignIcon
                                                                iconName="content-copy"
                                                                class="w-4 h-4"
                                                            />
                                                            {t("app.copy")}
                                                        </button>
                                                    </div>
                                                {/if}
                                            </div>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if !isLoading && identities.length === 0}
                <div class="identities-section py-12 text-center text-sem-fg-muted">
                    <MaterialDesignIcon iconName="account-group" class="size-12 mx-auto mb-3 opacity-40" />
                    <h3 class="text-lg font-semibold text-sem-fg">
                        {t("identities.no_identities")}
                    </h3>
                    <p class="mt-1 text-sm">{t("identities.create_first")}</p>
                    <button
                        type="button"
                        class="primary-chip mt-4 cursor-pointer"
                        onclick={() => (showCreateModal = true)}
                    >
                        <MaterialDesignIcon iconName="plus" class="size-4" />
                        {t("identities.new_identity")}
                    </button>
                </div>
            {/if}
        </div>
    </div>

    {#if showCreateModal}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <div
            class="fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            onclick={(e) => {
                if (e.target === e.currentTarget) showCreateModal = false;
            }}
        >
            <div class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                    <h2 class="text-lg font-bold text-sem-fg">
                        {t("identities.new_identity")}
                    </h2>
                    <button
                        type="button"
                        class="text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                        onclick={() => (showCreateModal = false)}
                    >
                        <MaterialDesignIcon iconName="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-sem-fg-muted">{t("identities.generate_fresh")}</p>
                    <div>
                        <label
                            for="new-identity-name-input"
                            class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1"
                        >
                            {t("identities.display_name")}
                        </label>
                        <input
                            id="new-identity-name-input"
                            bind:value={newIdentityName}
                            type="text"
                            placeholder={t("identities.display_name_hint")}
                            class="input-field"
                            onkeydown={(e) => {
                                if (e.key === "Enter") createIdentity();
                            }}
                        />
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-sem-border flex justify-end gap-2">
                    <button
                        type="button"
                        class="secondary-chip cursor-pointer"
                        onclick={() => (showCreateModal = false)}
                    >
                        {t("common.cancel")}
                    </button>
                    <button
                        type="button"
                        class="primary-chip cursor-pointer"
                        disabled={isCreating}
                        onclick={createIdentity}
                    >
                        <MaterialDesignIcon
                            iconName={isCreating ? "loading" : "check"}
                            class="size-4 {isCreating ? 'animate-spin' : ''}"
                        />
                        {t("common.add")}
                    </button>
                </div>
            </div>
        </div>
    {/if}

    {#if showImportModal}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <div
            class="fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            onclick={(e) => {
                if (e.target === e.currentTarget) showImportModal = false;
            }}
        >
            <div class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                    <h2 class="text-lg font-bold text-sem-fg">
                        {t("identities.import")}
                    </h2>
                    <button
                        type="button"
                        class="text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                        onclick={() => (showImportModal = false)}
                    >
                        <MaterialDesignIcon iconName="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-sem-fg-muted">{t("identities.import_hint")}</p>
                    <p class="text-xs text-sem-fg-muted">
                        {t("identities.import_key_only_hint")}
                    </p>
                    <button
                        type="button"
                        class="w-full secondary-chip justify-center cursor-pointer"
                        disabled={identityRestoreInProgress}
                        onclick={() => identityFileInput?.click()}
                    >
                        {#if identityRestoreInProgress}
                            <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                        {:else}
                            <MaterialDesignIcon iconName="upload" class="size-4" />
                        {/if}
                        {t("identities.upload_key_file")}
                    </button>
                    <div class="border-t border-sem-border pt-4 space-y-3">
                        <label
                            for="identity-restore-b32"
                            class="block text-xs uppercase tracking-wider font-semibold text-gray-500"
                        >
                            {t("identities.paste_base32")}
                        </label>
                        <textarea
                            id="identity-restore-b32"
                            bind:value={identityRestoreBase32}
                            rows="3"
                            class="input-field font-mono text-xs w-full"
                            placeholder={t("identities.paste_base32_placeholder")}
                            disabled={identityRestoreInProgress}></textarea>
                        {#if identityRestoreError}
                            <div role="alert" class="text-sm text-red-600 dark:text-red-400">
                                {identityRestoreError}
                            </div>
                        {/if}
                        {#if identityRestoreMessage}
                            <div class="text-sm text-green-600 dark:text-green-400">
                                {identityRestoreMessage}
                            </div>
                        {/if}
                        <button
                            type="button"
                            class="primary-chip cursor-pointer"
                            disabled={identityRestoreInProgress || !identityRestoreBase32.trim()}
                            onclick={restoreIdentityBase32}
                        >
                            {#if identityRestoreInProgress}
                                <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                            {/if}
                            {identityRestoreInProgress ? t("identities.restoring") : t("identities.confirm_restore")}
                        </button>
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-sem-border">
                    <button
                        type="button"
                        class="w-full secondary-chip justify-center cursor-pointer"
                        onclick={() => (showImportModal = false)}
                    >
                        {t("common.cancel")}
                    </button>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .identities-section {
        width: 100%;
        border-bottom: 1px solid rgba(229, 231, 235, 0.6);
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    :global(.dark) .identities-section {
        border-bottom-color: rgba(39, 39, 42, 0.6);
    }
    .identities-section--hero {
        border-bottom: 1px solid rgba(229, 231, 235, 0.6);
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    :global(.dark) .identities-section--hero {
        border-bottom-color: rgba(39, 39, 42, 0.6);
    }
</style>
