// @ts-check

import { STORAGE_KEYS } from "../constants.js";
import { useIdentityScope } from "../identityScope.js";

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
    const scope = options.identityScope || useIdentityScope({ getIdentityKey: options.getIdentityKey });
    const lastDraftIdentityKey = scope.identityKey;
    const getNewMessageText = options.getNewMessageText || (() => "");
    const setDraftText = options.setDraftText || (() => {});

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
            // Record which identity the composer text belongs to before any
            // saveDraft call, so a later save cannot fall back to a switched
            // identity and leak the draft into the wrong bucket.
            const key = scope.beginIdentity(identityKey);
            const drafts = readDraftRoot();
            // Drafts saved before the identity hash resolved landed in the
            // "_" fallback bucket. Fold them into the real bucket once the
            // hash is known so they are not orphaned behind the nested
            // bucket check. Existing real-bucket entries win.
            if (key !== "_" && drafts["_"] !== undefined) {
                const fallback = draftBucketFor(drafts, "_");
                if (fallback) {
                    let target = draftBucketFor(drafts, key);
                    if (!target) {
                        target = {};
                        drafts[key] = target;
                    }
                    for (const [dest, draftText] of Object.entries(fallback)) {
                        if (typeof draftText === "string" && typeof target[dest] !== "string") {
                            target[dest] = draftText;
                        }
                    }
                }
                delete drafts["_"];
                localStorage.setItem(STORAGE_KEYS.MESSAGE_DRAFTS, JSON.stringify(drafts));
            }
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
            const key = scope.keyForWrite(identityKey);
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
            scope.identityKey.value = key;
        } catch (e) {
            console.error("Failed to save draft:", e);
        }
    }

    return {
        lastDraftIdentityKey,
        loadDraft,
        saveDraft,
        identityScope: scope,
    };
}
