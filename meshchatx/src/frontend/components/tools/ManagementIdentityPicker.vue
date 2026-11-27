<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-2">
        <div class="flex flex-wrap items-end gap-2">
            <label class="block min-w-0 flex-1 space-y-1">
                <span class="text-xs font-medium text-sem-fg-muted">{{ $t("remote_mgmt.management_identity") }}</span>
                <select
                    :value="modelValue"
                    class="input-field w-full font-mono text-xs"
                    :disabled="disabled || loading"
                    @change="onSelect($event.target.value)"
                >
                    <option value="">{{ $t("remote_mgmt.select_identity") }}</option>
                    <option v-for="item in identities" :key="item.path" :value="item.path">
                        {{ item.name }} ({{ shortHash(item.hash) }})
                    </option>
                </select>
            </label>
            <button
                type="button"
                class="secondary-chip px-3 py-2 text-xs"
                :disabled="disabled || loading"
                @click="loadIdentities"
            >
                <MaterialDesignIcon icon-name="refresh" class="size-4" />
            </button>
            <button
                type="button"
                class="secondary-chip px-3 py-2 text-xs"
                :disabled="disabled || creating"
                @click="createIdentity"
            >
                <MaterialDesignIcon icon-name="plus" class="size-4" />
                {{ $t("remote_mgmt.create_identity") }}
            </button>
        </div>
        <p v-if="selectedHash" class="font-mono text-[10px] text-sem-fg-muted break-all">
            {{ selectedHash }}
        </p>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import { apiPath } from "../../js/constants";
import { translateUi } from "../../js/localeLoader.js";

const props = withDefaults(
    defineProps<{
        modelValue?: string;
        disabled?: boolean;
        defaultName?: string;
    }>(),
    {
        modelValue: "",
        disabled: false,
        defaultName: "mgmt",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: string];
    "update:identityHash": [value: string];
    loaded: [identities: any[]];
}>();

const identities = ref<any[]>([]);
const loading = ref(false);
const creating = ref(false);

const selectedHash = computed(() => {
    const match = identities.value.find((item) => item.path === props.modelValue);
    return match?.hash || "";
});

watch(selectedHash, (value) => {
    emit("update:identityHash", value || "");
});

onMounted(async () => {
    await loadIdentities();
});

function shortHash(hash: string) {
    if (!hash || hash.length < 10) return hash || "";
    return `${hash.slice(0, 8)}…`;
}

function onSelect(value: string) {
    emit("update:modelValue", value || "");
}

async function loadIdentities() {
    loading.value = true;
    try {
        const response = await (window as any).api.get(apiPath("/reticulum/management-identities"));
        identities.value = Array.isArray(response.data?.identities) ? response.data.identities : [];
        emit("loaded", identities.value);
        if (props.modelValue && !identities.value.some((item) => item.path === props.modelValue)) {
            emit("update:modelValue", "");
        }
    } catch (error: any) {
        ToastUtils.error(error?.response?.data?.message || translateUi("remote_mgmt.failed_load_identities"));
    } finally {
        loading.value = false;
    }
}

async function createIdentity() {
    const suggested = props.defaultName || "mgmt";
    const name = await DialogUtils.prompt(translateUi("remote_mgmt.create_identity_prompt"), suggested);
    if (!name || !String(name).trim()) {
        return;
    }
    creating.value = true;
    try {
        const response = await (window as any).api.post(apiPath("/reticulum/management-identities"), {
            name: String(name).trim(),
        });
        const identity = response.data?.identity;
        await loadIdentities();
        if (identity?.path) {
            emit("update:modelValue", identity.path);
        }
        ToastUtils.success(translateUi("remote_mgmt.identity_created"));
    } catch (error: any) {
        ToastUtils.error(error?.response?.data?.message || translateUi("remote_mgmt.failed_create_identity"));
    } finally {
        creating.value = false;
    }
}

defineExpose({ loadIdentities });
</script>
