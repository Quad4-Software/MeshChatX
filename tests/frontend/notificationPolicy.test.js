// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach } from "vitest";
import {
    shouldShowOsMessageNotification,
    shouldPlayMessageSound,
    isUserFacingLxmfDeliveryMessage,
    deliverySourceHash,
} from "../../meshchatx/src/frontend/js/notificationPolicy.js";
import {
    setOpenDestinationHashes,
    listOpenDestinationHashes,
    clearOpenDestinationHashesForTests,
    hasOpenDestinationHash,
} from "../../meshchatx/src/frontend/js/activeConversationStore.js";

const peerA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const peerB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

describe("notificationPolicy", () => {
    it("DND blocks OS and sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                dnd: true,
                hasFocus: false,
                userFacing: true,
                sourceHash: peerA,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                dnd: true,
                hasFocus: false,
                userFacing: true,
                sourceHash: peerA,
            })
        ).toBe(false);
    });

    it("sieve suppress blocks OS and sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                sieveSuppress: true,
                hasFocus: false,
                userFacing: true,
                sourceHash: peerA,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                sieveSuppress: true,
                hasFocus: true,
                userFacing: true,
                sourceHash: peerA,
            })
        ).toBe(false);
    });

    it("open peer A + msg A + focused: no OS, no sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [peerA],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [peerA],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(false);
    });

    it("open peer A + msg A + blurred: OS and sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [peerA],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(true);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [peerA],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(true);
    });

    it("open A + msg B + focused: no OS, sound for B", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [peerA],
                sourceHash: peerB,
                userFacing: true,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [peerA],
                sourceHash: peerB,
                userFacing: true,
            })
        ).toBe(true);
    });

    it("open A + msg B + blurred: OS and sound for B", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [peerA],
                sourceHash: peerB,
                userFacing: true,
            })
        ).toBe(true);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [peerA],
                sourceHash: peerB,
                userFacing: true,
            })
        ).toBe(true);
    });

    it("no open peers + blurred: OS and sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(true);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: false,
                openDestinationHashes: [],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(true);
    });

    it("no open peers + focused: no OS, sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: true,
                openDestinationHashes: [],
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(true);
    });

    it("outbound: no OS or sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: false,
                hasFocus: false,
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: false,
                hasFocus: false,
                sourceHash: peerA,
                userFacing: true,
            })
        ).toBe(false);
    });

    it("non-user-facing: no OS or sound", () => {
        expect(
            shouldShowOsMessageNotification({
                isIncoming: true,
                hasFocus: false,
                sourceHash: peerA,
                userFacing: false,
            })
        ).toBe(false);
        expect(
            shouldPlayMessageSound({
                isIncoming: true,
                hasFocus: false,
                sourceHash: peerA,
                userFacing: false,
            })
        ).toBe(false);
    });

    it("isUserFacingLxmfDeliveryMessage filters reactions and empty telemetry", () => {
        expect(isUserFacingLxmfDeliveryMessage({ is_reaction: true, content: "" })).toBe(false);
        expect(
            isUserFacingLxmfDeliveryMessage({
                content: "",
                title: "",
                fields: { reaction: { reaction_to: "abc" } },
            })
        ).toBe(false);
        expect(
            isUserFacingLxmfDeliveryMessage({
                content: "",
                title: "",
                fields: { telemetry: { x: 1 } },
            })
        ).toBe(false);
        expect(isUserFacingLxmfDeliveryMessage({ content: "hi", title: "" })).toBe(true);
        expect(
            isUserFacingLxmfDeliveryMessage({
                content: "",
                title: "",
                fields: { image: { image_bytes: "x" } },
            })
        ).toBe(true);
    });

    it("deliverySourceHash prefers lxmf_message.source_hash", () => {
        expect(
            deliverySourceHash({
                remote_identity_hash: peerB,
                lxmf_message: { source_hash: peerA },
            })
        ).toBe(peerA);
    });
});

describe("activeConversationStore", () => {
    beforeEach(() => {
        clearOpenDestinationHashesForTests();
    });

    it("tracks open destination hashes", () => {
        setOpenDestinationHashes([peerA, peerB, ""]);
        expect(listOpenDestinationHashes().sort()).toEqual([peerA, peerB].sort());
        expect(hasOpenDestinationHash(peerA.toUpperCase())).toBe(true);
        setOpenDestinationHashes([]);
        expect(listOpenDestinationHashes()).toEqual([]);
    });
});
