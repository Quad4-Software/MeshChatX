// SPDX-License-Identifier: 0BSD

/**
 * Live PageOutlet: stableKey conversation switches must update props without
 * effect_update_depth_exceeded, and leaving messages must swap the host.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount } from "svelte";
import { clearRoutes, registerRoute } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import { navigate, resetForTests, start } from "../../meshchatx/src/frontend/shell/hashRouter.js";
import PageOutlet from "../../meshchatx/src/frontend/shell/PageOutlet.svelte";

async function waitFor(predicate, timeoutMs = 2000) {
    const startAt = Date.now();
    while (Date.now() - startAt < timeoutMs) {
        if (await predicate()) {
            return;
        }
        await new Promise((resolve) => setTimeout(resolve, 20));
    }
    throw new Error("waitFor timeout");
}

describe("PageOutlet stableKey navigation", () => {
    let host;
    let app;
    let pageErrors;
    let onError;

    beforeEach(async () => {
        clearRoutes();
        resetForTests();
        pageErrors = [];
        onError = (event) => {
            pageErrors.push(String(event?.reason || event?.error || event?.message || event));
        };
        window.addEventListener("error", onError);
        window.addEventListener("unhandledrejection", onError);
        host = document.createElement("div");
        document.body.appendChild(host);

        const messagesMod = await import("./fixtures/StableKeyMessagesStub.svelte");
        const contactsMod = await import("./fixtures/ContactsStub.svelte");

        registerRoute({
            name: "messages",
            path: "/messages/:destinationHash?",
            mount: "svelte",
            load: async () => messagesMod,
            meta: { stableKey: true },
        });
        registerRoute({
            name: "contacts",
            path: "/contacts",
            mount: "svelte",
            load: async () => contactsMod,
        });

        window.location.hash = "#/messages";
        start();
        app = mount(PageOutlet, { target: host });
        await waitFor(() => host.querySelector("[data-testid='messages-stub']"));
    });

    afterEach(() => {
        window.removeEventListener("error", onError);
        window.removeEventListener("unhandledrejection", onError);
        if (app) {
            try {
                unmount(app);
            } catch {
                /* already gone */
            }
        }
        host?.remove();
        resetForTests();
        clearRoutes();
    });

    it("updates conversation props then navigates away without effect depth errors", async () => {
        await navigate({ name: "messages", params: { destinationHash: "aabbccddeeff0011" } });
        await waitFor(() => {
            const el = host.querySelector("[data-testid='messages-stub']");
            return el && el.getAttribute("data-hash") === "aabbccddeeff0011";
        });

        // Second conversation switch (same stableKey, syncProps path).
        await navigate({ name: "messages", params: { destinationHash: "1122334455667788" } });
        await waitFor(() => {
            const el = host.querySelector("[data-testid='messages-stub']");
            return el && el.getAttribute("data-hash") === "1122334455667788";
        });

        await navigate({ name: "contacts" });
        await waitFor(() => host.querySelector("[data-testid='contacts-stub']"));

        expect(host.querySelector("[data-testid='contacts-stub']")).toBeTruthy();
        expect(host.textContent).toContain("ContactsStub");
        expect(pageErrors.join("\n")).not.toMatch(/effect_update_depth_exceeded/);
    });
});
