<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import AppUpdatePrompt from "./AppUpdatePrompt.svelte";
    import AndroidStorageBridge from "../../../js/AndroidStorageBridge.js";
    import ToastUtils from "../../../js/ToastUtils.js";

    interface Props {
        variant?: "setup" | "upgrade";
        open?: boolean;
        oncompleted?: (payload: unknown) => void;
        ondismissed?: () => void;
    }

    let { variant = "upgrade", open = $bindable(false), oncompleted, ondismissed }: Props = $props();

    let busy = $state(false);
    let status = $state<any>(null);
    let selectedSetupMode = $state<"external" | "internal">("external");
    let storageBridge: AndroidStorageBridge | null = null;

    function ensureStorageBridge(): AndroidStorageBridge {
        if (!storageBridge) {
            storageBridge = new AndroidStorageBridge();
        }
        return storageBridge;
    }

    const setupMode = $derived(variant === "setup");

    const promptTitle = $derived(setupMode ? t("android_storage.setup_title") : t("android_storage.upgrade_title"));

    const promptDescription = $derived(setupMode ? t("android_storage.setup_desc") : t("android_storage.upgrade_desc"));

    const primaryLabel = $derived(setupMode ? t("android_storage.setup_continue") : t("android_storage.upgrade_copy"));

    const secondaryLabel = $derived(setupMode ? "" : t("android_storage.upgrade_stay_internal"));

    export function refreshStatus(): any {
        status = ensureStorageBridge().getStatus();
        return status;
    }

    export function shouldShowSetup(): boolean {
        const s = refreshStatus();
        return Boolean(s?.needs_setup_choice);
    }

    export function shouldShowUpgrade(): boolean {
        const s = refreshStatus();
        return Boolean(s?.needs_upgrade_prompt);
    }

    export function showSetup(): boolean {
        if (!shouldShowSetup()) {
            return false;
        }
        selectedSetupMode = "external";
        open = true;
        return true;
    }

    export function showUpgrade(): boolean {
        if (!shouldShowUpgrade()) {
            return false;
        }
        open = true;
        return true;
    }

    export function hide(): void {
        open = false;
    }

    $effect(() => {
        if (!open) {
            ondismissed?.();
        }
    });

    export async function onPrimary(): Promise<void> {
        if (busy) {
            return;
        }
        busy = true;
        try {
            if (setupMode) {
                const mode = selectedSetupMode || "external";
                const result = ensureStorageBridge().applySetupChoice(mode, status);
                hide();
                oncompleted?.({ action: "setup", mode, restarted: result.restarted });
                if (result.restarted) {
                    ToastUtils.success(t("android_storage.restart_to_apply"));
                }
                return;
            }
            if (!ensureStorageBridge().scheduleCopyToExternalAndRestart()) {
                ToastUtils.error(t("android_storage.failed"));
                return;
            }
            ToastUtils.success(t("android_storage.copy_restart_hint"));
            ensureStorageBridge().restartApp();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("android_storage.failed"));
        } finally {
            busy = false;
        }
    }

    export async function onSecondary(): Promise<void> {
        if (busy || setupMode) {
            return;
        }
        busy = true;
        try {
            if (!ensureStorageBridge().keepInternalAndDismiss()) {
                ToastUtils.error(t("android_storage.failed"));
                return;
            }
            hide();
            oncompleted?.({ action: "stay_internal" });
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("android_storage.failed"));
        } finally {
            busy = false;
        }
    }
</script>

<AppUpdatePrompt
    bind:open
    title={promptTitle}
    description={promptDescription}
    {primaryLabel}
    {secondaryLabel}
    {busy}
    busyText={t("android_storage.working")}
    primaryDisabled={setupMode && !selectedSetupMode}
    onprimary={onPrimary}
    onsecondary={onSecondary}
>
    {#if setupMode}
        <div class="space-y-2 text-left">
            <label
                class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors {selectedSetupMode ===
                'external'
                    ? 'border-blue-500 bg-blue-50/80 dark:bg-blue-950/30'
                    : 'border-sem-border'}"
            >
                <input bind:group={selectedSetupMode} type="radio" class="mt-1" value="external" />
                <span>
                    <span class="font-medium text-sem-fg block">
                        {t("android_storage.setup_external_title")}
                    </span>
                    <span class="text-xs text-sem-fg-muted">
                        {t("android_storage.setup_external_desc")}
                    </span>
                </span>
            </label>
            <label
                class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors {selectedSetupMode ===
                'internal'
                    ? 'border-blue-500 bg-blue-50/80 dark:bg-blue-950/30'
                    : 'border-sem-border'}"
            >
                <input bind:group={selectedSetupMode} type="radio" class="mt-1" value="internal" />
                <span>
                    <span class="font-medium text-sem-fg block">
                        {t("android_storage.setup_internal_title")}
                    </span>
                    <span class="text-xs text-sem-fg-muted">
                        {t("android_storage.setup_internal_desc")}
                    </span>
                </span>
            </label>
        </div>
    {/if}
    {#if status?.active_path}
        <p class="text-[10px] font-mono text-sem-fg-muted break-all">
            {status.active_path}
        </p>
    {/if}
</AppUpdatePrompt>
