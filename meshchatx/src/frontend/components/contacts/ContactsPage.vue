<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <div class="flex-1 overflow-y-auto p-4 md:p-6">
            <div class="max-w-5xl mx-auto space-y-4">
                <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900 dark:text-zinc-100">{{ $t("contacts.title") }}</h1>
                        <p class="text-sm text-gray-600 dark:text-zinc-400">
                            {{ $t("contacts.description") }}
                        </p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button type="button" class="secondary-chip" @click="openMyIdentityDialog">
                            <MaterialDesignIcon icon-name="qrcode" class="size-4" />
                            {{ $t("contacts.share_my_identity") }}
                        </button>
                        <button type="button" class="primary-chip" @click="openAddDialog">
                            <MaterialDesignIcon icon-name="plus" class="size-4" />
                            {{ $t("contacts.add_contact") }}
                        </button>
                    </div>
                </div>

                <div class="glass-card space-y-3">
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                        <input
                            v-model="contactsSearch"
                            type="text"
                            :placeholder="$t('contacts.search_placeholder')"
                            class="input-field"
                            @input="onContactsSearchInput"
                        />
                    </div>
                </div>

                <div class="glass-card">
                    <template v-if="isLoading && contacts.length === 0">
                        <div
                            v-for="i in 8"
                            :key="'skeleton-' + i"
                            class="rounded-2xl border border-gray-100 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/50 px-4 py-3 flex items-center gap-3"
                        >
                            <div
                                class="size-10 sm:size-12 rounded-full bg-gray-200 dark:bg-zinc-700 animate-pulse shrink-0"
                            />
                            <div class="flex-1 min-w-0 space-y-2">
                                <div class="h-4 w-32 bg-gray-200 dark:bg-zinc-700 rounded animate-pulse" />
                                <div class="h-3 w-48 bg-gray-100 dark:bg-zinc-800 rounded animate-pulse" />
                            </div>
                        </div>
                    </template>
                    <div
                        v-else-if="!isLoading && contacts.length === 0"
                        class="py-10 text-center text-gray-500 dark:text-zinc-400"
                    >
                        {{ $t("contacts.no_contacts") }}
                    </div>
                    <div v-else class="space-y-2">
                        <div
                            v-for="contact in contacts"
                            :key="contact.id"
                            class="rounded-2xl border border-gray-100 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/50 px-4 py-3 flex items-center gap-3 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-default"
                            @contextmenu.prevent="openContextMenu($event, contact)"
                        >
                            <div class="flex-shrink-0">
                                <LxmfUserIcon
                                    :custom-image="contact.custom_image"
                                    :icon-name="contact.remote_icon ? contact.remote_icon.icon_name : ''"
                                    :icon-foreground-colour="
                                        contact.remote_icon ? contact.remote_icon.foreground_colour : ''
                                    "
                                    :icon-background-colour="
                                        contact.remote_icon ? contact.remote_icon.background_colour : ''
                                    "
                                    icon-class="size-10 sm:size-12"
                                />
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="font-semibold text-gray-900 dark:text-zinc-100 truncate">
                                    {{ contact.name }}
                                </div>
                                <div class="text-xs font-mono text-gray-500 dark:text-zinc-400 break-all">
                                    {{ contact.lxmf_address || contact.remote_identity_hash }}
                                </div>
                            </div>
                            <button
                                type="button"
                                class="p-1.5 rounded-lg text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 hover:text-gray-700 dark:hover:text-zinc-200 transition-colors"
                                :title="$t('contacts.actions')"
                                @click.stop="openContextMenu($event, contact)"
                            >
                                <MaterialDesignIcon icon-name="dots-vertical" class="size-5" />
                            </button>
                        </div>
                        <div v-if="hasMoreContacts && !isLoadingMore" class="pt-2 flex justify-center">
                            <button type="button" class="secondary-chip" @click="loadMoreContacts">
                                {{ $t("contacts.load_more") }}
                            </button>
                        </div>
                        <div v-if="isLoadingMore" class="py-3 flex justify-center">
                            <div
                                class="size-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Contact context menu -->
        <div
            v-if="contextMenu.visible"
            class="fixed z-[210] min-w-48 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl"
            :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
        >
            <button type="button" class="context-item" @click="shareContact(contextMenu.contact)">
                <MaterialDesignIcon icon-name="share-variant" class="size-4" />
                {{ $t("contacts.share_contact") }}
            </button>
            <button type="button" class="context-item" @click="copyContactUri(contextMenu.contact)">
                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                {{ $t("contacts.copy_contact_uri") }}
            </button>
            <button
                type="button"
                class="context-item text-red-600 dark:text-red-400"
                @click="removeContact(contextMenu.contact)"
            >
                <MaterialDesignIcon icon-name="delete-outline" class="size-4" />
                {{ $t("contacts.remove_contact") }}
            </button>
        </div>

        <!-- Add contact dialog -->
        <div
            v-if="isAddDialogOpen"
            class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="closeAddDialog"
        >
            <div class="w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100">{{ $t("contacts.add_contact") }}</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="closeAddDialog"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <div>
                        <label class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1">
                            {{ $t("contacts.contact_name_optional") }}
                        </label>
                        <input
                            v-model="newContactName"
                            type="text"
                            class="input-field"
                            :placeholder="$t('contacts.contact_name_placeholder')"
                        />
                    </div>
                    <div>
                        <label class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1">
                            {{ $t("contacts.hash_or_uri") }}
                        </label>
                        <input
                            v-model="newContactInput"
                            type="text"
                            class="input-field font-mono"
                            :placeholder="$t('contacts.hash_or_uri_placeholder')"
                            @keydown.enter.prevent="submitAddContact"
                        />
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button type="button" class="secondary-chip" @click="pasteFromClipboard">
                            <MaterialDesignIcon icon-name="clipboard-text-outline" class="size-4" />
                            {{ $t("contacts.paste") }}
                        </button>
                        <button v-if="cameraSupported" type="button" class="secondary-chip" @click="openScannerDialog">
                            <MaterialDesignIcon icon-name="qrcode-scan" class="size-4" />
                            {{ $t("contacts.scan_qr") }}
                        </button>
                    </div>
                </div>
                <div class="px-5 py-4 border-t border-gray-100 dark:border-zinc-800 flex justify-end gap-2">
                    <button type="button" class="secondary-chip" @click="closeAddDialog">
                        {{ $t("common.cancel") }}
                    </button>
                    <button
                        type="button"
                        class="primary-chip"
                        :disabled="!newContactInput || isSubmitting"
                        @click="submitAddContact"
                    >
                        <MaterialDesignIcon
                            :icon-name="isSubmitting ? 'loading' : 'check'"
                            class="size-4"
                            :class="{ 'animate-spin': isSubmitting }"
                        />
                        {{ $t("contacts.add_contact") }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Scanner dialog -->
        <div
            v-if="isScannerDialogOpen"
            class="fixed inset-0 z-[220] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            @click.self="closeScannerDialog"
        >
            <div class="w-full max-w-xl rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100">{{ $t("contacts.scan_qr") }}</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="closeScannerDialog"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-3">
                    <video
                        ref="scannerVideo"
                        class="w-full rounded-xl bg-black max-h-[60vh]"
                        autoplay
                        playsinline
                        muted
                    ></video>
                    <div class="text-sm text-gray-500 dark:text-zinc-400">
                        {{ scannerError || $t("contacts.scanner_hint") }}
                    </div>
                </div>
            </div>
        </div>

        <!-- My identity dialog -->
        <div
            v-if="isMyIdentityDialogOpen"
            class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="isMyIdentityDialogOpen = false"
        >
            <div class="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100">
                        {{ $t("contacts.share_my_identity") }}
                    </h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="isMyIdentityDialogOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-4">
                    <div class="flex justify-center">
                        <img
                            v-if="myQrDataUrl"
                            :src="myQrDataUrl"
                            alt="Identity QR"
                            class="w-52 h-52 rounded-xl border border-gray-200 dark:border-zinc-800 bg-white"
                        />
                    </div>
                    <div class="text-xs font-mono break-all text-center text-gray-600 dark:text-zinc-300">
                        {{ myIdentityUri }}
                    </div>
                    <div class="flex justify-center gap-2">
                        <button
                            type="button"
                            class="secondary-chip"
                            @click="copyToClipboard(myIdentityUri, $t('contacts.identity_uri_copied'))"
                        >
                            <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                            {{ $t("common.copy") }}
                        </button>
                        <button type="button" class="primary-chip" @click="shareUri(myIdentityUri)">
                            <MaterialDesignIcon icon-name="share-variant" class="size-4" />
                            {{ $t("contacts.share") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import QRCode from "qrcode";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import ToastUtils from "../../js/ToastUtils";

import LxmfUserIcon from "../LxmfUserIcon.vue";

export default {
    name: "ContactsPage",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    data() {
        return {
            contacts: [],
            contactsSearch: "",
            isLoading: false,
            isLoadingMore: false,
            searchDebounceTimeout: null,
            contactsPageSize: 30,
            contactsOffset: 0,
            totalContactsCount: 0,

            config: null,
            myIdentityUri: null,
            myQrDataUrl: null,
            isMyIdentityDialogOpen: false,

            isAddDialogOpen: false,
            isSubmitting: false,
            newContactName: "",
            newContactInput: "",

            isScannerDialogOpen: false,
            scannerError: null,
            scannerStream: null,
            scannerAnimationFrame: null,
            pendingLxmaImport: false,

            contextMenu: {
                visible: false,
                x: 0,
                y: 0,
                contact: null,
            },
        };
    },
    computed: {
        cameraSupported() {
            return (
                typeof window !== "undefined" &&
                typeof window.BarcodeDetector !== "undefined" &&
                navigator?.mediaDevices?.getUserMedia
            );
        },
        hasMoreContacts() {
            return this.contacts.length < this.totalContactsCount;
        },
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
        document.removeEventListener("click", this.closeContextMenu);
        this.stopScanner();
        if (this.searchDebounceTimeout) {
            clearTimeout(this.searchDebounceTimeout);
        }
    },
    async mounted() {
        document.addEventListener("click", this.closeContextMenu);
        WebSocketConnection.on("message", this.onWebsocketMessage);
        await this.getConfig();
        await this.getContacts();
    },
    methods: {
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
                this.myIdentityUri = this.buildMyIdentityUri();
                if (this.myIdentityUri) {
                    this.myQrDataUrl = await QRCode.toDataURL(this.myIdentityUri, { margin: 1, scale: 6 });
                }
            } catch (e) {
                console.log(e);
            }
        },
        buildMyIdentityUri() {
            if (!this.config?.lxmf_address_hash) return null;
            if (this.config?.identity_public_key) {
                return `lxma://${this.config.lxmf_address_hash}:${this.config.identity_public_key}`;
            }
            return `lxmf://${this.config.lxmf_address_hash}`;
        },
        async getContacts(append = false) {
            if (append) {
                this.isLoadingMore = true;
            } else {
                this.isLoading = true;
                this.contactsOffset = 0;
            }
            try {
                const response = await window.axios.get("/api/v1/telephone/contacts", {
                    params: {
                        search: this.contactsSearch || undefined,
                        limit: this.contactsPageSize,
                        offset: this.contactsOffset,
                    },
                });
                const list = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);
                this.totalContactsCount = response.data?.total_count ?? list.length;
                if (append) {
                    this.contacts = [...this.contacts, ...list];
                } else {
                    this.contacts = list;
                }
                this.contactsOffset += list.length;
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("contacts.failed_load_contacts"));
            } finally {
                this.isLoading = false;
                this.isLoadingMore = false;
            }
        },
        loadMoreContacts() {
            if (this.isLoadingMore || !this.hasMoreContacts) return;
            this.getContacts(true);
        },
        onContactsSearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getContacts();
            }, 250);
        },
        openAddDialog() {
            this.newContactName = "";
            this.newContactInput = "";
            this.pendingLxmaImport = false;
            this.isAddDialogOpen = true;
        },
        closeAddDialog() {
            this.isAddDialogOpen = false;
            this.pendingLxmaImport = false;
        },
        openMyIdentityDialog() {
            this.isMyIdentityDialogOpen = true;
        },
        parseLxmaUri(input) {
            const normalized = input.trim();
            const match = normalized.match(/^lxma:\/\/([0-9a-f]{32}):([0-9a-f]{64}|[0-9a-f]{128})$/i);
            if (!match) return null;
            return {
                destinationHash: match[1].toLowerCase(),
                publicKeyHex: match[2].toLowerCase(),
                normalizedUri: `lxma://${match[1].toLowerCase()}:${match[2].toLowerCase()}`,
            };
        },
        extractDestinationHash(input) {
            const raw = input.trim().toLowerCase();
            if (/^[0-9a-f]{32}$/.test(raw)) return raw;
            const lxmfMatch = raw.match(/^lxmf:\/\/([0-9a-f]{32})$/);
            if (lxmfMatch) return lxmfMatch[1];
            const lxmMatch = raw.match(/^lxm:\/\/([0-9a-f]{32})$/);
            if (lxmMatch) return lxmMatch[1];
            return null;
        },
        async submitAddContact() {
            if (!this.newContactInput || this.isSubmitting) return;
            this.isSubmitting = true;
            try {
                const lxmaData = this.parseLxmaUri(this.newContactInput);
                if (lxmaData) {
                    this.pendingLxmaImport = true;
                    WebSocketConnection.send(
                        JSON.stringify({
                            type: "lxm.ingest_uri",
                            uri: lxmaData.normalizedUri,
                        })
                    );
                    ToastUtils.info(this.$t("contacts.importing_lxma"));
                    return;
                }

                const destinationHash = this.extractDestinationHash(this.newContactInput);
                if (!destinationHash) {
                    ToastUtils.error(this.$t("contacts.invalid_contact_input"));
                    return;
                }

                const existing = await window.axios.get(`/api/v1/telephone/contacts/check/${destinationHash}`);
                if (existing.data?.id) {
                    ToastUtils.info(this.$t("contacts.contact_already_exists"));
                    return;
                }

                await window.axios.post("/api/v1/telephone/contacts", {
                    name: this.newContactName?.trim() || `Contact ${destinationHash.slice(0, 8)}`,
                    remote_identity_hash: destinationHash,
                    lxmf_address: destinationHash,
                });
                ToastUtils.success(this.$t("contacts.contact_added"));
                this.closeAddDialog();
                await this.getContacts();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("contacts.failed_add_contact"));
            } finally {
                this.isSubmitting = false;
            }
        },
        async onWebsocketMessage(message) {
            let json;
            try {
                json = JSON.parse(message.data);
            } catch {
                return;
            }

            if (json.type === "lxm.ingest_uri.result" && this.pendingLxmaImport) {
                this.pendingLxmaImport = false;
                this.isSubmitting = false;
                if (json.status === "success" && json.ingest_type === "lxma_contact") {
                    ToastUtils.success(json.message || this.$t("contacts.contact_added"));
                    this.closeAddDialog();
                    await this.getContacts();
                } else if (json.status === "error") {
                    ToastUtils.error(json.message || this.$t("contacts.failed_add_contact"));
                }
            }
        },
        async removeContact(contact) {
            this.closeContextMenu();
            if (!contact?.id) return;
            if (!window.confirm(this.$t("contacts.remove_contact_confirm"))) return;
            try {
                await window.axios.delete(`/api/v1/telephone/contacts/${contact.id}`);
                ToastUtils.success(this.$t("contacts.contact_removed"));
                await this.getContacts();
            } catch {
                ToastUtils.error(this.$t("contacts.failed_remove_contact"));
            }
        },
        openContextMenu(event, contact) {
            this.contextMenu.visible = true;
            this.contextMenu.contact = contact;
            this.contextMenu.x = event.clientX;
            this.contextMenu.y = event.clientY;
        },
        closeContextMenu() {
            this.contextMenu.visible = false;
            this.contextMenu.contact = null;
        },
        async fetchContactLxmaUri(contact) {
            const destinationHash = (contact?.lxmf_address || contact?.remote_identity_hash || "").toLowerCase();
            if (!/^[0-9a-f]{32}$/.test(destinationHash)) return null;
            try {
                const response = await window.axios.get("/api/v1/announces", {
                    params: {
                        destination_hash: destinationHash,
                        limit: 1,
                    },
                });
                const announce = response.data?.announces?.[0];
                const publicKeyBase64 = announce?.identity_public_key;
                if (!publicKeyBase64) return null;
                const binary = atob(publicKeyBase64);
                const publicKeyHex = Array.from(binary)
                    .map((c) => c.charCodeAt(0).toString(16).padStart(2, "0"))
                    .join("");
                if (publicKeyHex.length !== 128) return null;
                return `lxma://${destinationHash}:${publicKeyHex}`;
            } catch {
                return null;
            }
        },
        async copyContactUri(contact) {
            this.closeContextMenu();
            const lxmaUri = await this.fetchContactLxmaUri(contact);
            if (lxmaUri) {
                await this.copyToClipboard(lxmaUri, this.$t("contacts.contact_uri_copied"));
                return;
            }

            const destinationHash = contact?.lxmf_address || contact?.remote_identity_hash;
            if (destinationHash) {
                await this.copyToClipboard(`lxmf://${destinationHash}`, this.$t("contacts.contact_uri_copied"));
            } else {
                ToastUtils.error(this.$t("contacts.failed_build_contact_uri"));
            }
        },
        async shareContact(contact) {
            this.closeContextMenu();
            const lxmaUri = await this.fetchContactLxmaUri(contact);
            const destinationHash = contact?.lxmf_address || contact?.remote_identity_hash;
            const fallback = destinationHash ? `lxmf://${destinationHash}` : null;
            const uri = lxmaUri || fallback;
            if (!uri) {
                ToastUtils.error(this.$t("contacts.failed_build_contact_uri"));
                return;
            }
            await this.shareUri(uri);
        },
        async shareUri(uri) {
            try {
                if (navigator.share) {
                    await navigator.share({
                        title: this.$t("contacts.share"),
                        text: uri,
                    });
                    return;
                }
            } catch {
                // ignore and fallback to clipboard
            }
            await this.copyToClipboard(uri, this.$t("contacts.contact_uri_copied"));
        },
        async copyToClipboard(value, successMessage) {
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(successMessage || this.$t("common.copied"));
            } catch {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
        async pasteFromClipboard() {
            try {
                this.newContactInput = await navigator.clipboard.readText();
            } catch {
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
            }
        },
        async openScannerDialog() {
            this.isScannerDialogOpen = true;
            this.scannerError = null;
            await this.$nextTick();
            await this.startScanner();
        },
        async startScanner() {
            if (!this.cameraSupported) {
                this.scannerError = this.$t("contacts.camera_not_supported");
                return;
            }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "environment" },
                    audio: false,
                });
                this.scannerStream = stream;
                const video = this.$refs.scannerVideo;
                if (!video) return;
                video.srcObject = stream;
                await video.play();
                this.detectQrLoop();
            } catch (e) {
                this.scannerError = e.message || this.$t("contacts.camera_failed");
            }
        },
        detectQrLoop() {
            if (!this.isScannerDialogOpen) return;
            const video = this.$refs.scannerVideo;
            if (!video || video.readyState < 2) {
                this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                return;
            }
            const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
            detector
                .detect(video)
                .then((barcodes) => {
                    const qr = barcodes?.[0]?.rawValue;
                    if (qr) {
                        this.newContactInput = qr.trim();
                        this.closeScannerDialog();
                        ToastUtils.success(this.$t("contacts.qr_scanned"));
                    } else {
                        this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                    }
                })
                .catch(() => {
                    this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                });
        },
        stopScanner() {
            if (this.scannerAnimationFrame) {
                cancelAnimationFrame(this.scannerAnimationFrame);
                this.scannerAnimationFrame = null;
            }
            if (this.scannerStream) {
                this.scannerStream.getTracks().forEach((track) => track.stop());
                this.scannerStream = null;
            }
        },
        closeScannerDialog() {
            this.isScannerDialogOpen = false;
            this.stopScanner();
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/95 dark:bg-zinc-900/85 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-sm p-4;
}

.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}

.primary-chip {
    @apply inline-flex items-center gap-1 rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 text-xs font-semibold transition disabled:opacity-60;
}

.secondary-chip {
    @apply inline-flex items-center gap-1 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-200 px-3 py-2 text-xs font-semibold transition;
}

.context-item {
    @apply w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800 flex items-center gap-2;
}
</style>
