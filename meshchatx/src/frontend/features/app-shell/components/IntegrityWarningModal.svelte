<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import { t } from "../../../js/i18n.js";
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";

    interface IntegritySubsystem {
        ok: boolean;
        issues: string[];
    }

    interface IntegrityStatus {
        backend: IntegritySubsystem;
        data: IntegritySubsystem;
    }

    interface Props {
        open?: boolean;
    }

    let { open = $bindable(false) }: Props = $props();

    let dontShowAgain = $state(false);
    let integrity = $state<IntegrityStatus>({
        backend: { ok: true, issues: [] },
        data: { ok: true, issues: [] },
    });

    const issues = $derived([...(integrity.backend?.issues || []), ...(integrity.data?.issues || [])]);

    onMount(async () => {
        const electron = (
            window as unknown as {
                electron?: { getIntegrityStatus?: () => Promise<IntegrityStatus>; appVersion?: () => Promise<string> };
            }
        ).electron;
        if (electron && typeof electron.getIntegrityStatus === "function") {
            try {
                integrity = await electron.getIntegrityStatus();
                const isOk = integrity.backend?.ok && integrity.data?.ok;
                if (!isOk) {
                    const dismissed = localStorage.getItem("integrity_warning_dismissed");
                    const appVersion = typeof electron.appVersion === "function" ? await electron.appVersion() : "";
                    if (dismissed !== appVersion) {
                        open = true;
                    }
                }
            } catch (e) {
                console.error("Failed to check integrity status:", e);
            }
        }
    });

    export async function close(): Promise<void> {
        const electron = (window as unknown as { electron?: { appVersion?: () => Promise<string> } }).electron;
        if (dontShowAgain && electron && typeof electron.appVersion === "function") {
            const appVersion = await electron.appVersion();
            localStorage.setItem("integrity_warning_dismissed", appVersion);
        }
        open = false;
    }

    export async function acknowledgeAndReset(): Promise<void> {
        try {
            const api = (window as unknown as { api?: { post: (url: string) => Promise<unknown> } }).api;
            if (api) {
                await api.post("/api/v1/app/integrity/acknowledge");
            }
            ToastUtils.success(t("about.integrity_acknowledged_reset"));
            open = false;
        } catch (e) {
            ToastUtils.error(t("about.failed_acknowledge_integrity"));
            console.error(e);
        }
    }
</script>

<Modal bind:open maxWidth={500} persistent showClose={false} panelClass="bg-amber-500 text-white">
    {#snippet header()}
        <MaterialDesignIcon iconName="alert-decagram" class="size-6 shrink-0" />
        <h2 class="min-w-0 flex-1 text-lg font-semibold">{t("about.security_integrity")}</h2>
    {/snippet}

    <div class="space-y-3 px-4 py-4 sm:px-5">
        {#if integrity.backend && !integrity.backend.ok}
            <p>
                <strong>{t("about.tampering_detected")}</strong><br />
                {t("about.integrity_backend_error")}
            </p>
        {/if}

        {#if integrity.data && !integrity.data.ok}
            <p>
                <strong>{t("about.tampering_detected")}</strong><br />
                {t("about.integrity_data_error")}
            </p>
        {/if}

        {#if issues.length > 0}
            <details class="rounded-lg bg-amber-600/40 p-3">
                <summary class="cursor-pointer text-sm font-medium">{t("about.technical_issues")}</summary>
                <ul class="mt-2 list-disc pl-5 text-xs">
                    {#each issues as issue, index (`issue-${index}`)}
                        <li>{issue}</li>
                    {/each}
                </ul>
            </details>
        {/if}

        <p class="text-xs opacity-90">{t("about.integrity_warning_footer")}</p>
    </div>

    {#snippet footer()}
        <div class="flex w-full flex-wrap items-center gap-3">
            <label class="flex items-center gap-2 text-sm">
                <input
                    bind:checked={dontShowAgain}
                    type="checkbox"
                    class="rounded-xs border-white/40 bg-transparent text-white focus:ring-white/50"
                />
                <span>{t("app.do_not_show_again")}</span>
            </label>
            <div class="flex-1"></div>
            <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10"
                onclick={close}
            >
                {t("common.continue")}
            </button>
            {#if integrity.data && !integrity.data.ok}
                <button
                    type="button"
                    class="rounded-lg bg-white px-4 py-2 text-sm font-bold text-amber-600 transition-colors hover:bg-amber-50"
                    onclick={acknowledgeAndReset}
                >
                    {t("common.acknowledge_reset")}
                </button>
            {/if}
        </div>
    {/snippet}
</Modal>
