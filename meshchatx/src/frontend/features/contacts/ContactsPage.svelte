<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import QRCode from "qrcode";
    import EmptyState from "../../ui/svelte/EmptyState.svelte";
    import LoadingState from "../../ui/svelte/LoadingState.svelte";
    import Skeleton from "../../ui/svelte/Skeleton.svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { isCameraSupported } from "../../js/qrScannerUtils.js";
    import { t } from "../../js/i18n.js";
    import { buildMyIdentityUri } from "./lib/contactUri.js";
    import { mergeContactsByName } from "./lib/mergeContacts.js";
    import {
        addContactFromInput,
        callHashHref,
        copyToClipboard,
        editContactNameWithDuplicates,
        exportContactsFile,
        fetchContactLxmaUri,
        importContactsList,
        messagesHashHref,
        removeContactWithDuplicates,
        shareUri,
    } from "./lib/contactsActions.js";
    import ContactListRow from "./components/ContactListRow.svelte";
    import ContactsToolbar from "./components/ContactsToolbar.svelte";
    import ContactsAddDialog from "./components/ContactsAddDialog.svelte";
    import ContactsImportDialog from "./components/ContactsImportDialog.svelte";
    import ContactsMyIdentityDialog from "./components/ContactsMyIdentityDialog.svelte";
    import ContactsScannerDialog from "./components/ContactsScannerDialog.svelte";
    import ContactsContextMenu from "./components/ContactsContextMenu.svelte";

    let contacts: Array<Record<string, unknown>> = $state([]);
    let contactsSearch = $state("");
    let isLoading = $state(false);
    let isLoadingMore = $state(false);
    let contactsOffset = $state(0);
    let totalContactsCount = $state(0);
    let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;
    const contactsPageSize = 30;

    let myIdentityUri: string | null = $state(null);
    let myQrDataUrl: string | null = $state(null);
    let isMyIdentityDialogOpen = $state(false);
    let isAddDialogOpen = $state(false);
    let isSubmitting = $state(false);
    let newContactName = $state("");
    let newContactInput = $state("");
    let isScannerDialogOpen = $state(false);
    let pendingLxmaImport = $state(false);
    let isImportDialogOpen = $state(false);
    let importError: string | null = $state(null);
    let contextMenu: {
        visible: boolean;
        x: number;
        y: number;
        contact: Record<string, unknown> | null;
    } = $state({
        visible: false,
        x: 0,
        y: 0,
        contact: null,
    });

    const cameraSupported = isCameraSupported();
    const hasMoreContacts = $derived(contacts.length < totalContactsCount);
    const mergedContacts = $derived(mergeContactsByName(contacts));

    async function getConfig() {
        try {
            const response = await window.api.get("/api/v1/config");
            myIdentityUri = buildMyIdentityUri(response.data.config);
            if (myIdentityUri) {
                myQrDataUrl = await QRCode.toDataURL(myIdentityUri, { margin: 1, scale: 6 });
            }
        } catch (e) {
            console.log(e);
        }
    }

    async function getContacts(append = false) {
        if (append) isLoadingMore = true;
        else {
            isLoading = true;
            contactsOffset = 0;
        }
        try {
            const response = await window.api.get("/api/v1/telephone/contacts", {
                params: {
                    search: contactsSearch || undefined,
                    limit: contactsPageSize,
                    offset: contactsOffset,
                },
            });
            const list = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);
            totalContactsCount = response.data?.total_count ?? list.length;
            contacts = append ? [...contacts, ...list] : list;
            contactsOffset += list.length;
        } catch (e) {
            console.log(e);
            ToastUtils.error(t("contacts.failed_load_contacts"));
        } finally {
            isLoading = false;
            isLoadingMore = false;
        }
    }

    function onContactsSearchInput() {
        if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
        searchDebounceTimeout = setTimeout(() => getContacts(), 250);
    }

    function closeContextMenu() {
        contextMenu = { visible: false, x: 0, y: 0, contact: null };
    }

    function openContextMenu(event: MouseEvent, contact: Record<string, unknown>) {
        contextMenu = { visible: true, x: event.clientX, y: event.clientY, contact };
    }

    function openConversation(contact: Record<string, unknown>) {
        closeContextMenu();
        const href = messagesHashHref(contact);
        if (href) location.hash = href;
    }

    function callContact(contact: Record<string, unknown>) {
        closeContextMenu();
        const href = callHashHref(contact);
        if (href) location.hash = href;
    }

    function openAddDialog() {
        newContactName = "";
        newContactInput = "";
        pendingLxmaImport = false;
        isAddDialogOpen = true;
    }

    async function submitAddContact() {
        if (!newContactInput || isSubmitting) return;
        isSubmitting = true;
        try {
            const result = await addContactFromInput(newContactInput, newContactName, {
                setPendingLxma: (v) => (pendingLxmaImport = v),
                onAdded: async () => {
                    isAddDialogOpen = false;
                    pendingLxmaImport = false;
                    await getContacts();
                },
            });
            if (result.added) {
                isAddDialogOpen = false;
                pendingLxmaImport = false;
            }
        } catch (e: any) {
            ToastUtils.error(e.response?.data?.message || t("contacts.failed_add_contact"));
        } finally {
            isSubmitting = false;
        }
    }

    async function onLxmIngestUriResult(json: { status?: string; ingest_type?: string; message?: string }) {
        if (!pendingLxmaImport) return;
        pendingLxmaImport = false;
        isSubmitting = false;
        if (json.status === "success" && json.ingest_type === "lxma_contact") {
            ToastUtils.success(json.message || t("contacts.contact_added"));
            isAddDialogOpen = false;
            await getContacts();
        } else if (json.status === "error") {
            ToastUtils.error(json.message || t("contacts.failed_add_contact"));
        }
    }

    function onImportFileSelected(file: File) {
        importError = null;
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const json = JSON.parse(String(e.target?.result || "{}"));
                const list = json.contacts ?? (Array.isArray(json) ? json : []);
                if (!Array.isArray(list) || list.length === 0) {
                    importError = t("contacts.import_failed");
                    return;
                }
                const err = await importContactsList(list, getContacts);
                if (err) importError = err;
                else isImportDialogOpen = false;
            } catch {
                importError = t("contacts.import_failed");
            }
        };
        reader.readAsText(file);
    }

    onMount(() => {
        document.addEventListener("click", closeContextMenu);
        onWsEvent("lxm.ingest_uri.result", onLxmIngestUriResult);
        getConfig();
        getContacts();
        return () => {
            offWsEvent("lxm.ingest_uri.result", onLxmIngestUriResult);
            document.removeEventListener("click", closeContextMenu);
            if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
        };
    });
