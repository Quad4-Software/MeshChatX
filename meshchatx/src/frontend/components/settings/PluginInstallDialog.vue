<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="open && preview" class="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
        <button
            type="button"
            class="absolute inset-0 bg-black/50"
            :aria-label="$t('plugins.install_dialog.close')"
            :disabled="confirming"
            @click="onCancel"
        />
        <div
            class="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl p-5 space-y-4"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="plugin-install-title"
        >
            <h2 id="plugin-install-title" class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {{
                    preview.requires_network_fetch
                        ? $t("plugins.install_dialog.network_title")
                        : $t("plugins.install_dialog.title")
                }}
            </h2>
            <p class="text-sm text-gray-600 dark:text-gray-400">
                {{ $t("plugins.install_dialog.message", { name: preview.name, id: preview.id }) }}
            </p>

            <div class="space-y-1">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ preview.name }}
                    <span class="text-xs font-normal text-gray-500">v{{ preview.version }}</span>
                </p>
                <p v-if="preview.description" class="text-sm text-gray-600 dark:text-gray-400">
                    {{ preview.description }}
                </p>
            </div>

            <section class="space-y-2">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {{ $t("plugins.install_dialog.signature") }}
                </h3>
                <p class="text-sm" :class="signatureClass">
                    {{ signatureLabel }}
                </p>
                <p
                    v-if="preview.signature?.signer"
                    class="text-xs font-mono break-all text-gray-600 dark:text-gray-400"
                >
                    {{ preview.signature.signer }}
                    <span v-if="preview.signature.signer_name"> ({{ preview.signature.signer_name }})</span>
                </p>
                <p v-if="preview.signature?.error" class="text-xs text-red-600 dark:text-red-400">
                    {{ preview.signature.error }}
                </p>
                <label
                    v-if="canTrustPublisher"
                    class="inline-flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300"
                >
                    <input v-model="trustPublisher" type="checkbox" class="rounded border-gray-300" />
                    {{ $t("plugins.install_dialog.trust_publisher") }}
                </label>
            </section>

            <section v-if="(preview.security_findings || []).length" class="space-y-2">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {{ $t("plugins.install_dialog.security_findings") }}
                </h3>
                <ul class="space-y-1 rounded-md border border-gray-200 dark:border-zinc-700 p-3">
                    <li
                        v-for="finding in preview.security_findings"
                        :key="finding.id"
                        class="text-xs text-gray-700 dark:text-gray-300"
                    >
                        <span class="font-semibold uppercase">{{ finding.severity }}</span>
                        {{ finding.message }}
                    </li>
                </ul>
            </section>

            <section v-if="(preview.permissions || []).length" class="space-y-2">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {{ $t("plugins.install_dialog.permissions") }}
                </h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    {{ $t("plugins.install_dialog.permissions_hint") }}
                </p>
                <ul class="space-y-2">
                    <li
                        v-for="perm in preview.permissions"
                        :key="perm"
                        class="flex items-center justify-between gap-3 rounded-md border border-gray-200 dark:border-zinc-700 px-3 py-2"
                    >
                        <span class="text-sm text-gray-800 dark:text-gray-200">{{ labelFor(perm) }}</span>
                        <label class="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                            <input v-model="grantedMap[perm]" type="checkbox" class="rounded border-gray-300" />
                            {{ $t("plugins.install_dialog.grant") }}
                        </label>
                    </li>
                </ul>
            </section>

            <section v-if="preview.requires_network_fetch" class="space-y-2">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {{ $t("plugins.install_dialog.network_endpoints") }}
                </h3>
                <p v-if="!networkFetchGranted" class="text-xs text-amber-700 dark:text-amber-300">
                    {{ $t("plugins.install_dialog.network_endpoints_blocked") }}
                </p>
                <ul
                    v-if="(preview.network_endpoints || []).length"
                    class="space-y-1 rounded-md border border-gray-200 dark:border-zinc-700 p-3"
                >
                    <li
                        v-for="endpoint in preview.network_endpoints"
                        :key="endpoint"
                        class="text-xs font-mono break-all text-gray-700 dark:text-gray-300"
                    >
                        {{ endpoint }}
                    </li>
                </ul>
                <p v-else class="text-xs text-gray-500 dark:text-gray-400">
                    {{ $t("plugins.install_dialog.network_endpoints_unknown") }}
                </p>
            </section>

            <div class="flex justify-end gap-2 pt-2">
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-md border border-gray-300 dark:border-zinc-600 text-sm"
                    :disabled="confirming"
                    @click="onCancel"
                >
                    {{ $t("plugins.install_dialog.cancel") }}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm disabled:opacity-50"
                    :disabled="confirming || signatureBlocksInstall"
                    @click="confirm"
                >
                    {{ confirming ? $t("plugins.settings.installing") : $t("plugins.install_dialog.confirm") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import { permissionLabel } from "../../js/plugins/pluginPermissions.js";

export default {
    name: "PluginInstallDialog",
    props: {
        open: { type: Boolean, default: false },
        preview: { type: Object, default: null },
        confirming: { type: Boolean, default: false },
    },
    emits: ["confirm", "cancel"],
    data() {
        return {
            grantedMap: {},
            trustPublisher: false,
        };
    },
    computed: {
        networkFetchGranted() {
            return this.grantedMap["network:fetch"] === true;
        },
        signatureBlocksInstall() {
            const signature = this.preview?.signature;
            return Boolean(signature?.present && !signature?.valid);
        },
        canTrustPublisher() {
            const signature = this.preview?.signature;
            return Boolean(signature?.valid && signature?.signer && !signature?.trusted);
        },
        signatureLabel() {
            const signature = this.preview?.signature || {};
            if (signature.present && !signature.valid) {
                return this.$t("plugins.install_dialog.signature_invalid");
            }
            if (signature.valid && signature.trusted) {
                return this.$t("plugins.install_dialog.signature_trusted");
            }
            if (signature.valid) {
                return this.$t("plugins.install_dialog.signature_signed");
            }
            return this.$t("plugins.install_dialog.signature_unsigned");
        },
        signatureClass() {
            const signature = this.preview?.signature || {};
            if (signature.present && !signature.valid) {
                return "text-red-700 dark:text-red-300";
            }
            if (signature.valid && signature.trusted) {
                return "text-green-700 dark:text-green-300";
            }
            if (signature.valid) {
                return "text-sky-700 dark:text-sky-300";
            }
            return "text-gray-600 dark:text-gray-400";
        },
    },
    watch: {
        open: {
            immediate: true,
            handler(value) {
                if (value) {
                    this.resetGrants();
                }
            },
        },
        preview: {
            immediate: true,
            handler() {
                this.resetGrants();
            },
        },
    },
    methods: {
        resetGrants() {
            const next = {};
            for (const perm of this.preview?.permissions || []) {
                next[perm] = true;
            }
            this.grantedMap = next;
            this.trustPublisher = false;
        },
        labelFor(perm) {
            return permissionLabel(perm, (key) => this.$t(key));
        },
        selectedPermissions() {
            return (this.preview?.permissions || []).filter((perm) => this.grantedMap[perm]);
        },
        onCancel() {
            if (!this.confirming) {
                this.$emit("cancel");
            }
        },
        confirm() {
            if (this.signatureBlocksInstall) {
                return;
            }
            this.$emit("confirm", {
                grantedPermissions: this.selectedPermissions(),
                trustPublisher: this.trustPublisher,
                signer: this.preview?.signature?.signer || "",
                signerName: this.preview?.signature?.signer_name || "",
            });
        },
    },
};
</script>
