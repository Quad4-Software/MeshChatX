import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RelaySearchPage from "@/components/relay/RelaySearchPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

const HITS = [
    {
        hub_hash: "aabbccddeeff00112233445566778899",
        hub_name: "Hub One",
        room: "lobby",
        nick: "alice",
        text: "hello world",
        ts: Date.now(),
        kind: "msg",
    },
    {
        hub_hash: "ffeeddccbbaa00112233445566778899",
        hub_name: "Hub Two",
        room: "dev",
        nick: "bob",
        text: "another hit",
        ts: Date.now(),
        kind: "msg",
    },
];

function makeApi() {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/rrc/search") {
                return Promise.resolve({ data: { results: HITS } });
            }
            return Promise.resolve({ data: {} });
        }),
    };
}

const mountPage = () => mount(RelaySearchPage, { global: mountToolsPageGlobals() });

describe("RelaySearchPage.vue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    it("queries the global endpoint with the raw query string", async () => {
        const api = makeApi();
        window.api = api;
        const wrapper = mountPage();
        wrapper.vm.query = 'from:alice "hello world" -spam';
        await wrapper.vm.runSearch();
        expect(api.get).toHaveBeenCalledWith("/api/v1/rrc/search", {
            params: { q: 'from:alice "hello world" -spam', limit: 100 },
        });
        expect(wrapper.vm.results).toHaveLength(2);
    });

    it("emits open-room with hub and room when a result is clicked", async () => {
        window.api = makeApi();
        const wrapper = mountPage();
        wrapper.vm.query = "hello";
        await wrapper.vm.runSearch();
        await wrapper.vm.$nextTick();
        const hit = wrapper.findAll("button").find((b) => b.text().includes("hello world"));
        await hit.trigger("click");
        expect(wrapper.emitted("open-room")).toEqual([[{ hubHash: HITS[0].hub_hash, room: "lobby" }]]);
    });

    it("skips the network call for an empty query", async () => {
        const api = makeApi();
        window.api = api;
        const wrapper = mountPage();
        wrapper.vm.query = "   ";
        await wrapper.vm.runSearch();
        expect(api.get).not.toHaveBeenCalledWith("/api/v1/rrc/search", expect.anything());
    });

    it("ignores stale responses from superseded searches", async () => {
        const resolvers = [];
        const api = {
            get: vi.fn().mockImplementation(() => new Promise((r) => resolvers.push(r))),
        };
        window.api = api;
        const wrapper = mountPage();
        wrapper.vm.query = "first";
        const p1 = wrapper.vm.runSearch();
        wrapper.vm.query = "second";
        const p2 = wrapper.vm.runSearch();
        // Resolve the superseded request last; its payload must be dropped.
        resolvers[1]({ data: { results: [{ room: "fresh" }] } });
        resolvers[0]({ data: { results: [{ room: "stale" }] } });
        await Promise.all([p1, p2]);
        expect(wrapper.vm.results.some((r) => r.room === "stale")).toBe(false);
        expect(wrapper.vm.results.some((r) => r.room === "fresh")).toBe(true);
    });
});