</script>

<div class="flex flex-1 min-w-0 h-full overflow-hidden bg-sem-canvas" data-testid="contacts-page">
    <div class="flex-1 flex flex-col min-h-0 overflow-hidden p-4 md:p-6">
        <div class="max-w-5xl mx-auto w-full shrink-0 border-b border-sem-border pb-6">
            <ContactsToolbar
                {totalContactsCount}
                onShareIdentity={() => (isMyIdentityDialogOpen = true)}
                onExport={exportContactsFile}
                onImport={() => {
                    importError = null;
                    isImportDialogOpen = true;
                }}
                onAdd={openAddDialog}
            />
        </div>

        <div class="max-w-5xl mx-auto w-full flex flex-col flex-1 min-h-0 pt-4">
            <div class="shrink-0 border-b border-sem-border pb-3">
                <div class="relative group">
                    <MaterialDesignIcon
                        iconName="magnify"
                        class="absolute left-3 top-1/2 -translate-y-1/2 size-5 shrink-0 text-gray-400 group-focus-within:text-sem-accent transition-colors pointer-events-none z-10"
                    />
                    <input
                        bind:value={contactsSearch}
                        type="text"
                        placeholder={t("contacts.search_placeholder")}
                        class="input-field pl-11!"
                        oninput={onContactsSearchInput}
                    />
                </div>
            </div>

            <div class="min-w-0 flex-1 min-h-0 flex flex-col">
                {#if isLoading && contacts.length === 0}
                    <div class="space-y-3 p-2" aria-busy="true">
                        {#each Array(6) as _, i (i)}
                            <div class="flex items-center gap-3">
                                <Skeleton variant="avatar" />
                                <div class="flex-1 space-y-2">
                                    <Skeleton variant="line" class="w-2/3" />
                                    <Skeleton variant="line" class="w-1/2" />
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else if !isLoading && contacts.length === 0}
                    <EmptyState icon="account-multiple-outline" title={t("contacts.no_contacts")} />
                {:else}
                    <div class="divide-y divide-sem-border overflow-y-auto flex-1 min-h-0" role="list">
                        {#each mergedContacts as contact (String(contact.id))}
                            <ContactListRow
                                {contact}
                                onOpenConversation={openConversation}
                                onCall={callContact}
                                onContextMenu={openContextMenu}
                                onCopyHash={(hash) => copyToClipboard(hash, t("common.copied"))}
                            />
                        {/each}
                        {#if hasMoreContacts && !isLoadingMore}
                            <div class="pt-2 flex justify-center">
                                <button
                                    type="button"
                                    class="secondary-chip focus-ring-sem"
                                    onclick={() => getContacts(true)}
                                >
                                    {t("contacts.load_more")}
                                </button>
                            </div>
                        {/if}
                        {#if isLoadingMore}
                            <LoadingState class="py-3" />
                        {/if}
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <button
        type="button"
        class="sm:hidden fixed bottom-5 right-4 z-180 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg ring-1 ring-blue-400/30 transition active:scale-95 focus-ring-sem"
        title={t("contacts.add_contact")}
        onclick={openAddDialog}
    >
        <MaterialDesignIcon iconName="plus" class="size-7" />
    </button>

    <ContactsContextMenu
        visible={contextMenu.visible}
        x={contextMenu.x}
        y={contextMenu.y}
        onSendMessage={() => contextMenu.contact && openConversation(contextMenu.contact)}
        onCall={() => contextMenu.contact && callContact(contextMenu.contact)}
        onEdit={() => contextMenu.contact && editContactNameWithDuplicates(contextMenu.contact, contacts, getContacts)}
        onShare={async () => {
            if (!contextMenu.contact) return;
            const c = contextMenu.contact;
            closeContextMenu();
            const lxmaUri = await fetchContactLxmaUri(c);
            const dest = c?.lxmf_address || c?.remote_identity_hash;
            const uri = lxmaUri || (dest ? `lxmf://${dest}` : null);
            if (!uri) ToastUtils.error(t("contacts.failed_build_contact_uri"));
            else await shareUri(uri);
        }}
        onCopyUri={async () => {
            if (!contextMenu.contact) return;
            const c = contextMenu.contact;
            closeContextMenu();
            const lxmaUri = await fetchContactLxmaUri(c);
            if (lxmaUri) {
                await copyToClipboard(lxmaUri, t("contacts.contact_uri_copied"));
                return;
            }
            const dest = c?.lxmf_address || c?.remote_identity_hash;
            if (dest) await copyToClipboard(`lxmf://${dest}`, t("contacts.contact_uri_copied"));
            else ToastUtils.error(t("contacts.failed_build_contact_uri"));
        }}
        onRemove={() => contextMenu.contact && removeContactWithDuplicates(contextMenu.contact, contacts, getContacts)}
    />

    <ContactsAddDialog
        bind:name={newContactName}
        bind:input={newContactInput}
        open={isAddDialogOpen}
        {isSubmitting}
        {cameraSupported}
        onClose={() => {
            isAddDialogOpen = false;
            pendingLxmaImport = false;
        }}
        onSubmit={submitAddContact}
        onPaste={async () => {
            try {
                newContactInput = await navigator.clipboard.readText();
            } catch {
                ToastUtils.error(t("messages.failed_read_clipboard"));
            }
        }}
        onScan={() => (isScannerDialogOpen = true)}
    />

    <ContactsScannerDialog
        open={isScannerDialogOpen}
        onClose={() => (isScannerDialogOpen = false)}
        onScanned={(value) => (newContactInput = value)}
    />

    <ContactsImportDialog
        open={isImportDialogOpen}
        {importError}
        onClose={() => {
            isImportDialogOpen = false;
            importError = null;
        }}
        onFileSelected={onImportFileSelected}
    />

    <ContactsMyIdentityDialog
        open={isMyIdentityDialogOpen}
        {myIdentityUri}
        {myQrDataUrl}
        onClose={() => (isMyIdentityDialogOpen = false)}
        onCopy={() => myIdentityUri && copyToClipboard(myIdentityUri, t("contacts.identity_uri_copied"))}
        onShare={() => myIdentityUri && shareUri(myIdentityUri)}
    />
</div>
