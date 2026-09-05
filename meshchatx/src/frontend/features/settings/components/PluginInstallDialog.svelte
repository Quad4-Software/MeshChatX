<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { permissionLabel } from "../../../js/plugins/pluginPermissions.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        open?: boolean;
        preview?: any;
        confirming?: boolean;
        oncancel?: () => void;
        onconfirm?: (data: {
            grantedPermissions: string[];
            trustPublisher: boolean;
            signer: string;
            signerName: string;
        }) => void;
    }

    let { open = false, preview = null, confirming = false, oncancel, onconfirm }: Props = $props();

    let grantedMap = $state<Record<string, boolean>>({});
    let trustPublisher = $state(false);

    $effect(() => {
        if (open && preview) {
            const next: Record<string, boolean> = {};
            for (const perm of preview.permissions || []) {
                next[perm] = true;
            }
            grantedMap = next;
            trustPublisher = false;
        }
    });

    const networkFetchGranted = $derived(grantedMap["network:fetch"] === true);
    const signatureBlocksInstall = $derived(Boolean(preview?.signature?.present && !preview?.signature?.valid));
    const canTrustPublisher = $derived(
        Boolean(preview?.signature?.valid && preview?.signature?.signer && !preview?.signature?.trusted)
    );

    const signatureLabel = $derived.by(() => {
        const signature = preview?.signature || {};
        if (signature.present && !signature.valid) {
            return t("plugins.install_dialog.signature_invalid");
        }
        if (signature.valid && signature.trusted) {
            return t("plugins.install_dialog.signature_trusted");
        }
        if (signature.valid) {
            return t("plugins.install_dialog.signature_signed");
        }
        return t("plugins.install_dialog.signature_unsigned");
    });

    const signatureClass = $derived.by(() => {
        const signature = preview?.signature || {};
        if (signature.present && !signature.valid) {
            return "text-red-700 dark:text-red-300";
        }
        if (signature.valid && signature.trusted) {
            return "text-green-700 dark:text-green-300";
        }
        if (signature.valid) {
            return "text-sky-700 dark:text-sky-300";
        }
        return "text-sem-fg-muted";
    });

    function labelFor(perm: string) {
        return permissionLabel(perm, (key) => t(key));
    }

    function selectedPermissions() {
        return (preview?.permissions || []).filter((perm: string) => grantedMap[perm]);
    }

    function handleCancel() {
        if (!confirming) {
            oncancel?.();
        }
    }

    function handleConfirm() {
        if (signatureBlocksInstall) return;
        onconfirm?.({
            grantedPermissions: selectedPermissions(),
            trustPublisher,
            signer: preview?.signature?.signer || "",
            signerName: preview?.signature?.signer_name || "",
        });
    }
</script>

