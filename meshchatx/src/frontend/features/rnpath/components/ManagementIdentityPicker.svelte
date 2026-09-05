<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { shortHash } from "../lib/pathQuery.js";
    import type { ManagementIdentity } from "../lib/types.js";

    interface Props {
        value?: string;
        identityHash?: string;
        disabled?: boolean;
        defaultName?: string;
        class?: string;
        onloaded?: (identities: ManagementIdentity[]) => void;
    }

    let {
        value = $bindable(""),
        identityHash = $bindable(""),
        disabled = false,
        defaultName = "mgmt",
        class: className = "",
        onloaded,
    }: Props = $props();

    let identities = $state<ManagementIdentity[]>([]);
    let loading = $state(false);
    let creating = $state(false);

    const selectedHash = $derived(identities.find((item) => item.path === value)?.hash || "");

    $effect(() => {
        identityHash = selectedHash;
    });

    export async function loadIdentities(): Promise<void> {
        loading = true;
        try {
            const response = await window.api.get("/api/v1/reticulum/management-identities");
            const data = (response as any).data as { identities?: ManagementIdentity[] } | undefined;
            identities = Array.isArray(data?.identities) ? data.identities : [];
            onloaded?.(identities);
            if (value && !identities.some((item) => item.path === value)) {
                value = "";
            }
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("remote_mgmt.failed_load_identities"));
        } finally {
            loading = false;
        }
    }

    async function createIdentity(): Promise<void> {
        const suggested = defaultName || "mgmt";
        const name = await DialogUtils.prompt(t("remote_mgmt.create_identity_prompt"), suggested);
        if (!name || !String(name).trim()) {
            return;
        }
        creating = true;
        try {
            const response = await window.api.post("/api/v1/reticulum/management-identities", {
                name: String(name).trim(),
            });
            const data = response.data as { identity?: ManagementIdentity } | undefined;
            const identity = data?.identity;
            await loadIdentities();
            if (identity?.path) {
                value = identity.path;
            }
            ToastUtils.success(t("remote_mgmt.identity_created"));
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("remote_mgmt.failed_create_identity"));
        } finally {
            creating = false;
        }
    }

    onMount(() => {
        void loadIdentities();
    });
</script>

<div class="space-y-2">
    <div class="flex flex-wrap items-end gap-2">
        <label class="block min-w-0 flex-1 space-y-1">
            <span class="text-xs font-medium text-sem-fg-muted">{t("remote_mgmt.management_identity")}</span>
            <select bind:value class="input-field w-full font-mono text-xs" disabled={disabled || loading}>
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
            class="secondary-chip px-3 py-2 text-xs cursor-pointer disabled:cursor-not-allowed"
            disabled={disabled || loading}
            onclick={() => void loadIdentities()}
            title={t("common.refresh")}
        >
            <MaterialDesignIcon iconName="refresh" class="size-4" />
        </button>
        <button
            type="button"
            class="secondary-chip px-3 py-2 text-xs cursor-pointer disabled:cursor-not-allowed"
            disabled={disabled || creating}
            onclick={() => void createIdentity()}
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
