<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-6 w-full max-w-4xl mx-auto">
                <!-- header -->
                <div class="flex items-center justify-between flex-wrap gap-4">
                    <div>
                        <h1 class="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
                            {{ $t("identities.title") }}
                        </h1>
                        <p class="text-gray-600 dark:text-gray-400 mt-1">
                            {{ $t("identities.manage") }}
                        </p>
                    </div>
                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-2 rounded-2xl bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:shadow-indigo-500/25 transition-all active:scale-95"
                            @click="showCreateModal = true"
                        >
                            <MaterialDesignIcon icon-name="plus" class="w-5 h-5" />
                            {{ $t("identities.new_identity") }}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-2 rounded-2xl border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-all active:scale-95"
                            @click="showImportModal = true"
                        >
                            <MaterialDesignIcon icon-name="upload" class="w-5 h-5" />
                            {{ $t("identities.import") }}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-2 rounded-2xl border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-all active:scale-95"
                            :disabled="identities.length === 0"
                            @click="downloadAllIdentities"
                        >
                            <MaterialDesignIcon icon-name="file-export" class="w-5 h-5" />
                            {{ $t("identities.export_all") }}
                        </button>
                    </div>
                </div>
                <input
                    ref="identityFileInput"
                    type="file"
                    accept=".identity,.bin,.key"
                    class="hidden"
                    @change="onIdentityRestoreFileChange"
                />

                <!-- identities list -->
                <div class="grid gap-4">
                    <template v-if="isLoading && identities.length === 0">
                        <div
                            v-for="i in 4"
                            :key="'skel-' + i"
                            class="glass-card overflow-hidden p-5 flex items-center gap-4"
                        >
                            <div class="w-14 h-14 rounded-2xl bg-gray-200 dark:bg-zinc-700 animate-pulse shrink-0" />
                            <div class="flex-1 min-w-0 space-y-2">
                                <div class="h-5 w-32 bg-gray-200 dark:bg-zinc-700 rounded animate-pulse" />
                                <div class="h-3 w-48 bg-gray-100 dark:bg-zinc-800 rounded animate-pulse" />
                            </div>
                        </div>
                    </template>
                    <div
                        v-for="identity in identities"
                        v-else
                        :key="identity.hash"
                        v-memo="[
                            identity.hash,
                            identity.is_current,
                            identity.display_name,
                            identity.lxmf_address,
                            identity.lxst_address,
                            identity.message_count,
                            identity.icon_name,
                            identity.icon_background_colour,
                            identity.icon_foreground_colour,
                        ]"
                        class="glass-card overflow-hidden group transition-all duration-300"
                        :class="{
                            'ring-2 ring-blue-500/50 dark:ring-blue-400/40 bg-blue-50/30 dark:bg-blue-900/10':
                                identity.is_current,
                        }"
                    >
                        <div class="p-5 flex items-center gap-4">
                            <!-- icon -->
                            <div class="relative">
                                <div
                                    class="w-14 h-14 rounded-2xl flex items-center justify-center shadow-inner overflow-hidden transition-all duration-500"
                                    :class="
                                        identity.is_current && !identity.icon_background_colour
                                            ? 'bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/50 dark:to-indigo-900/50'
                                            : !identity.icon_background_colour
                                              ? 'bg-gradient-to-br from-gray-100 to-slate-100 dark:from-zinc-800 dark:to-zinc-800/50'
                                              : ''
                                    "
                                    :style="
                                        identity.icon_background_colour
                                            ? { 'background-color': identity.icon_background_colour }
                                            : {}
                                    "
                                >
                                    <MaterialDesignIcon
                                        v-if="identity.icon_name"
                                        :icon-name="identity.icon_name"
                                        class="w-8 h-8"
                                        :style="{ color: identity.icon_foreground_colour || 'inherit' }"
                                    />
                                    <MaterialDesignIcon
                                        v-else
                                        :icon-name="identity.is_current ? 'account-check' : 'account'"
                                        class="w-8 h-8"
                                        :class="
                                            identity.is_current
                                                ? 'text-blue-600 dark:text-blue-400'
                                                : 'text-gray-500 dark:text-gray-400'
                                        "
                                    />
                                </div>
                                <div
                                    v-if="identity.is_current"
                                    class="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-white dark:border-zinc-900 shadow-sm"
                                ></div>
                            </div>

                            <!-- info -->
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2">
                                    <h3 class="font-bold text-gray-900 dark:text-white truncate">
                                        {{ identity.display_name }}
                                    </h3>
                                    <span
                                        v-if="identity.is_current"
                                        class="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-[10px] font-bold uppercase tracking-wider"
                                    >
                                        {{ $t("identities.current") }}
                                    </span>
                                </div>
                                <div
                                    class="text-xs font-mono text-gray-500 dark:text-zinc-500 truncate mt-0.5 tracking-tight"
                                    :title="'RNS: ' + identity.hash"
                                >
                                    ID: {{ identity.hash }}
                                </div>
                                <div
                                    v-if="identity.lxmf_address"
                                    class="text-[10px] font-mono text-gray-400 dark:text-zinc-600 truncate mt-0.5 tracking-tighter"
                                    :title="'LXMF: ' + identity.lxmf_address"
                                >
                                    LXMF: {{ identity.lxmf_address }}
                                </div>
                                <div
                                    v-if="identity.lxst_address"
                                    class="text-[10px] font-mono text-gray-400 dark:text-zinc-600 truncate mt-0.5 tracking-tighter"
                                    :title="'LXST: ' + identity.lxst_address"
                                >
                                    LXST: {{ identity.lxst_address }}
                                </div>
                                <div
                                    v-if="identity.message_count != null"
                                    class="text-[10px] text-gray-400 dark:text-zinc-500 mt-0.5"
                                >
                                    {{ $t("identities.message_count", { count: identity.message_count }) }}
                                </div>
                            </div>

                            <!-- actions: key export on hover for current identity only -->
                            <div class="flex items-center gap-2">
                                <template v-if="identity.is_current">
                                    <div
                                        class="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                        <button
                                            type="button"
                                            class="p-2.5 rounded-xl bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-amber-500 hover:text-white dark:hover:bg-amber-600 transition-all active:scale-90"
                                            :title="$t('identities.export_key_file')"
                                            @click="downloadIdentityFile"
                                        >
                                            <MaterialDesignIcon icon-name="file-export" class="w-5 h-5" />
                                        </button>
                                        <button
                                            type="button"
                                            class="p-2.5 rounded-xl bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-amber-500 hover:text-white dark:hover:bg-amber-600 transition-all active:scale-90"
                                            :title="$t('identities.copy_base32')"
                                            @click="copyIdentityBase32"
                                        >
                                            <MaterialDesignIcon icon-name="content-copy" class="w-5 h-5" />
                                        </button>
                                    </div>
                                </template>
                                <button
                                    v-if="!identity.is_current"
                                    type="button"
                                    class="p-2.5 rounded-xl bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-blue-500 hover:text-white dark:hover:bg-blue-600 transition-all active:scale-90"
                                    :title="$t('identities.switch')"
                                    @click="switchIdentity(identity)"
                                >
                                    <MaterialDesignIcon icon-name="swap-horizontal" class="w-5 h-5" />
                                </button>
                                <button
                                    v-if="!identity.is_current"
                                    type="button"
                                    class="p-2.5 rounded-xl bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-red-500 hover:text-white dark:hover:bg-red-600 transition-all active:scale-90"
                                    :title="$t('identities.delete')"
                                    @click="deleteIdentity(identity)"
                                >
                                    <MaterialDesignIcon icon-name="delete-outline" class="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- empty state -->
                <div v-if="!isLoading && identities.length === 0" class="glass-card p-12 text-center">
                    <div
                        class="w-20 h-20 bg-gray-100 dark:bg-zinc-800 rounded-3xl flex items-center justify-center mx-auto mb-4"
                    >
                        <MaterialDesignIcon icon-name="account-group" class="w-10 h-10 text-gray-400" />
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                        {{ $t("identities.no_identities") }}
                    </h3>
                    <p class="text-gray-500 dark:text-gray-400 mt-2">{{ $t("identities.create_first") }}</p>
                </div>
            </div>
        </div>

        <!-- create modal -->
        <div
            v-if="showCreateModal"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
        >
            <div class="glass-card w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                <div class="p-6">
                    <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                        {{ $t("identities.new_identity") }}
                    </h2>
                    <p class="text-gray-500 dark:text-gray-400 mt-1">{{ $t("identities.generate_fresh") }}</p>

                    <div class="mt-6 space-y-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
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

                    <div class="mt-8 flex gap-3">
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-zinc-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition"
                            @click="showCreateModal = false"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-lg shadow-blue-500/25 hover:bg-blue-500 transition active:scale-95"
                            :disabled="isCreating"
                            @click="createIdentity"
                        >
                            <span v-if="isCreating" class="animate-spin mr-2">
                                <MaterialDesignIcon icon-name="loading" class="w-4 h-4" />
                            </span>
                            {{ $t("common.add") }}
                        </button>
                    </div>
                </div>

                <!-- import modal -->
                <div
                    v-if="showImportModal"
                    class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
                    @click.self="showImportModal = false"
                >
                    <div class="glass-card w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                        <div class="p-6">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("identities.import") }}
                            </h2>
                            <p class="text-gray-500 dark:text-gray-400 mt-1">{{ $t("identities.import_hint") }}</p>
                            <div class="mt-6 space-y-4">
                                <button
                                    type="button"
                                    class="w-full secondary-chip justify-center"
                                    @click="
                                        $refs.identityFileInput?.click();
                                        showImportModal = false;
                                    "
                                >
                                    <MaterialDesignIcon icon-name="upload" class="w-4 h-4" />
                                    {{ $t("identities.upload_key_file") }}
                                </button>
                                <div class="border-t border-gray-200 dark:border-zinc-700 pt-4">
                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                        {{ $t("identities.paste_base32") }}
                                    </label>
                                    <textarea
                                        v-model="identityRestoreBase32"
                                        rows="3"
                                        class="input-field font-mono text-xs w-full"
                                        :placeholder="$t('identities.paste_base32_placeholder')"
                                    />
                                    <div
                                        v-if="identityRestoreError"
                                        class="text-sm text-red-600 dark:text-red-400 mt-2"
                                    >
                                        {{ identityRestoreError }}
                                    </div>
                                    <div
                                        v-if="identityRestoreMessage"
                                        class="text-sm text-green-600 dark:text-green-400 mt-2"
                                    >
                                        {{ identityRestoreMessage }}
                                    </div>
                                    <button
                                        type="button"
                                        class="primary-chip mt-3"
                                        :disabled="identityRestoreInProgress || !identityRestoreBase32.trim()"
                                        @click="restoreIdentityBase32"
                                    >
                                        <MaterialDesignIcon
                                            v-if="identityRestoreInProgress"
                                            icon-name="loading"
                                            class="w-4 h-4 animate-spin"
                                        />
                                        {{
                                            identityRestoreInProgress
                                                ? $t("identities.restoring")
                                                : $t("identities.confirm_restore")
                                        }}
                                    </button>
                                </div>
                            </div>
                            <div class="mt-6">
                                <button
                                    type="button"
                                    class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-zinc-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800"
                                    @click="showImportModal = false"
                                >
                                    {{ $t("common.cancel") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import GlobalEmitter from "../../js/GlobalEmitter";

export default {
    name: "IdentitiesPage",
    components: {
        MaterialDesignIcon,
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
        };
    },
    computed: {
        currentIdentity() {
            return this.identities.find((i) => i.is_current) || null;
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
        async getIdentities() {
            this.isLoading = true;
            try {
                const response = await window.axios.get("/api/v1/identities");
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
                const response = await window.axios.get("/api/v1/identity/backup/download", {
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
                const response = await window.axios.get("/api/v1/identity/backup/base32");
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
                const response = await window.axios.get("/api/v1/identities/export-all", {
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
                const response = await window.axios.post("/api/v1/identity/restore", formData, {
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
                const response = await window.axios.post("/api/v1/identity/restore", {
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
                await window.axios.post("/api/v1/identities/create", {
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

                const response = await window.axios.post("/api/v1/identities/switch", {
                    identity_hash: identity.hash,
                });

                if (response.data.hotswapped) {
                    // Success is handled by GlobalEmitter "identity-switched" which we listen to
                    ToastUtils.success(this.$t("identities.switched") || "Identity switched successfully");
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

                // If it was a partial failure, we might need to reload anyway to be safe,
                // but let's try to stay on the page if hotswap just failed.
                GlobalEmitter.emit("identity-switched"); // To clear any global loading overlays
            }
        },
        async deleteIdentity(identity) {
            if (!(await DialogUtils.confirm(this.$t("identities.delete_confirm", { name: identity.display_name })))) {
                return;
            }

            try {
                await window.axios.delete(`/api/v1/identities/${identity.hash}`);
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
.glass-card {
    @apply bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-lg;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-3 text-gray-900 dark:text-gray-100 transition;
}
</style>
