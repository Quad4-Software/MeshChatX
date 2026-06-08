<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-linear-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6">
            <div class="space-y-0 w-full max-w-5xl mx-auto min-w-0">
                <div class="identities-section identities-section--hero">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div class="space-y-2 flex-1 min-w-0">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                {{ $t("identities.eyebrow") }}
                            </div>
                            <h1 class="text-2xl sm:text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                                {{ $t("identities.title") }}
                            </h1>
                            <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed max-w-xl">
                                {{ $t("identities.manage") }}
                            </p>
                        </div>
                        <div class="flex flex-wrap items-center gap-2 shrink-0">
                            <button type="button" class="primary-chip" @click="showCreateModal = true">
                                <MaterialDesignIcon icon-name="plus" class="size-4" />
                                <span class="hidden sm:inline">{{ $t("identities.new_identity") }}</span>
                            </button>
                            <button type="button" class="secondary-chip" @click="showImportModal = true">
                                <MaterialDesignIcon icon-name="file-import" class="size-4" />
                                <span class="hidden sm:inline">{{ $t("identities.import") }}</span>
                            </button>
                            <button
                                type="button"
                                class="secondary-chip"
                                :disabled="identities.length === 0"
                                @click="downloadAllIdentities"
                            >
                                <MaterialDesignIcon icon-name="file-export" class="size-4" />
                                <span class="hidden sm:inline">{{ $t("identities.export_all") }}</span>
                            </button>
                        </div>
                    </div>
                </div>

                <input
                    ref="identityFileInput"
                    type="file"
                    accept=".identity,.bin,.key"
                    class="hidden"
                    @change="onIdentityRestoreFileChange"
                />

                <template v-if="isLoading && identities.length === 0">
                    <div class="identities-section">
                        <div
                            v-for="i in 4"
                            :key="'skel-' + i"
                            class="flex items-center gap-3 border-b border-gray-100 px-1 py-3 dark:border-zinc-800"
                        >
                            <div
                                class="size-10 sm:size-12 rounded-full bg-gray-200 dark:bg-zinc-700 animate-pulse shrink-0"
                            />
                            <div class="flex-1 min-w-0 space-y-2">
                                <div class="h-4 w-32 bg-gray-200 dark:bg-zinc-700 rounded-sm animate-pulse" />
                                <div class="h-3 w-48 bg-gray-100 dark:bg-zinc-800 rounded-sm animate-pulse" />
                            </div>
                        </div>
                    </div>
                </template>

                <template v-else-if="currentIdentity">
                    <div class="identities-section space-y-4">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("identities.active_identity") }}
                        </div>
                        <div class="flex items-center gap-3 sm:gap-4">
                            <div class="size-10 sm:size-12 shrink-0">
                                <LxmfUserIcon
                                    :icon-name="currentIdentity.icon_name"
                                    :icon-foreground-colour="currentIdentity.icon_foreground_colour"
                                    :icon-background-colour="currentIdentity.icon_background_colour"
                                    icon-class="w-full h-full"
                                />
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="flex flex-wrap items-center gap-2">
                                    <h2 class="text-lg font-bold text-gray-900 dark:text-white truncate">
                                        {{ currentIdentity.display_name }}
                                    </h2>
                                    <span
                                        class="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-[10px] font-semibold uppercase tracking-wide"
                                    >
                                        {{ $t("identities.current") }}
                                    </span>
                                </div>
                                <p
                                    v-if="currentIdentity.message_count != null"
                                    class="text-sm text-gray-500 dark:text-zinc-400 mt-0.5"
                                >
                                    {{ $t("identities.message_count", { count: currentIdentity.message_count }) }}
                                </p>
                            </div>
                        </div>

                        <div class="grid gap-3 sm:grid-cols-2">
                            <div class="address-card">
                                <div class="address-card__label">{{ $t("app.identity_hash") }}</div>
                                <div class="address-card__value monospace-field">{{ currentIdentity.hash }}</div>
                                <button
                                    type="button"
                                    class="address-card__action"
                                    @click="copyAddress(currentIdentity.hash)"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                    {{ $t("app.copy") }}
                                </button>
                            </div>
                            <div v-if="currentIdentity.lxmf_address" class="address-card">
                                <div class="address-card__label">{{ $t("app.lxmf_address") }}</div>
                                <div class="address-card__value monospace-field">
                                    {{ currentIdentity.lxmf_address }}
                                </div>
                                <button
                                    type="button"
                                    class="address-card__action"
                                    @click="copyAddress(currentIdentity.lxmf_address)"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                    {{ $t("app.copy") }}
                                </button>
                            </div>
                            <div v-if="currentIdentity.lxst_address" class="address-card">
                                <div class="address-card__label">{{ $t("identities.lxst_address") }}</div>
                                <div class="address-card__value monospace-field">
                                    {{ currentIdentity.lxst_address }}
                                </div>
                                <button
                                    type="button"
                                    class="address-card__action"
                                    @click="copyAddress(currentIdentity.lxst_address)"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                    {{ $t("app.copy") }}
                                </button>
                            </div>
                        </div>

                        <div class="flex flex-wrap gap-2">
                            <button type="button" class="secondary-chip" @click="downloadIdentityFile">
                                <MaterialDesignIcon icon-name="file-export" class="size-4" />
                                {{ $t("identities.export_key_file") }}
                            </button>
                            <button type="button" class="secondary-chip" @click="copyIdentityBase32">
                                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                {{ $t("identities.copy_base32") }}
                            </button>
                        </div>
                    </div>
                </template>

                <div v-if="!isLoading && otherIdentities.length > 0" class="identities-section">
                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
                        {{ $t("identities.other_identities") }}
                    </div>
                    <div class="divide-y divide-gray-100 dark:divide-zinc-800">
                        <div
                            v-for="identity in otherIdentities"
                            :key="identity.hash"
                            v-memo="[
                                identity.hash,
                                identity.display_name,
                                identity.lxmf_address,
                                identity.lxst_address,
                                identity.message_count,
                                identity.icon_name,
                                identity.icon_background_colour,
                                identity.icon_foreground_colour,
                                expandedAddressHashes[identity.hash],
                            ]"
                            class="identity-row group py-3 px-1 transition-colors hover:bg-gray-50/80 dark:hover:bg-zinc-900/70"
                        >
                            <div class="flex items-center gap-3">
                                <div class="size-10 sm:size-12 shrink-0">
                                    <LxmfUserIcon
                                        :icon-name="identity.icon_name"
                                        :icon-foreground-colour="identity.icon_foreground_colour"
                                        :icon-background-colour="identity.icon_background_colour"
                                        icon-class="w-full h-full"
                                    />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div class="font-semibold text-gray-900 dark:text-zinc-100 truncate">
                                        {{ identity.display_name }}
                                    </div>
                                    <p
                                        v-if="identity.message_count != null"
                                        class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5"
                                    >
                                        {{ $t("identities.message_count", { count: identity.message_count }) }}
                                    </p>
                                </div>
                                <div class="flex items-center gap-2 shrink-0">
                                    <button
                                        type="button"
                                        class="secondary-chip"
                                        :title="$t('identities.switch')"
                                        @click="switchIdentity(identity)"
                                    >
                                        <MaterialDesignIcon icon-name="swap-horizontal" class="size-4" />
                                        <span class="hidden sm:inline">{{ $t("identities.switch_label") }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-xl text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition"
                                        :title="$t('identities.delete')"
                                        @click="deleteIdentity(identity)"
                                    >
                                        <MaterialDesignIcon icon-name="delete-outline" class="size-5" />
                                    </button>
                                </div>
                            </div>
                            <div
                                v-if="identity.lxmf_address || identity.lxst_address || identity.hash"
                                class="mt-2 pl-11 sm:pl-14"
                            >
                                <button
                                    type="button"
                                    class="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                                    @click="toggleAddresses(identity.hash)"
                                >
                                    {{
                                        expandedAddressHashes[identity.hash]
                                            ? $t("identities.hide_addresses")
                                            : $t("identities.show_addresses")
                                    }}
                                </button>
                                <div v-if="expandedAddressHashes[identity.hash]" class="grid gap-2 mt-2 sm:grid-cols-2">
                                    <div class="address-card">
                                        <div class="address-card__label">{{ $t("app.identity_hash") }}</div>
                                        <div class="address-card__value monospace-field text-xs">{{ identity.hash }}</div>
                                        <button
                                            type="button"
                                            class="address-card__action"
                                            @click="copyAddress(identity.hash)"
                                        >
                                            <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                            {{ $t("app.copy") }}
                                        </button>
                                    </div>
                                    <div v-if="identity.lxmf_address" class="address-card">
                                        <div class="address-card__label">{{ $t("app.lxmf_address") }}</div>
                                        <div class="address-card__value monospace-field text-xs">
                                            {{ identity.lxmf_address }}
                                        </div>
                                        <button
                                            type="button"
                                            class="address-card__action"
                                            @click="copyAddress(identity.lxmf_address)"
                                        >
                                            <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                            {{ $t("app.copy") }}
                                        </button>
                                    </div>
                                    <div v-if="identity.lxst_address" class="address-card">
                                        <div class="address-card__label">{{ $t("identities.lxst_address") }}</div>
                                        <div class="address-card__value monospace-field text-xs">
                                            {{ identity.lxst_address }}
                                        </div>
                                        <button
                                            type="button"
                                            class="address-card__action"
                                            @click="copyAddress(identity.lxst_address)"
                                        >
                                            <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                            {{ $t("app.copy") }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div
                    v-if="!isLoading && identities.length === 0"
                    class="identities-section py-12 text-center text-gray-500 dark:text-zinc-400"
                >
                    <MaterialDesignIcon icon-name="account-group" class="size-12 mx-auto mb-3 opacity-40" />
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("identities.no_identities") }}
                    </h3>
                    <p class="mt-1 text-sm">{{ $t("identities.create_first") }}</p>
                    <button type="button" class="primary-chip mt-4" @click="showCreateModal = true">
                        <MaterialDesignIcon icon-name="plus" class="size-4" />
                        {{ $t("identities.new_identity") }}
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="showCreateModal"
            class="fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            @click.self="showCreateModal = false"
        >
            <div class="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h2 class="text-lg font-bold text-gray-900 dark:text-white">
                        {{ $t("identities.new_identity") }}
                    </h2>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="showCreateModal = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ $t("identities.generate_fresh") }}</p>
                    <div>
                        <label class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1">
                            {{ $t("identities.display_name") }}
                        </label>
                        <input
                            v-model="newIdentityName"
                            type="text"
                            :placeholder="$t('identities.display_name_hint')"
                            class="input-field"
                            autofocus
                            @keyup.enter="createIdentity"
                        />
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-gray-100 dark:border-zinc-800 flex justify-end gap-2">
                    <button type="button" class="secondary-chip" @click="showCreateModal = false">
                        {{ $t("common.cancel") }}
                    </button>
                    <button type="button" class="primary-chip" :disabled="isCreating" @click="createIdentity">
                        <MaterialDesignIcon
                            :icon-name="isCreating ? 'loading' : 'check'"
                            class="size-4"
                            :class="{ 'animate-spin': isCreating }"
                        />
                        {{ $t("common.add") }}
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="showImportModal"
            class="fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            @click.self="showImportModal = false"
        >
            <div class="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h2 class="text-lg font-bold text-gray-900 dark:text-white">
                        {{ $t("identities.import") }}
                    </h2>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="showImportModal = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ $t("identities.import_hint") }}</p>
                    <button
                        type="button"
                        class="w-full secondary-chip justify-center"
                        @click="
                            $refs.identityFileInput?.click();
                            showImportModal = false;
                        "
                    >
                        <MaterialDesignIcon icon-name="upload" class="size-4" />
                        {{ $t("identities.upload_key_file") }}
                    </button>
                    <div class="border-t border-gray-200 dark:border-zinc-700 pt-4 space-y-3">
                        <label class="block text-xs uppercase tracking-wider font-semibold text-gray-500">
                            {{ $t("identities.paste_base32") }}
                        </label>
                        <textarea
                            v-model="identityRestoreBase32"
                            rows="3"
                            class="input-field font-mono text-xs w-full"
                            :placeholder="$t('identities.paste_base32_placeholder')"
                        />
                        <div v-if="identityRestoreError" class="text-sm text-red-600 dark:text-red-400">
                            {{ identityRestoreError }}
                        </div>
                        <div v-if="identityRestoreMessage" class="text-sm text-green-600 dark:text-green-400">
                            {{ identityRestoreMessage }}
                        </div>
                        <button
                            type="button"
                            class="primary-chip"
                            :disabled="identityRestoreInProgress || !identityRestoreBase32.trim()"
                            @click="restoreIdentityBase32"
                        >
                            <MaterialDesignIcon
                                v-if="identityRestoreInProgress"
                                icon-name="loading"
                                class="size-4 animate-spin"
                            />
                            {{
                                identityRestoreInProgress
                                    ? $t("identities.restoring")
                                    : $t("identities.confirm_restore")
                            }}
                        </button>
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-gray-100 dark:border-zinc-800">
                    <button type="button" class="w-full secondary-chip justify-center" @click="showImportModal = false">
                        {{ $t("common.cancel") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import GlobalEmitter from "../../js/GlobalEmitter";

export default {
    name: "IdentitiesPage",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    data() {
        return {
            identities: [],
            isLoading: false,
            showCreateModal: false,
            showImportModal: false,
            newIdentityName: "",
            isCreating: false,
            identityRestoreBase32: "",
            identityRestoreInProgress: false,
            identityRestoreMessage: "",
            identityRestoreError: "",
            identityRestoreFile: null,
            expandedAddressHashes: {},
        };
    },
    computed: {
        currentIdentity() {
            return this.identities.find((i) => i.is_current) || null;
        },
        otherIdentities() {
            return this.identities.filter((i) => !i.is_current);
        },
    },
    mounted() {
        this.getIdentities();
        GlobalEmitter.on("identity-switched", this.onIdentitySwitched);
    },
    beforeUnmount() {
        GlobalEmitter.off("identity-switched", this.onIdentitySwitched);
    },
    methods: {
        onIdentitySwitched() {
            this.getIdentities();
            this.isCreating = false;
        },
        toggleAddresses(hash) {
            this.expandedAddressHashes = {
                ...this.expandedAddressHashes,
                [hash]: !this.expandedAddressHashes[hash],
            };
        },
        async copyAddress(value) {
            if (!value) return;
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(this.$t("common.copied"));
            } catch {
                ToastUtils.error(this.$t("identities.identity_copy_failed"));
            }
        },
        async getIdentities() {
            this.isLoading = true;
            try {
                const response = await window.api.get("/api/v1/identities");
                this.identities = response.data?.identities ?? [];
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("identities.failed_load"));
            } finally {
                this.isLoading = false;
            }
        },
        async downloadIdentityFile() {
            try {
                const response = await window.api.get("/api/v1/identity/backup/download", {
                    responseType: "blob",
                });
                const blob = new Blob([response.data], { type: "application/octet-stream" });
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", "identity");
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                ToastUtils.success(this.$t("identities.identity_exported"));
            } catch {
                ToastUtils.error(this.$t("identities.identity_export_failed"));
            }
        },
        async copyIdentityBase32() {
            try {
                const response = await window.api.get("/api/v1/identity/backup/base32");
                const base32 = response.data?.identity_base32 ?? "";
                if (!base32) {
                    ToastUtils.error(this.$t("identities.no_identity_available"));
                    return;
                }
                await navigator.clipboard.writeText(base32);
                ToastUtils.success(this.$t("identities.identity_copied"));
            } catch {
                ToastUtils.error(this.$t("identities.identity_copy_failed"));
            }
        },
        async downloadAllIdentities() {
            try {
                const response = await window.api.get("/api/v1/identities/export-all", {
                    responseType: "blob",
                });
                const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/zip" }));
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", "identities_export.zip");
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                ToastUtils.success(this.$t("identities.export_all_success"));
            } catch (e) {
                const msg = e?.response?.data?.message || this.$t("identities.export_all_failed");
                ToastUtils.error(msg);
            }
        },
        onIdentityRestoreFileChange(event) {
            const files = event.target.files;
            if (files?.[0]) {
                this.identityRestoreFile = files[0];
                this.identityRestoreError = "";
                this.identityRestoreMessage = "";
                this.restoreIdentityFile();
            }
            event.target.value = "";
        },
        async restoreIdentityFile() {
            if (this.identityRestoreInProgress || !this.identityRestoreFile) return;
            this.identityRestoreInProgress = true;
            this.identityRestoreMessage = "";
            this.identityRestoreError = "";
            try {
                const formData = new FormData();
                formData.append("file", this.identityRestoreFile);
                const response = await window.api.post("/api/v1/identity/restore", formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                this.identityRestoreMessage = response.data?.message ?? this.$t("identities.identity_restored");
                this.identityRestoreFile = null;
                this.showImportModal = false;
            } catch {
                this.identityRestoreError = this.$t("identities.identity_restore_failed");
            } finally {
                this.identityRestoreInProgress = false;
            }
        },
        async restoreIdentityBase32() {
            if (this.identityRestoreInProgress || !this.identityRestoreBase32?.trim()) return;
            this.identityRestoreInProgress = true;
            this.identityRestoreMessage = "";
            this.identityRestoreError = "";
            try {
                const response = await window.api.post("/api/v1/identity/restore", {
                    base32: this.identityRestoreBase32.trim(),
                });
                this.identityRestoreMessage = response.data?.message ?? this.$t("identities.identity_restored");
                this.identityRestoreBase32 = "";
                this.showImportModal = false;
            } catch {
                this.identityRestoreError = this.$t("identities.identity_restore_failed");
            } finally {
                this.identityRestoreInProgress = false;
            }
        },
        async createIdentity() {
            if (!this.newIdentityName) {
                ToastUtils.warning(this.$t("identities.enter_display_name_warning"));
                return;
            }

            this.isCreating = true;
            try {
                await window.api.post("/api/v1/identities/create", {
                    display_name: this.newIdentityName,
                });
                ToastUtils.success(this.$t("identities.created"));
                this.showCreateModal = false;
                this.newIdentityName = "";
                await this.getIdentities();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("identities.failed_create"));
            } finally {
                this.isCreating = false;
            }
        },
        async switchIdentity(identity) {
            if (identity.is_current) return;

            if (!(await DialogUtils.confirm(this.$t("identities.switch_confirm", { name: identity.display_name })))) {
                return;
            }

            try {
                this.isCreating = true;
                GlobalEmitter.emit("identity-switching-start");

                const response = await window.api.post("/api/v1/identities/switch", {
                    identity_hash: identity.hash,
                });

                if (response.data.hotswapped) {
                    GlobalEmitter.emit("identity-switched-apply", {
                        identity_hash: response.data.identity_hash ?? identity.hash,
                        display_name: response.data.display_name ?? identity.display_name ?? "",
                    });
                } else {
                    ToastUtils.info(this.$t("identities.switch_scheduled"));
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
            } catch (e) {
                console.error(e);
                const errorMsg =
                    e.response?.data?.message || this.$t("identities.failed_switch") || "Failed to switch identity";
                ToastUtils.error(errorMsg);
                this.isCreating = false;
                GlobalEmitter.emit("identity-switched");
            }
        },
        async deleteIdentity(identity) {
            if (!(await DialogUtils.confirm(this.$t("identities.delete_confirm", { name: identity.display_name })))) {
                return;
            }

            try {
                await window.api.delete(`/api/v1/identities/${identity.hash}`);
                ToastUtils.success(this.$t("identities.deleted"));
                await this.getIdentities();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("identities.failed_delete"));
            }
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.identities-section {
    @apply w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6;
}
.identities-section--hero {
    @apply border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6;
}
</style>
