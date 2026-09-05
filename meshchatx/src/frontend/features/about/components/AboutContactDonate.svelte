<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { DEVELOPER_LXMF_ALTERNATE, DEVELOPER_LXMF_PRIMARY, MONERO_DONATE_ADDRESS } from "../lib/constants.js";

    let showContactSupport = $state(false);

    async function copyValue(value: string, labelKey: string): Promise<void> {
        if (!value) return;
        const label = t(labelKey);
        try {
            await navigator.clipboard.writeText(value);
            ToastUtils.success(t("about.copied_label_to_clipboard", { label }));
        } catch {
            ToastUtils.error(t("about.failed_to_copy_label", { label }));
        }
    }
</script>

<div class="mt-6 pt-6 border-t border-gray-200/70 dark:border-zinc-800/80">
    <button
        type="button"
        class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip w-full justify-between text-left"
        aria-expanded={showContactSupport}
        onclick={() => (showContactSupport = !showContactSupport)}
    >
        <div class="flex items-center gap-3 min-w-0">
            <span
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sem-surface-muted text-sem-fg-muted"
            >
                <MaterialDesignIcon iconName="card-account-details-outline" class="size-[22px]" />
            </span>
            <span class="text-xs font-semibold uppercase tracking-wide text-sem-fg truncate">
                {t("about.contact_support_title")}
            </span>
        </div>
        <MaterialDesignIcon
            iconName={showContactSupport ? "chevron-up" : "chevron-down"}
            class="size-[22px] shrink-0 text-sem-fg-muted transition-colors"
        />
    </button>

    {#if showContactSupport}
        <div class="mt-6 flex flex-col gap-6">
            <div class="flex flex-col gap-3">
                <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide flex items-center gap-2">
                    <MaterialDesignIcon iconName="account-circle-outline" class="size-4" />
                    {t("about.contact_developer")}
                </div>
                <div class="flex flex-col gap-2">
                    <div
                        class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                    >
                        <a
                            href={`#/messages/${DEVELOPER_LXMF_PRIMARY}`}
                            class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 break-all leading-snug text-left no-underline"
                            title={t("about.contact_open_messages")}
                        >
                            {DEVELOPER_LXMF_PRIMARY}
                        </a>
                        <button
                            type="button"
                            class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                            aria-label={t("about.contact_copy_address")}
                            onclick={() => copyValue(DEVELOPER_LXMF_PRIMARY, "about.contact_lxmf_address")}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        </button>
                    </div>
                    <div
                        class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                    >
                        <a
                            href={`#/messages/${DEVELOPER_LXMF_ALTERNATE}`}
                            class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 break-all leading-snug text-left no-underline"
                            title={t("about.contact_open_messages")}
                        >
                            {DEVELOPER_LXMF_ALTERNATE}
                        </a>
                        <button
                            type="button"
                            class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                            aria-label={t("about.contact_copy_address")}
                            onclick={() => copyValue(DEVELOPER_LXMF_ALTERNATE, "about.contact_alternate")}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        </button>
                    </div>
                </div>
                <div
                    class="text-xs text-sem-fg-muted bg-sem-surface-muted/40 p-3 rounded-xl border border-sem-border flex items-start gap-2"
                >
                    <MaterialDesignIcon iconName="information-outline" class="size-4 shrink-0 mt-0.5" />
                    <span>{t("about.contact_propagation_hint")}</span>
                </div>
            </div>

            <div class="border-t border-sem-border/90"></div>

            <div class="flex flex-col gap-3">
                <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide flex items-center gap-2">
                    <MaterialDesignIcon iconName="hand-heart" class="size-4" />
                    {t("about.donate_label")}
                </div>
                <div>
                    <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide mb-1.5">
                        {t("about.donate_monero_label")}
                    </div>
                    <div
                        class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                    >
                        <span
                            class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted break-all leading-snug select-all"
                        >
                            {MONERO_DONATE_ADDRESS}
                        </span>
                        <button
                            type="button"
                            class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                            aria-label={t("about.donate_copy_monero")}
                            onclick={() => copyValue(MONERO_DONATE_ADDRESS, "about.donate_monero_label")}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        </button>
                    </div>
                </div>

                <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                    <a
                        href="https://ko-fi.com/quad4"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-sem-border bg-sem-surface-muted/40 hover:bg-sem-surface-muted text-sem-fg text-xs font-semibold transition-colors no-underline"
                    >
                        <MaterialDesignIcon iconName="coffee" class="size-[18px] text-sem-fg-muted" />
                        {t("about.donate_kofi")}
                    </a>
                    <a
                        href="https://buymeacoffee.com/quad4"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-sem-border bg-sem-surface-muted/40 hover:bg-sem-surface-muted text-sem-fg text-xs font-semibold transition-colors no-underline"
                    >
                        <MaterialDesignIcon iconName="cup" class="size-[18px] text-sem-fg-muted" />
                        {t("about.donate_buymeacoffee")}
                    </a>
                </div>
            </div>
        </div>
    {/if}
</div>
