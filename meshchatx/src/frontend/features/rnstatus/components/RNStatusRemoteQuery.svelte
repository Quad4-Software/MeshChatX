<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { shortHash } from "../lib/statusFormat.js";
    import { fetchManagementIdentities, createManagementIdentity } from "../lib/statusPoller.js";
    import type { ManagementIdentityItem } from "../lib/types.js";

    interface Props {
        remoteHash: string;
        identityPath: string;
        remoteTimeout: number;
        activeRemoteHash: string;
        disabled?: boolean;
        onClearRemote?: () => void;
    }

    let {
        remoteHash = $bindable(""),
        identityPath = $bindable(""),
        remoteTimeout = $bindable(15),
        activeRemoteHash = "",
        disabled = false,
        onClearRemote,
    }: Props = $props();

    let identities: ManagementIdentityItem[] = $state([]);
    let loadingIdentities = $state(false);
    let creatingIdentity = $state(false);

    const selectedHash = $derived(identities.find((item) => item.path === identityPath)?.hash || "");

    async function loadIdentities() {
        loadingIdentities = true;
        try {
            identities = await fetchManagementIdentities();
            if (identityPath && !identities.some((item) => item.path === identityPath)) {
                identityPath = "";
            }
        } catch (error: unknown) {
            const err = error as { response?: { data?: { message?: string } } };
            ToastUtils.error(err?.response?.data?.message || t("remote_mgmt.failed_load_identities"));
        } finally {
            loadingIdentities = false;
        }
    }

    async function handleCreateIdentity() {
        const name = await DialogUtils.prompt(t("remote_mgmt.create_identity_prompt"), "mgmt");
        if (!name || !String(name).trim()) {
            return;
        }
        creatingIdentity = true;
        try {
            const identity = await createManagementIdentity(String(name).trim());
            await loadIdentities();
            if (identity?.path) {
                identityPath = identity.path;
            }
            ToastUtils.success(t("remote_mgmt.identity_created"));
        } catch (error: unknown) {
            const err = error as { response?: { data?: { message?: string } } };
            ToastUtils.error(err?.response?.data?.message || t("remote_mgmt.failed_create_identity"));
        } finally {
            creatingIdentity = false;
        }
    }

    onMount(() => {
        void loadIdentities();
    });
</script>

<div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
    <h2 class="text-sm font-semibold text-sem-fg">
        {t("rnstatus.remote_query")}
    </h2>
    <p class="text-xs text-sem-fg-muted">
        {t("rnstatus.remote_query_hint")}
    </p>
    <div class="grid gap-3 lg:grid-cols-2">
        <label class="block space-y-1">
            <span class="text-xs font-medium text-sem-fg-muted">
                {t("rnstatus.remote_transport_hash")}
            </span>
            <input
                bind:value={remoteHash}
                type="text"
                class="input-field font-mono text-xs"
                placeholder={t("rnstatus.remote_transport_placeholder")}
                {disabled}
            />
        </label>
        <label class="block space-y-1">
            <span class="text-xs font-medium text-sem-fg-muted">
                {t("rnstatus.remote_timeout")}
            </span>
            <input bind:value={remoteTimeout} type="number" min="1" step="1" class="input-field text-sm" {disabled} />
        </label>
    </div>

    <div class="space-y-2">
        <div class="flex flex-wrap items-end gap-2">
            <label class="block min-w-0 flex-1 space-y-1">
                <span class="text-xs font-medium text-sem-fg-muted">
                    {t("remote_mgmt.management_identity")}
                </span>
                <select
                    bind:value={identityPath}
                    class="input-field w-full font-mono text-xs"
                    disabled={disabled || loadingIdentities}
                >
                    <option value="">{t("remote_mgmt.select_identity")}</option>
                    {#each identities as item (item.path)}
                        <option value={item.path}>
                            {item.name} ({shortHash(item.hash)})
                        </option>
                    {/each}
                </select>
            </label>
            <button
                type="button"
                class="secondary-chip px-3 py-2 text-xs"
                disabled={disabled || loadingIdentities}
                onclick={() => void loadIdentities()}
                aria-label="Refresh management identities"
            >
                <MaterialDesignIcon iconName="refresh" class="size-4" />
            </button>
            <button
                type="button"
                class="secondary-chip px-3 py-2 text-xs"
                disabled={disabled || creatingIdentity}
                onclick={() => void handleCreateIdentity()}
            >
                <MaterialDesignIcon iconName="plus" class="size-4" />
                {t("remote_mgmt.create_identity")}
            </button>
        </div>
        {#if selectedHash}
            <p class="font-mono text-[10px] text-sem-fg-muted break-all">
                {selectedHash}
            </p>
        {/if}
    </div>

    {#if activeRemoteHash}
        <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="font-mono text-amber-700 dark:text-amber-300">
                {t("rnstatus.remote_active", { hash: activeRemoteHash })}
            </span>
            <button
                type="button"
                class="inline-flex items-center px-2 py-1 rounded-lg border border-gray-300 dark:border-zinc-600 bg-sem-surface text-xs font-medium text-sem-fg hover:bg-sem-surface-muted"
                onclick={onClearRemote}
            >
                {t("rnstatus.use_local")}
            </button>
        </div>
    {/if}
</div>
