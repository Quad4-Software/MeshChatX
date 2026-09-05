<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RnshConnectForm } from "../lib/types.js";

    interface Props {
        form: RnshConnectForm;
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
        {t("rnsh.usage_hint")}
    </p>
    <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <div>
            <label class="glass-label" for="rnsh-connect-name">{t("rnsh.name")}</label>
            <input
                id="rnsh-connect-name"
                bind:value={form.name}
                type="text"
                class="input-field"
                placeholder={t("rnsh.name_placeholder")}
            />
        </div>
        <div>
            <label class="glass-label" for="rnsh-connect-destination">{t("rnsh.destination_hash")}</label>
            <input
                id="rnsh-connect-destination"
                bind:value={form.destination}
                type="text"
                class="input-field font-mono text-xs"
                placeholder={t("rnsh.destination_placeholder")}
            />
        </div>
    </div>
    <div>
        <label class="glass-label" for="rnsh-connect-command">{t("rnsh.remote_command")}</label>
        <input
            id="rnsh-connect-command"
            bind:value={form.command}
            type="text"
            class="input-field font-mono text-xs"
            placeholder={t("rnsh.command_placeholder")}
        />
    </div>
    <div>
        <label class="glass-label" for="rnsh-connect-config">{t("rnsh.config_dir")}</label>
        <input
            id="rnsh-connect-config"
            bind:value={form.config_path}
            type="text"
            class="input-field font-mono text-xs"
            placeholder={t("rnsh.config_dir_placeholder")}
        />
        <p class="mt-1 text-[10px] sm:text-xs text-sem-fg-muted">
            {t("rnsh.config_dir_hint")}
        </p>
    </div>
    <div class="flex flex-wrap items-center gap-3 sm:gap-4">
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.mirror} type="checkbox" class="rounded-sm" />
            {t("rnsh.mirror_exit_code")}
        </label>
        <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
            <input bind:checked={form.no_id} type="checkbox" class="rounded-sm" />
            {t("rnsh.no_id")}
        </label>
    </div>
    <button type="submit" class="primary-chip px-4 py-2 text-sm w-full sm:w-auto">
        <MaterialDesignIcon iconName="plus" class="size-4" />
        {t("rnsh.create_and_start")}
    </button>
</form>
