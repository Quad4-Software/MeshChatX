// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi } from "vitest";
import {
    applyRelayShareLink,
    buildMeshchatRelayUri,
    buildRelayShareMessage,
    findRelayUriInContent,
    parseMeshchatRelayUri,
} from "@/js/relayLinkUtils.js";

const HUB = "00112233445566778899aabbccddeeff";

describe("relayLinkUtils", () => {
    it("builds and parses meshchatx relay URIs", () => {
        const uri = buildMeshchatRelayUri({
            hub: HUB,
            room: "lobby",
            name: "Test Hub",
            aspect: "custom.hub",
        });
        expect(uri.startsWith("meshchatx://relay?")).toBe(true);
        const p = parseMeshchatRelayUri(uri);
        expect(p).not.toBeNull();
        expect(p.hub).toBe(HUB);
        expect(p.room).toBe("lobby");
        expect(p.name).toBe("Test Hub");
        expect(p.aspect).toBe("custom.hub");
    });

    it("accepts meshchat:// alias and defaults aspect", () => {
        const p = parseMeshchatRelayUri(`meshchat://relay?hub=${HUB}`);
        expect(p).not.toBeNull();
        expect(p.aspect).toBe("rrc.hub");
        expect(p.room).toBe("");
    });

    it("rejects invalid hub hashes", () => {
        expect(parseMeshchatRelayUri("meshchatx://relay?hub=short")).toBeNull();
        expect(buildMeshchatRelayUri({ hub: "nope" })).toBeNull();
    });

    it("finds first relay URI in text", () => {
        const text = `See meshchatx://relay?hub=${HUB}&room=general end`;
        expect(findRelayUriInContent(text)).toBe(`meshchatx://relay?hub=${HUB}&room=general`);
    });

    it("builds share message text", () => {
        expect(buildRelayShareMessage({ hub: HUB })).toBe(`MeshChatX relay: meshchatx://relay?hub=${HUB}`);
        expect(buildRelayShareMessage({ hub: HUB, room: "lobby" })).toBe(
            `MeshChatX relay room: meshchatx://relay?hub=${HUB}&room=lobby`
        );
    });

    it("applyRelayShareLink adds hub and joins room", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { hubs: [] } }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        const result = await applyRelayShareLink({ hub: HUB, room: "lobby", name: "N", aspect: "rrc.hub" }, { api });
        expect(api.post).toHaveBeenCalledWith("/api/v1/rrc/hubs", {
            hub_hash: HUB,
            name: "N",
            dest_name: "rrc.hub",
            connect: true,
        });
        expect(api.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB}/rooms`, { room: "lobby" });
        expect(result).toEqual({ hub_hash: HUB, room: "lobby" });
    });

    it("applyRelayShareLink reconnects existing disconnected hub", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({
                data: { hubs: [{ hub_hash: HUB, connected: false }] },
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        await applyRelayShareLink({ hub: HUB, room: "", name: "", aspect: "rrc.hub" }, { api });
        expect(api.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB}/connect`);
        expect(api.post).not.toHaveBeenCalledWith("/api/v1/rrc/hubs", expect.anything());
    });
});
