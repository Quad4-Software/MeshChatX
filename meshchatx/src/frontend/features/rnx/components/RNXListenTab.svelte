<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RnxListenForm } from "../lib/types.js";

    interface Props {
        form: RnxListenForm;
        onsubmit: () => void;
    }

    let { form = $bindable(), onsubmit }: Props = $props();

    function handleSubmit(event: Event): void {
        event.preventDefault();
        onsubmit();
    }
</script>

<form
    class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-3 sm:px-4 md:px-5 lg:px-8 py-3 sm:py-4 space-y-3 sm:space-y-4"
    onsubmit={handleSubmit}
>
    <p class="text-xs text-sem-fg-muted leading-relaxed">
        {t("rnx.usage_hint")}
    </p>
    <div>
        <label class="glass-label" for="rnx-listen-name">{t("rnx.name")}</label>
        <input
            id="rnx-listen-name"
            bind:value={form.name}
            type="text"
            class="input-field"
            placeholder={t("rnx.name_placeholder")}
        />
    </div>
    <div>
        <label class="glass-label" for="rnx-listen-hashes">{t("rnx.allowed_hashes")}</label>
        <textarea
            id="rnx-listen-hashes"
            bind:value={form.allowed_hashes_text}
            rows="4"
            class="input-field font-mono text-xs"
            placeholder={t("rnx.allowed_hashes_placeholder")}></textarea>
    </div>
    <div>
        <label class="glass-label" for="rnx-listen-config">{t("rnx.config_dir")}</label>
        <input
            id="rnx-listen-config"
            bind:value={form.config_path}
            type="text"
            class="input-field font-mono text-xs"
            placeholder={t("rnx.config_dir_placeholder")}
        />
        <p class="mt-1 text-[10px] sm:text-xs text-sem-fg-muted">
            {t("rnx.config_dir_hint")}
        </p>
    </div>
    <div class="flex flex-wrap items-center gap-3 sm:gap-4">
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.no_auth} type="checkbox" class="rounded-sm" />
            {t("rnx.no_auth")}
        </label>
    </div>
    <button type="submit" class="primary-chip px-4 py-2 text-sm w-full sm:w-auto">
        <MaterialDesignIcon iconName="plus" class="size-4" />
        {t("rnx.create_and_start")}
    </button>
</form>
