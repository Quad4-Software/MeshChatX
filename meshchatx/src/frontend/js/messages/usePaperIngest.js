// @ts-check

import { ref } from "vue";

import ToastUtils from "../ToastUtils.js";
import WebSocketConnection from "../WebSocketConnection.js";
import {
    isPaperMessageIngested as isPaperMessageIngestedStored,
    listIngestedPaperMessageHashes,
    markPaperMessageIngested,
    normalizePaperIngestMessageHash,
    shouldMarkPaperIngestFromResultStatus,
} from "../../components/messages/conversationPaperIngest.js";

/**
 * Paper-message ingest state for ConversationViewer: the pending ingest
 * result hash, the identity-scoped ingested-hash map, WS ingest request,
 * and the lxm.ingest_uri result handler.
 *
 * options.getIdentityKey resolves the active identity bucket the ingested
 * hashes are stored under. options.t is the host i18n function.
 */
export function usePaperIngest(options = {}) {
    const getIdentityKey = options.getIdentityKey || (() => "_");
    const t = options.t || ((key) => key);

    const pendingPaperIngestMessageHash = ref(null);
    /** @type {import("vue").Ref<Record<string, boolean>>} */
    const ingestedPaperMessageHashes = ref({});

    function reloadIngestedPaperMessageHashes() {
        const hashes = listIngestedPaperMessageHashes(getIdentityKey());
        /** @type {Record<string, boolean>} */
        const next = {};
        for (const hash of hashes) {
            next[hash] = true;
        }
        ingestedPaperMessageHashes.value = next;
    }

    function isPaperMessageIngested(chatItem) {
        const hash = normalizePaperIngestMessageHash(chatItem?.lxmf_message?.hash);
        if (!hash) {
            return false;
        }
        if (ingestedPaperMessageHashes.value[hash]) {
            return true;
        }
        return isPaperMessageIngestedStored(getIdentityKey(), hash);
    }

    async function ingestPaperMessage(uri, messageHash = null) {
        try {
            const hash = normalizePaperIngestMessageHash(messageHash);
            pendingPaperIngestMessageHash.value = hash || null;
            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxm.ingest_uri",
                    uri: uri,
                })
            );
            ToastUtils.info(t("messages.ingesting_paper_message"));
        } catch (e) {
            console.error(e);
            pendingPaperIngestMessageHash.value = null;
            ToastUtils.error(t("messages.failed_ingest_paper"));
        }
    }

    function onLxmIngestUriResultEvent(json) {
        const pendingHash = pendingPaperIngestMessageHash.value;
        pendingPaperIngestMessageHash.value = null;
        if (!pendingHash || !shouldMarkPaperIngestFromResultStatus(json?.status)) {
            return;
        }
        const list = markPaperMessageIngested(getIdentityKey(), pendingHash);
        const next = { ...ingestedPaperMessageHashes.value };
        for (const hash of list) {
            next[hash] = true;
        }
        next[pendingHash] = true;
        ingestedPaperMessageHashes.value = next;
    }

    return {
        pendingPaperIngestMessageHash,
        ingestedPaperMessageHashes,
        reloadIngestedPaperMessageHashes,
        isPaperMessageIngested,
        ingestPaperMessage,
        onLxmIngestUriResultEvent,
    };
}
