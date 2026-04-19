<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-3">
            <div class="flex items-center gap-2">
                <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                    {{ provisionStepNumber }}. {{ $t("tools.rnode_flasher.step_provision") }}
                </h3>
                <MaterialDesignIcon icon-name="key-variant" class="size-4 text-zinc-400" />
            </div>
            <p class="text-xs text-gray-500 dark:text-zinc-500">
                {{ $t("tools.rnode_flasher.provision_description") }}
            </p>
            <button
                v-if="!isProvisioning"
                :disabled="!canProvision"
                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors disabled:opacity-50"
                @click="$emit('provision')"
            >
                {{ $t("tools.rnode_flasher.provision") }}
            </button>
            <div v-else class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                <v-progress-circular indeterminate size="18" width="2" />
                <span class="font-bold">{{ $t("tools.rnode_flasher.provisioning_wait") }}</span>
            </div>
        </div>

        <div class="space-y-3">
            <div class="flex items-center gap-2">
                <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                    {{ provisionStepNumber + 1 }}. {{ $t("tools.rnode_flasher.step_set_hash") }}
                </h3>
                <MaterialDesignIcon icon-name="shield-check" class="size-4 text-zinc-400" />
            </div>
            <p class="text-xs text-gray-500 dark:text-zinc-500">
                {{ $t("tools.rnode_flasher.set_hash_description") }}
            </p>
            <button
                v-if="!isSettingFirmwareHash"
                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors"
                @click="$emit('set-hash')"
            >
                {{ $t("tools.rnode_flasher.set_firmware_hash") }}
            </button>
            <div v-else class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                <v-progress-circular indeterminate size="18" width="2" />
                <span class="font-bold">{{ $t("tools.rnode_flasher.setting_hash_wait") }}</span>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeProvisionPanel",
    components: { MaterialDesignIcon },
    props: {
        provisionStepNumber: { type: Number, default: 3 },
        canProvision: { type: Boolean, default: false },
        isProvisioning: { type: Boolean, default: false },
        isSettingFirmwareHash: { type: Boolean, default: false },
    },
    emits: ["provision", "set-hash"],
};
</script>
