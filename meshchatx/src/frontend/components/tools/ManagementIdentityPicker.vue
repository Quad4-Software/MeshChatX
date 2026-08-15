<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-2">
        <div class="flex flex-wrap items-end gap-2">
            <label class="block min-w-0 flex-1 space-y-1">
                <span class="text-xs font-medium text-gray-700 dark:text-zinc-300">{{
                    $t("remote_mgmt.management_identity")
                }}</span>
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
        <p v-if="selectedHash" class="font-mono text-[10px] text-gray-500 dark:text-zinc-500 break-all">
            {{ selectedHash }}
        </p>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "ManagementIdentityPicker",
    components: { MaterialDesignIcon },
    props: {
        modelValue: { type: String, default: "" },
        disabled: { type: Boolean, default: false },
        defaultName: { type: String, default: "mgmt" },
    },
    emits: ["update:modelValue", "update:identityHash", "loaded"],
    data() {
        return {
            identities: [],
            loading: false,
            creating: false,
        };
    },
    computed: {
        selectedHash() {
            const match = this.identities.find((item) => item.path === this.modelValue);
            return match?.hash || "";
        },
    },
    watch: {
        selectedHash(value) {
            this.$emit("update:identityHash", value || "");
        },
    },
    async mounted() {
        await this.loadIdentities();
    },
    methods: {
        shortHash(hash) {
            if (!hash || hash.length < 10) return hash || "";
            return `${hash.slice(0, 8)}…`;
        },
        onSelect(value) {
            this.$emit("update:modelValue", value || "");
        },
        async loadIdentities() {
            this.loading = true;
            try {
                const response = await window.api.get("/api/v1/reticulum/management-identities");
                this.identities = Array.isArray(response.data?.identities) ? response.data.identities : [];
                this.$emit("loaded", this.identities);
                if (this.modelValue && !this.identities.some((item) => item.path === this.modelValue)) {
                    this.$emit("update:modelValue", "");
                }
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("remote_mgmt.failed_load_identities"));
            } finally {
                this.loading = false;
            }
        },
        async createIdentity() {
            const suggested = this.defaultName || "mgmt";
            const name = await DialogUtils.prompt(this.$t("remote_mgmt.create_identity_prompt"), suggested);
            if (!name || !String(name).trim()) {
                return;
            }
            this.creating = true;
            try {
                const response = await window.api.post("/api/v1/reticulum/management-identities", {
                    name: String(name).trim(),
                });
                const identity = response.data?.identity;
                await this.loadIdentities();
                if (identity?.path) {
                    this.$emit("update:modelValue", identity.path);
                }
                ToastUtils.success(this.$t("remote_mgmt.identity_created"));
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("remote_mgmt.failed_create_identity"));
            } finally {
                this.creating = false;
            }
        },
    },
};
</script>
