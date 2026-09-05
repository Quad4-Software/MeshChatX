<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RnxExecuteForm } from "../lib/types.js";

    interface Props {
        form: RnxExecuteForm;
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
    <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <div>
            <label class="glass-label" for="rnx-exec-name">{t("rnx.name")}</label>
            <input
                id="rnx-exec-name"
                bind:value={form.name}
                type="text"
                class="input-field"
                placeholder={t("rnx.name_placeholder")}
            />
        </div>
        <div>
            <label class="glass-label" for="rnx-exec-destination">{t("rnx.destination_hash")}</label>
            <input
                id="rnx-exec-destination"
                bind:value={form.destination}
                type="text"
                class="input-field font-mono text-xs"
                placeholder={t("rnx.destination_placeholder")}
            />
        </div>
    </div>
    {#if !form.interactive}
        <div>
            <label class="glass-label" for="rnx-exec-command">{t("rnx.remote_command")}</label>
            <input
                id="rnx-exec-command"
                bind:value={form.command}
                type="text"
                class="input-field font-mono text-xs"
                placeholder={t("rnx.command_placeholder")}
            />
        </div>
    {/if}
    <div>
        <label class="glass-label" for="rnx-exec-config">{t("rnx.config_dir")}</label>
        <input
            id="rnx-exec-config"
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
            <input bind:checked={form.mirror} type="checkbox" class="rounded-sm" />
            {t("rnx.mirror_exit_code")}
        </label>
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.no_id} type="checkbox" class="rounded-sm" />
            {t("rnx.no_id")}
        </label>
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.detailed} type="checkbox" class="rounded-sm" />
            {t("rnx.detailed")}
        </label>
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.interactive} type="checkbox" class="rounded-sm" />
            {t("rnx.interactive")}
        </label>
    </div>
    <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <div>
            <label class="glass-label" for="rnx-exec-timeout">{t("rnx.timeout")}</label>
            <input
                id="rnx-exec-timeout"
                bind:value={form.timeout}
                type="number"
                min="1"
                step="1"
                class="input-field font-mono text-xs"
            />
        </div>
        <div>
            <label class="glass-label" for="rnx-exec-result-timeout">{t("rnx.result_timeout")}</label>
            <input
                id="rnx-exec-result-timeout"
                bind:value={form.result_timeout}
                type="number"
                min="1"
                step="1"
                class="input-field font-mono text-xs"
            />
        </div>
        <div>
            <label class="glass-label" for="rnx-exec-stdout-limit">{t("rnx.stdout_limit")}</label>
            <input
                id="rnx-exec-stdout-limit"
                bind:value={form.stdout_limit}
                type="number"
                min="1"
                step="1"
                class="input-field font-mono text-xs"
            />
        </div>
        <div>
            <label class="glass-label" for="rnx-exec-stderr-limit">{t("rnx.stderr_limit")}</label>
            <input
                id="rnx-exec-stderr-limit"
                bind:value={form.stderr_limit}
                type="number"
                min="1"
                step="1"
                class="input-field font-mono text-xs"
            />
        </div>
    </div>
    <button type="submit" class="primary-chip px-4 py-2 text-sm w-full sm:w-auto">
        <MaterialDesignIcon iconName="plus" class="size-4" />
        {t("rnx.create_and_start")}
    </button>
</form>