{#if open && preview}
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
        <button
            type="button"
            class="absolute inset-0 bg-black/50 border-0"
            aria-label={t("plugins.install_dialog.close")}
            disabled={confirming}
            onclick={handleCancel}
        ></button>
        <div
            class="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-sem-border bg-sem-surface shadow-xl p-5 space-y-4"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="plugin-install-title"
        >
            <h2 id="plugin-install-title" class="text-lg font-semibold text-sem-fg">
                {preview.requires_network_fetch
                    ? t("plugins.install_dialog.network_title")
                    : t("plugins.install_dialog.title")}
            </h2>
            <p class="text-sm text-sem-fg-muted">
                {t("plugins.install_dialog.message", { name: preview.name, id: preview.id })}
            </p>

            <div class="space-y-1">
                <p class="text-sm font-medium text-sem-fg">
                    {preview.name}
                    <span class="text-xs font-normal text-sem-fg-muted">v{preview.version}</span>
                </p>
                {#if preview.description}
                    <p class="text-sm text-sem-fg-muted">
                        {preview.description}
                    </p>
                {/if}
            </div>

            <section class="space-y-2">
                <h3 class="text-sm font-semibold text-sem-fg">
                    {t("plugins.install_dialog.signature")}
                </h3>
                <p class="text-sm {signatureClass}">
                    {signatureLabel}
                </p>
                {#if preview.signature?.signer}
                    <p class="text-xs font-mono break-all text-sem-fg-muted">
                        {preview.signature.signer}
                        {#if preview.signature?.signer_name}
                            <span> ({preview.signature.signer_name})</span>
                        {/if}
                    </p>
                {/if}
                {#if preview.signature?.error}
                    <p class="text-xs text-red-600 dark:text-red-400">
                        {preview.signature.error}
                    </p>
                {/if}
                {#if canTrustPublisher}
                    <label class="inline-flex items-center gap-2 text-xs text-sem-fg">
                        <input bind:checked={trustPublisher} type="checkbox" class="rounded border-sem-border" />
                        {t("plugins.install_dialog.trust_publisher")}
                    </label>
                {/if}
            </section>

            {#if (preview.security_findings || []).length}
                <section class="space-y-2">
                    <h3 class="text-sm font-semibold text-sem-fg">
                        {t("plugins.install_dialog.security_findings")}
                    </h3>
                    <ul class="space-y-1 rounded-md border border-sem-border p-3">
                        {#each preview.security_findings as finding (finding.id)}
                            <li class="text-xs text-sem-fg">
                                <span class="font-semibold uppercase">{finding.severity}</span>
                                {finding.message}
                            </li>
                        {/each}
                    </ul>
                </section>
            {/if}

            {#if (preview.permissions || []).length}
                <section class="space-y-2">
                    <h3 class="text-sm font-semibold text-sem-fg">
                        {t("plugins.install_dialog.permissions")}
                    </h3>
                    <p class="text-xs text-sem-fg-muted">
                        {t("plugins.install_dialog.permissions_hint")}
                    </p>
                    <ul class="space-y-2">
                        {#each preview.permissions as perm (perm)}
                            <li
                                class="flex items-center justify-between gap-3 rounded-md border border-sem-border px-3 py-2"
                            >
                                <span class="text-sm text-sem-fg">{labelFor(perm)}</span>
                                <label class="inline-flex items-center gap-2 text-xs text-sem-fg-muted">
                                    <input
                                        bind:checked={grantedMap[perm]}
                                        type="checkbox"
                                        class="rounded border-sem-border"
                                    />
                                    {t("plugins.install_dialog.grant")}
                                </label>
                            </li>
                        {/each}
                    </ul>
                </section>
            {/if}

            {#if preview.requires_network_fetch}
                <section class="space-y-2">
                    <h3 class="text-sm font-semibold text-sem-fg">
                        {t("plugins.install_dialog.network_endpoints")}
                    </h3>
                    {#if !networkFetchGranted}
                        <p class="text-xs text-amber-700 dark:text-amber-300">
                            {t("plugins.install_dialog.network_endpoints_blocked")}
                        </p>
                    {/if}
                    {#if (preview.network_endpoints || []).length}
                        <ul class="space-y-1 rounded-md border border-sem-border p-3">
                            {#each preview.network_endpoints as endpoint (endpoint)}
                                <li class="text-xs font-mono break-all text-sem-fg">
                                    {endpoint}
                                </li>
                            {/each}
                        </ul>
                    {:else}
                        <p class="text-xs text-sem-fg-muted">
                            {t("plugins.install_dialog.network_endpoints_unknown")}
                        </p>
                    {/if}
                </section>
            {/if}

            <div class="flex justify-end gap-2 pt-2">
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-md border border-sem-border text-sm"
                    disabled={confirming}
                    onclick={handleCancel}
                >
                    {t("plugins.install_dialog.cancel")}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm disabled:opacity-50"
                    disabled={confirming || signatureBlocksInstall}
                    onclick={handleConfirm}
                >
                    {confirming ? t("plugins.settings.installing") : t("plugins.install_dialog.confirm")}
                </button>
            </div>
        </div>
    </div>
{/if}
