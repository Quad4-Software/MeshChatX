import { afterEach, describe, expect, it } from "vitest";
import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed } from "@/js/browserLayoutStore";

describe("browserLayoutStore sidebar collapse", () => {
    afterEach(() => {
        localStorage.clear();
    });

    it("returns null when no sidebar collapse value is stored", () => {
        expect(loadFeatureSidebarCollapsed("messages")).toBeNull();
        expect(loadFeatureSidebarCollapsed("app")).toBeNull();
        expect(loadFeatureSidebarCollapsed("nomadnetwork")).toBeNull();
        expect(loadFeatureSidebarCollapsed("relayChat")).toBeNull();
    });

    it("persists and restores sidebar collapse flags per feature", () => {
        saveFeatureSidebarCollapsed("messages", true);
        saveFeatureSidebarCollapsed("app", false);
        saveFeatureSidebarCollapsed("nomadnetwork", true);

        expect(loadFeatureSidebarCollapsed("messages")).toBe(true);
        expect(loadFeatureSidebarCollapsed("app")).toBe(false);
        expect(loadFeatureSidebarCollapsed("nomadnetwork")).toBe(true);
    });

    it("migrates legacy relay sidebar collapse storage", () => {
        localStorage.setItem("relayChatSidebarCollapsed", "1");

        expect(loadFeatureSidebarCollapsed("relayChat")).toBe(true);
    });

    it("writes legacy relay sidebar collapse storage for compatibility", () => {
        saveFeatureSidebarCollapsed("relayChat", false);

        expect(localStorage.getItem("relayChatSidebarCollapsed")).toBe("0");
        expect(loadFeatureSidebarCollapsed("relayChat")).toBe(false);
    });
});
