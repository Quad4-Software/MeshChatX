<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        provisionStepNumber?: number;
        canProvision?: boolean;
        isProvisioning?: boolean;
        isSettingFirmwareHash?: boolean;
        onprovision?: () => void;
        onsetHash?: () => void;
    }

    let {
        provisionStepNumber = 3,
        canProvision = false,
        isProvisioning = false,
        isSettingFirmwareHash = false,
        onprovision,
        onsetHash,
    }: Props = $props();
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="space-y-3">
        <div class="flex items-center gap-2">
            <h3 class="font-bold text-sem-fg">
                {provisionStepNumber}. {t("tools.rnode_flasher.step_provision")}
            </h3>
            <MaterialDesignIcon iconName="key-variant" class="size-4 text-zinc-400" />
        </div>
        <p class="text-xs text-sem-fg-muted">
            {t("tools.rnode_flasher.provision_description")}
        </p>
        {#if !isProvisioning}
            <button
                type="button"
                disabled={!canProvision}
                class="w-full sm:max-w-xs mx-auto inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                onclick={() => onprovision?.()}
            >
                {t("tools.rnode_flasher.provision")}
            </button>
        {:else}
            <div class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                <MaterialDesignIcon iconName="loading" class="size-[18px] animate-spin text-blue-600" />
                <span class="font-bold">{t("tools.rnode_flasher.provisioning_wait")}</span>
            </div>
        {/if}
    </div>

    <div class="space-y-3">
        <div class="flex items-center gap-2">
            <h3 class="font-bold text-sem-fg">
                {provisionStepNumber + 1}. {t("tools.rnode_flasher.step_set_hash")}
            </h3>
            <MaterialDesignIcon iconName="shield-check" class="size-4 text-zinc-400" />
        </div>
        <p class="text-xs text-sem-fg-muted">
            {t("tools.rnode_flasher.set_hash_description")}
        </p>
        {#if !isSettingFirmwareHash}
            <button
                type="button"
                class="w-full sm:max-w-xs mx-auto inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors cursor-pointer"
                onclick={() => onsetHash?.()}
            >
                {t("tools.rnode_flasher.set_firmware_hash")}
            </button>
        {:else}
            <div class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                <MaterialDesignIcon iconName="loading" class="size-[18px] animate-spin text-blue-600" />
                <span class="font-bold">{t("tools.rnode_flasher.setting_hash_wait")}</span>
            </div>
        {/if}
    </div>
</div>
