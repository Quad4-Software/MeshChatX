import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RelayBotsPage from "@/components/relay/RelayBotsPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

const RRC_BOT = {
    id: "bot1",
    name: "Uptime Bot",
    template_id: "rrc",
    running: true,
    rrc: { hub: "aabbccddeeff00112233445566778899", rooms: ["general"], nick: "upbot" },
};

function makeApi(bots = []) {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({ data: { status: { bots } } });
            }
            return Promise.resolve({ data: {} });
        }),
        post: vi.fn().mockResolvedValue({ data: { success: true } }),
        patch: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    };
}

const mountPage = (props = {}) =>
    mount(RelayBotsPage, {
        global: mountToolsPageGlobals(),
        props,
    });

describe("RelayBotsPage.vue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    it("lists only rrc-template bots", async () => {
        window.api = makeApi([RRC_BOT, { id: "b2", name: "Echo", template_id: "echo", running: false }]);
        const wrapper = mountPage();
        await wrapper.vm.fetchBots();
        expect(wrapper.vm.rrcBots.map((b) => b.id)).toEqual(["bot1"]);
    });

    it("creates a bot with normalized rooms and rrc config", async () => {
        const api = makeApi();
        window.api = api;
        const wrapper = mountPage();
        wrapper.vm.form.name = "UpBot";
        wrapper.vm.form.hubCustom = "aabbccddeeff00112233445566778899";
        wrapper.vm.form.roomsCsv = "#general,  #dev ,,";
        await wrapper.vm.createBot();
        const payload = api.post.mock.calls[0][1];
        expect(payload.template_id).toBe("rrc");
        expect(payload.rrc.rooms).toEqual(["general", "dev"]);
        expect(payload.rrc.hub).toBe("aabbccddeeff00112233445566778899");
        expect(payload.rrc.mention_only).toBe(true);
    });

    it("uses the picked known hub over the custom hash input", async () => {
        window.api = makeApi();
        const wrapper = mountPage({ knownHubs: [{ hash: "ff".repeat(16), name: "Hub" }] });
        wrapper.vm.form.hubPick = "ff".repeat(16);
        wrapper.vm.form.hubCustom = "00".repeat(16);
        expect(wrapper.vm.effectiveHubHash).toBe("ff".repeat(16));
    });

    it("requires name and hub before create is enabled", async () => {
        window.api = makeApi();
        const wrapper = mountPage();
        wrapper.vm.showCreate = true;
        await wrapper.vm.$nextTick();
        const btn = wrapper.findAll("button").find((b) => b.text().includes("Create bot"));
        expect(btn.attributes("disabled")).toBeDefined();
        wrapper.vm.form.name = "X";
        wrapper.vm.form.hubCustom = "aa".repeat(16);
        await wrapper.vm.$nextTick();
        expect(btn.attributes("disabled")).toBeUndefined();
    });

    it("stops a running bot and refreshes the list", async () => {
        const api = makeApi([RRC_BOT]);
        window.api = api;
        const wrapper = mountPage();
        await wrapper.vm.fetchBots();
        await wrapper.vm.stopBot(wrapper.vm.rrcBots[0]);
        expect(api.post).toHaveBeenCalledWith("/api/v1/bots/stop", { bot_id: "bot1" });
    });

    it("polls bot status while mounted", async () => {
        const api = makeApi([RRC_BOT]);
        window.api = api;
        mountPage();
        await vi.advanceTimersByTimeAsync(5000);
        const calls = api.get.mock.calls.filter((c) => c[0] === "/api/v1/bots/status");
        expect(calls.length).toBeGreaterThanOrEqual(2);
    });
});
