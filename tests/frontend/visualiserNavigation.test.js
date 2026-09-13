// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    attachAnnounceMetaToNodes,
    openAnnounceDestination,
    resolveAnnounceDestinationHash,
} from "@/features/network-visualiser/lib/visualiserNavigation.ts";

vi.mock("@/shell/hashRouter.js", () => ({
    navigate: vi.fn(),
}));

import { navigate } from "@/shell/hashRouter.js";

describe("visualiserNavigation", () => {
    beforeEach(() => {
        vi.mocked(navigate).mockReset();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("resolves destination hash from announce or fallback", () => {
        expect(resolveAnnounceDestinationHash({ destination_hash: "aa" }, "bb")).toBe("aa");
        expect(resolveAnnounceDestinationHash(null, "bb")).toBe("bb");
    });

    it("attaches announce meta onto matching node ids", () => {
        const nodes = [{ id: "deadbeef" }, { id: "iface1" }];
        attachAnnounceMetaToNodes(nodes, {
            deadbeef: { destination_hash: "deadbeef", aspect: "lxmf.delivery" },
        });
        expect(nodes[0]._announce?.aspect).toBe("lxmf.delivery");
        expect(nodes[1]._announce).toBeUndefined();
    });

    it("opens lxmf.delivery announces in messages", () => {
        openAnnounceDestination({ destination_hash: "abcd", aspect: "lxmf.delivery" }, "");
        expect(navigate).toHaveBeenCalledWith({
            name: "messages",
            params: { destinationHash: "abcd" },
        });
    });

    it("opens nomadnetwork.node announces in nomadnetwork", () => {
        openAnnounceDestination({ destination_hash: "nn01", aspect: "nomadnetwork.node" }, "");
        expect(navigate).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: "nn01" },
            query: { newTab: "1" },
        });
    });

    it("ignores announces without a navigable aspect", () => {
        openAnnounceDestination({ destination_hash: "x", aspect: "other" }, "");
        expect(navigate).not.toHaveBeenCalled();
    });
});
