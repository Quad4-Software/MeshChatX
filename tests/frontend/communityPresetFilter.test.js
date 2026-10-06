// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    COMMUNITY_FILTER_OPTIONS,
    communityPresetAddress,
    communityPresetGroup,
    filterCommunityInterfaces,
} from "../../meshchatx/src/frontend/js/interfaces/communityPresetFilter.js";

const tcp = { name: "tcp-node", type: "TCPClientInterface" };
const backbone = { name: "bb", type: "BackboneInterface" };
const i2p = { name: "i2p-node", type: "I2PInterface", i2p_peers: ["abc.b32.i2p"] };
const ygg = { name: "ygg", type: "YggdrasilInterface" };
const other = { name: "udp", type: "UDPInterface" };
const list = [tcp, backbone, i2p, ygg, other];

describe("communityPresetGroup", () => {
    it("maps known types to groups", () => {
        expect(communityPresetGroup(tcp)).toBe("tcp");
        expect(communityPresetGroup(backbone)).toBe("backbone");
        expect(communityPresetGroup(i2p)).toBe("i2p");
        expect(communityPresetGroup(ygg)).toBe("yggdrasil");
    });

    it("maps unknown or missing types to other", () => {
        expect(communityPresetGroup(other)).toBe("other");
        expect(communityPresetGroup({ name: "x" })).toBe("other");
        expect(communityPresetGroup(null)).toBe("other");
        expect(communityPresetGroup({ type: "AutoInterface" })).toBe("other");
    });
});

describe("filterCommunityInterfaces", () => {
    it("returns everything for all", () => {
        expect(filterCommunityInterfaces(list, "all")).toEqual(list);
    });

    it("treats a missing group as all", () => {
        expect(filterCommunityInterfaces(list, null)).toEqual(list);
        expect(filterCommunityInterfaces(list, undefined)).toEqual(list);
    });

    it("filters by each group", () => {
        expect(filterCommunityInterfaces(list, "tcp")).toEqual([tcp]);
        expect(filterCommunityInterfaces(list, "backbone")).toEqual([backbone]);
        expect(filterCommunityInterfaces(list, "i2p")).toEqual([i2p]);
        expect(filterCommunityInterfaces(list, "yggdrasil")).toEqual([ygg]);
        expect(filterCommunityInterfaces(list, "other")).toEqual([other]);
    });

    it("returns empty when the group has no entries", () => {
        expect(filterCommunityInterfaces([tcp, i2p], "backbone")).toEqual([]);
    });

    it("tolerates a non-array list", () => {
        expect(filterCommunityInterfaces(null, "tcp")).toEqual([]);
        expect(filterCommunityInterfaces(undefined, "all")).toEqual([]);
    });
});

describe("COMMUNITY_FILTER_OPTIONS", () => {
    it("exposes every group the user can filter by", () => {
        expect(COMMUNITY_FILTER_OPTIONS.map((o) => o.id)).toEqual([
            "all",
            "tcp",
            "backbone",
            "i2p",
            "yggdrasil",
            "other",
        ]);
        for (const opt of COMMUNITY_FILTER_OPTIONS) {
            expect(opt.icon).toBeTruthy();
            expect(opt.labelKey).toMatch(/^interfaces\./);
        }
    });
});

describe("communityPresetAddress", () => {
    it("joins host and port for TCP presets", () => {
        expect(communityPresetAddress({ type: "TCPClientInterface", target_host: "rns.example", target_port: 4242 })).toBe(
            "rns.example:4242",
        );
    });

    it("uses the first i2p peer for I2P presets", () => {
        expect(
            communityPresetAddress({ type: "I2PInterface", i2p_peers: ["abc123.b32.i2p", "def456.b32.i2p"] }),
        ).toBe("abc123.b32.i2p");
    });

    it("falls back to target_host for I2P presets without peers", () => {
        expect(communityPresetAddress({ type: "I2PInterface", target_host: "node.i2p" })).toBe("node.i2p");
    });

    it("omits the port when absent", () => {
        expect(communityPresetAddress({ type: "BackboneInterface", target_host: "bb.example" })).toBe("bb.example");
    });

    it("returns empty for malformed input", () => {
        expect(communityPresetAddress(null)).toBe("");
        expect(communityPresetAddress({})).toBe("");
        expect(communityPresetAddress({ type: "I2PInterface" })).toBe("");
    });
});
