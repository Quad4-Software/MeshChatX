<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        androidShellPrivacy?: {
            blockScreenshots?: boolean;
            clearClipboardOnBackground?: boolean;
            [k: string]: any;
        };
        remoteBackendUrl?: string;
        effectiveBackendUrl?: string;
        remoteBackendActive?: boolean;
        onupdateBlockScreenshots?: (val: boolean) => void;
        onupdateClearClipboardOnBackground?: (val: boolean) => void;
        onupdateRemoteBackendUrl?: (val: string) => void;
        onapplyRemoteBackend?: () => void;
        onclearRemoteBackend?: () => void;
        onshareApk?: () => void;
    }

    let {
        visible = true,
        androidShellPrivacy = {},
        remoteBackendUrl = "",
        effectiveBackendUrl = "",
        remoteBackendActive = false,
        onupdateBlockScreenshots,
        onupdateClearClipboardOnBackground,
        onupdateRemoteBackendUrl,
        onapplyRemoteBackend,
        onclearRemoteBackend,
        onshareApk,
    }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Android</div>
                <h2>{t("settings.android_privacy_heading")}</h2>
                <p>{t("settings.android_privacy_desc")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <input
                    checked={androidShellPrivacy.blockScreenshots}
                    type="checkbox"
                    class="rounded-sm"
                    onchange={(e) => onupdateBlockScreenshots?.((e.target as HTMLInputElement).checked)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.android_block_screenshots")}</span>
                    <span class="setting-toggle__description">{t("settings.android_block_screenshots_desc")}</span>
                </span>
            </label>
            <label class="setting-toggle">
                <input
                    checked={androidShellPrivacy.clearClipboardOnBackground}
                    type="checkbox"
                    class="rounded-sm"
                    onchange={(e) => onupdateClearClipboardOnBackground?.((e.target as HTMLInputElement).checked)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.android_clear_clipboard_on_background")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.android_clear_clipboard_on_background_desc")}</span
                    >
                </span>
            </label>

            <div class="space-y-2">
                <div class="setting-toggle__title">{t("settings.android_remote_backend_heading")}</div>
                <p class="text-xs opacity-80">{t("settings.android_remote_backend_desc")}</p>
                <input
                    value={remoteBackendUrl}
                    type="url"
                    inputmode="url"
                    autocomplete="off"
                    spellcheck="false"
                    class="w-full rounded-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                    placeholder={t("settings.android_remote_backend_placeholder")}
                    oninput={(e) => onupdateRemoteBackendUrl?.((e.target as HTMLInputElement).value)}
                />
                {#if remoteBackendActive}
                    <p class="text-xs text-emerald-700 dark:text-emerald-300">
                        {t("settings.android_remote_backend_active", { url: effectiveBackendUrl })}
                    </p>
                {/if}
                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="btn-maintenance border-blue-200 dark:border-blue-900/30 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20"
                        onclick={onapplyRemoteBackend}
                    >
                        {t("settings.android_remote_backend_apply")}
                    </button>
                    <button
                        type="button"
                        class="btn-maintenance border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-900/40 hover:bg-gray-100 dark:hover:bg-gray-800"
                        disabled={!remoteBackendActive && !(remoteBackendUrl || "").trim()}
                        onclick={onclearRemoteBackend}
                    >
                        {t("settings.android_remote_backend_use_local")}
                    </button>
                </div>
            </div>

            <button
                type="button"
                class="btn-maintenance border-blue-200 dark:border-blue-900/30 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20"
                onclick={onshareApk}
            >
                <div class="flex flex-col items-start text-left">
                    <div class="font-bold flex items-center gap-2">
                        <MaterialDesignIcon iconName="share-variant" class="size-4" />
                        {t("settings.share_apk")}
                    </div>
                    <div class="text-xs opacity-80">
                        {t("settings.share_apk_short_hint")}
                    </div>
                </div>
            </button>
        </div>
    </section>
{/if}
