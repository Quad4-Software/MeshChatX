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
 * Paper-message ingest state for ConversationViewer: pending ingest
 * results keyed by request id, the identity-scoped ingested-hash map,
 * WS ingest request, and the lxm.ingest_uri result handler.
 *
 * options.getIdentityKey resolves the active identity bucket the ingested
 * hashes are stored under. options.t is the host i18n function.
 */
export function usePaperIngest(options = {}) {
    const getIdentityKey = options.getIdentityKey || (() => "_");
    const t = options.t || ((key) => key);

    const pendingPaperIngestMessageHash = ref(null);
    /** @type {import("vue").Ref<Record<string, string | null>>} requestId -> message hash */
    const pendingPaperIngests = ref({});
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

    function nextRequestId() {
        if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
            return crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }

    function refreshPendingDisplayHash() {
        const remaining = Object.values(pendingPaperIngests.value).filter(Boolean);
        pendingPaperIngestMessageHash.value = remaining.length ? remaining[remaining.length - 1] : null;
    }

    async function ingestPaperMessage(uri, messageHash = null) {
        try {
            const hash = normalizePaperIngestMessageHash(messageHash);
            const requestId = nextRequestId();
            const sent = WebSocketConnection.send(
                JSON.stringify({
                    type: "lxm.ingest_uri",
                    uri: uri,
                    request_id: requestId,
                })
            );
            if (!sent) {
                ToastUtils.error(t("messages.failed_ingest_paper"));
                return;
            }
            // Only register the request once it is on the wire so an
            // unrelated result cannot set a false ingested badge.
            pendingPaperIngests.value = { ...pendingPaperIngests.value, [requestId]: hash || null };
            refreshPendingDisplayHash();
            ToastUtils.info(t("messages.ingesting_paper_message"));
        } catch (e) {
            console.error(e);
            pendingPaperIngestMessageHash.value = null;
            ToastUtils.error(t("messages.failed_ingest_paper"));
        }
    }

    function onLxmIngestUriResultEvent(json) {
        const requestId = json && json.request_id != null ? String(json.request_id) : null;
        if (requestId == null) {
            // Results without a request id come from ingests this composable
            // did not send; they must not consume a pending paper hash.
            return;
        }
        const pending = { ...pendingPaperIngests.value };
        if (!(requestId in pending)) {
            return;
        }
        const pendingHash = pending[requestId];
        delete pending[requestId];
        pendingPaperIngests.value = pending;
        refreshPendingDisplayHash();
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
        pendingPaperIngests,
        ingestedPaperMessageHashes,
        reloadIngestedPaperMessageHashes,
        isPaperMessageIngested,
        ingestPaperMessage,
        onLxmIngestUriResultEvent,
    };
}
