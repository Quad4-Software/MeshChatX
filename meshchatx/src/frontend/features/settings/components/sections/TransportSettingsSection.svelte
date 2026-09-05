<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import ManagementIdentityPicker from "../../../rnpath/components/ManagementIdentityPicker.svelte";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        reticulumInstance?: {
            share_instance?: boolean;
            respond_to_probes?: boolean;
            enable_remote_management?: boolean;
            remote_management_allowed?: string[];
            shared_instance_type?: string;
            instance_name?: string;
            rpc_config_snippet?: string;
            is_connected_to_shared_instance?: boolean;
            [k: string]: any;
        };
        reticulumInstanceSaving?: boolean;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onupdatereticuluminstance?: (patch: Record<string, any>) => void;
        onsaveremotemanagementallowed?: (allowed: string[]) => void;
    }

    let {
        visible = true,
        config = {},
        reticulumInstance = $bindable({}),
        reticulumInstanceSaving = false,
        onupdatefield,
        onupdatereticuluminstance,
        onsaveremotemanagementallowed,
    }: Props = $props();

    let rpcKeyVisible = $state(false);
    let settingsMgmtIdentityPath = $state("");
    let settingsMgmtIdentityHash = $state("");
    let remoteManagementAllowedText = $state("");

    $effect(() => {
        if (Array.isArray(reticulumInstance.remote_management_allowed)) {
            remoteManagementAllowedText = reticulumInstance.remote_management_allowed.join("\n");
        }
    });

    $effect(() => {
        if (settingsMgmtIdentityHash) {
            const current = remoteManagementAllowedText.trim();
            const lines = current ? current.split("\n").map((s) => s.trim()) : [];
            if (!lines.includes(settingsMgmtIdentityHash)) {
                lines.push(settingsMgmtIdentityHash);
                remoteManagementAllowedText = lines.join("\n");
            }
        }
    });

    const displayedRpcConfigSnippet = $derived.by(() => {
        const snippet = reticulumInstance?.rpc_config_snippet;
        if (!snippet) {
            return t("app.rpc_config_unavailable");
        }
        if (rpcKeyVisible) {
            return snippet;
        }
        return snippet.replace(/(rpc_key\s*=\s*)([^\r\n]+)/g, "$1••••••••••••••••");
    });

    function handleSaveRemoteManagementAllowed() {
        const allowed = remoteManagementAllowedText
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean);
        onsaveremotemanagementallowed?.(allowed);
    }

    async function copyRpcConfigSnippet() {
        if (!reticulumInstance.rpc_config_snippet) return;
        try {
            await navigator.clipboard.writeText(reticulumInstance.rpc_config_snippet);
            ToastUtils.success(t("app.rpc_config_copied"));
        } catch {
            ToastUtils.error(t("common.copy_failed"));
        }
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Reticulum</div>
                <h2>{t("app.transport_mode")}</h2>
                <p>{t("app.transport_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="transport-enabled"
                    checked={Boolean(config.is_transport_enabled)}
                    onchange={(val) => onupdatefield?.({ key: "is_transport_enabled", value: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.enable_transport_mode")}</span>
                    <span class="setting-toggle__description">{t("app.transport_toggle_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="share-reticulum-instance"
                    checked={Boolean(reticulumInstance.share_instance)}
                    disabled={reticulumInstanceSaving}
                    onchange={(val) => onupdatereticuluminstance?.({ share_instance: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.share_reticulum_instance")}</span>
                    <span class="setting-toggle__description">{t("app.share_reticulum_instance_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="respond-to-probes"
                    checked={Boolean(reticulumInstance.respond_to_probes)}
                    disabled={reticulumInstanceSaving}
                    onchange={(val) => onupdatereticuluminstance?.({ respond_to_probes: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.respond_to_probes")}</span>
                    <span class="setting-toggle__description">{t("app.respond_to_probes_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="enable-remote-management"
                    checked={Boolean(reticulumInstance.enable_remote_management)}
                    disabled={reticulumInstanceSaving}
                    onchange={(val) => onupdatereticuluminstance?.({ enable_remote_management: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.enable_remote_management")}</span>
                    <span class="setting-toggle__description">{t("app.enable_remote_management_description")}</span>
                </span>
            </label>

            {#if reticulumInstance.enable_remote_management}
                <div class="space-y-2 rounded-xl border border-sem-border bg-sem-surface-muted/40 p-3">
                    <label class="block space-y-1">
                        <span class="text-sm font-medium text-sem-fg">{t("app.remote_management_allowed")}</span>
                        <textarea
                            bind:value={remoteManagementAllowedText}
                            rows="3"
                            class="w-full rounded-xl border border-sem-border bg-sem-surface px-3 py-2 font-mono text-xs text-sem-fg"
                            disabled={reticulumInstanceSaving}
                            placeholder={t("app.remote_management_allowed_placeholder")}></textarea>
                        <span class="text-xs text-sem-fg-muted">{t("app.remote_management_allowed_description")}</span>
                    </label>
                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            class="primary-chip px-3 py-1.5 text-xs cursor-pointer"
                            disabled={reticulumInstanceSaving}
                            onclick={handleSaveRemoteManagementAllowed}
                        >
                            {t("app.remote_management_allowed_save")}
                        </button>
                        <ManagementIdentityPicker
                            bind:value={settingsMgmtIdentityPath}
                            bind:identityHash={settingsMgmtIdentityHash}
                            class="min-w-[16rem] flex-1"
                            defaultName="mgmt"
                            onloaded={() => {}}
                        />
                    </div>
                    {#if settingsMgmtIdentityHash}
                        <p class="text-xs text-sem-fg-muted">
                            {t("remote_mgmt.management_identity")}:
                            <span class="font-mono">{settingsMgmtIdentityHash}</span>
                        </p>
                    {/if}
                </div>
            {/if}

            <div class="grid gap-3 sm:grid-cols-2">
                <label class="block space-y-1">
                    <span class="text-sm font-medium text-sem-fg">{t("app.shared_instance_type")}</span>
                    <select
                        value={reticulumInstance.shared_instance_type || ""}
                        class="w-full rounded-xl border border-sem-border bg-sem-surface px-3 py-2 text-sm text-sem-fg"
                        disabled={reticulumInstanceSaving}
                        onchange={(e) =>
                            onupdatereticuluminstance?.({
                                shared_instance_type: (e.target as HTMLSelectElement).value,
                            })}
                    >
                        <option value="">{t("app.shared_instance_type_default")}</option>
                        <option value="unix">unix</option>
                        <option value="tcp">tcp</option>
                    </select>
                    <span class="text-xs text-sem-fg-muted">{t("app.shared_instance_type_description")}</span>
                </label>
                <label class="block space-y-1">
                    <span class="text-sm font-medium text-sem-fg">{t("app.instance_name")}</span>
                    <input
                        value={reticulumInstance.instance_name || ""}
                        type="text"
                        maxlength="64"
                        class="w-full rounded-xl border border-sem-border bg-sem-surface px-3 py-2 text-sm text-sem-fg"
                        disabled={reticulumInstanceSaving}
                        onchange={(e) =>
                            onupdatereticuluminstance?.({ instance_name: (e.target as HTMLInputElement).value })}
                    />
                    <span class="text-xs text-sem-fg-muted">{t("app.instance_name_description")}</span>
                </label>
            </div>

            <div class="rounded-xl border border-sem-border bg-sem-surface-muted/40 p-3 space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {t("app.rpc_config")}
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {t("app.rpc_config_description")}
                </p>
                {#if reticulumInstance.is_connected_to_shared_instance}
                    <p class="text-xs text-amber-700 dark:text-amber-300">
                        {t("app.connected_to_shared_instance")}
                    </p>
                {/if}
                <div
                    class="relative rounded-lg border border-gray-200/70 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/60"
                >
                    <pre
                        class="text-xs font-mono whitespace-pre-wrap break-all text-sem-fg p-2 pr-12">{displayedRpcConfigSnippet}</pre>
                    {#if reticulumInstance.rpc_config_snippet}
                        <button
                            type="button"
                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center rounded-lg p-1.5 text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted cursor-pointer"
                            aria-label={rpcKeyVisible ? t("app.rpc_key_hide") : t("app.rpc_key_show")}
                            title={rpcKeyVisible ? t("app.rpc_key_hide") : t("app.rpc_key_show")}
                            onclick={() => (rpcKeyVisible = !rpcKeyVisible)}
                        >
                            <MaterialDesignIcon
                                iconName={rpcKeyVisible ? "eye-off-outline" : "eye-outline"}
                                class="w-4 h-4"
                            />
                        </button>
                    {/if}
                </div>
                <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-3 py-2 cursor-pointer"
                    disabled={!reticulumInstance.rpc_config_snippet}
                    onclick={copyRpcConfigSnippet}
                >
                    <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
                    {t("app.copy_rpc_config")}
                </button>
            </div>
        </div>
    </section>
{/if}
