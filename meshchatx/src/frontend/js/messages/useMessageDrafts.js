// @ts-check

import { ref } from "vue";

import { STORAGE_KEYS } from "../constants.js";

/**
 * Conversation draft persistence for ConversationViewer. Drafts live in
 * localStorage under a per-identity bucket so a draft written under one
 * identity never leaks into another identity's compose box.
 *
 * options.getIdentityKey resolves the active identity bucket (defaults to
 * "_"). options.getNewMessageText / options.setDraftText bridge to the
 * compose textarea state the host owns.
 */
export function useMessageDrafts(options = {}) {
    const getIdentityKey = options.getIdentityKey || (() => "_");
    const getNewMessageText = options.getNewMessageText || (() => "");
    const setDraftText = options.setDraftText || (() => {});

    const lastDraftIdentityKey = ref("");

    function readDraftRoot() {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEYS.MESSAGE_DRAFTS) || "{}");
        return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
    }

    function draftBucketFor(drafts, identityKey) {
        const nested = drafts[identityKey];
        if (nested && typeof nested === "object" && !Array.isArray(nested)) {
            return nested;
        }
        return null;
    }

    function hasNestedDraftBuckets(drafts) {
        return Object.values(drafts).some((value) => value && typeof value === "object" && !Array.isArray(value));
    }

    function loadDraft(destinationHash, identityKey) {
        try {
            const drafts = readDraftRoot();
            const key = identityKey || getIdentityKey();
            const bucket = draftBucketFor(drafts, key);
            let text = "";
            if (bucket && typeof bucket[destinationHash] === "string") {
                text = bucket[destinationHash];
            } else if (!hasNestedDraftBuckets(drafts) && typeof drafts[destinationHash] === "string") {
                // Legacy flat keys (pre identity-scoped drafts).
                text = drafts[destinationHash];
            }
            setDraftText(text);
        } catch (e) {
            console.error("Failed to load draft:", e);
        }
    }

    function saveDraft(destinationHash, identityKey) {
        try {
            const drafts = readDraftRoot();
            const key = identityKey || getIdentityKey();
            let bucket = draftBucketFor(drafts, key);
            if (!bucket) {
                bucket = {};
                drafts[key] = bucket;
                if (typeof drafts[destinationHash] === "string") {
                    delete drafts[destinationHash];
                }
            }
            if (getNewMessageText()) {
                bucket[destinationHash] = getNewMessageText();
            } else {
                delete bucket[destinationHash];
            }
            localStorage.setItem(STORAGE_KEYS.MESSAGE_DRAFTS, JSON.stringify(drafts));
            lastDraftIdentityKey.value = key;
        } catch (e) {
            console.error("Failed to save draft:", e);
        }
    }

    return {
        lastDraftIdentityKey,
        loadDraft,
        saveDraft,
    };
}
