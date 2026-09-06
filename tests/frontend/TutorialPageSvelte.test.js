// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import TutorialPage from "../../meshchatx/src/frontend/features/tutorial/TutorialPage.svelte";
import TutorialModalHost from "../../meshchatx/src/frontend/features/tutorial/components/TutorialModalHost.svelte";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState.js";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: { confirm: vi.fn().mockResolvedValue(true) },
}));
vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

const GET_RESPONSES = {
    "/api/v1/identities": { identities: [{ hash: "old-hash", is_current: true }] },
    "/api/v1/config": { config: { display_name: "Old Name", theme: "light" } },
    "/api/v1/community-interfaces": { interfaces: [] },
    "/api/v1/reticulum/discovered-interfaces": { interfaces: [] },
    "/api/v1/reticulum/discovery": { discovery: { default_bootstrap_only: false } },
    "/api/v1/app/info": { app_info: {} },
};

function makeApi() {
    return {
        get: vi.fn((url) => Promise.resolve({ data: GET_RESPONSES[url] ?? {} })),
        post: vi.fn((url) => {
            if (url === "/api/v1/identity/restore") {
                return Promise.resolve({ data: { identity: { hash: "imported-hash" } } });
            }
            if (url === "/api/v1/identities/switch") {
                return Promise.resolve({ data: { hotswapped: true, identity_hash: "imported-hash" } });
            }
            return Promise.resolve({ data: {} });
        }),
        patch: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    };
}

/** Walk from the identity step to the finish step through the manual path. */
async function advanceToFinish(getByText) {
    await fireEvent.click(getByText("tutorial.mode_manual_title"));
    await waitFor(() => getByText("tutorial.propagation_skip_auto"));
    await fireEvent.click(getByText("tutorial.propagation_skip_auto"));
    await waitFor(() => getByText("tutorial.finish_setup"));
}

describe("TutorialPage (Svelte)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(null);
        GlobalState.hasPendingInterfaceChanges = false;
        window.api = makeApi();
    });

    afterEach(() => {
        cleanup();
    });

    it("opens on the welcome step and loads setup defaults", async () => {
        const { getByText } = render(TutorialPage);
        await waitFor(() => {
            expect(getByText("tutorial.welcome_desc")).toBeTruthy();
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/identities");
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/community-interfaces");
        });
    });

    it("renames the current identity when continuing in new identity mode", async () => {
        const { getByText } = render(TutorialPage);
        await waitFor(() => getByText("tutorial.continue"));

        await fireEvent.click(getByText("tutorial.continue"));
        await waitFor(() => getByText("tutorial.identity_title"));

        await fireEvent.click(getByText("tutorial.continue"));
        await waitFor(() => {
            expect(window.api.patch).toHaveBeenCalledWith("/api/v1/config", { display_name: "Old Name" });
            expect(getByText("tutorial.connect")).toBeTruthy();
        });
        expect(window.api.post).not.toHaveBeenCalledWith(
            "/api/v1/identity/restore",
            expect.anything(),
            expect.anything()
        );
    });

    it("restores an identity key on continue and defers activation to finish", async () => {
        const { getByText, getByPlaceholderText } = render(TutorialPage);
        await waitFor(() => getByText("tutorial.continue"));
        await fireEvent.click(getByText("tutorial.continue"));
        await waitFor(() => getByText("tutorial.identity_import"));

        await fireEvent.click(getByText("tutorial.identity_import"));
        const base32Input = await waitFor(() => getByPlaceholderText("tutorial.identity_base32_placeholder"));
        await fireEvent.input(base32Input, { target: { value: "AAAA BBBB" } });

        await fireEvent.click(getByText("tutorial.continue"));
        await waitFor(() => {
            expect(window.api.post).toHaveBeenCalledWith("/api/v1/identity/restore", {
                base32: "AAAABBBB",
                display_name: "Old Name",
            });
        });
        // Restore imports the key. Switching identities waits for Finish.
        expect(window.api.post).not.toHaveBeenCalledWith("/api/v1/identities/switch", expect.anything());

        await waitFor(() => getByText("tutorial.connect"));
        await advanceToFinish(getByText);
        await fireEvent.click(getByText("tutorial.finish_setup"));

        await waitFor(() => {
            expect(window.api.post).toHaveBeenCalledWith("/api/v1/identities/switch", {
                identity_hash: "imported-hash",
            });
            expect(window.api.delete).toHaveBeenCalledWith("/api/v1/identities/old-hash");
            expect(window.api.post).toHaveBeenCalledWith("/api/v1/app/tutorial/seen");
        });
    });

    it("opens the shell modal through the show surface the app shell binds to", async () => {
        const { component, getByText, queryByText } = render(TutorialModalHost);
        expect(queryByText("tutorial.welcome_desc")).toBeNull();
        expect(component.isOpen()).toBe(false);

        component.show();
        await waitFor(() => {
            expect(getByText("tutorial.welcome_desc")).toBeTruthy();
            expect(component.isOpen()).toBe(true);
        });
        // The modal footer uses the short labels, the page uses the long ones.
        expect(getByText("tutorial.next")).toBeTruthy();

        component.hide();
        await waitFor(() => {
            expect(component.isOpen()).toBe(false);
            expect(window.api.post).toHaveBeenCalledWith("/api/v1/app/tutorial/seen");
        });
    });

    it("keeps the file picker on identity key material only", async () => {
        const { container, getByText } = render(TutorialPage);
        await waitFor(() => getByText("tutorial.continue"));
        await fireEvent.click(getByText("tutorial.continue"));

        const fileInput = await waitFor(() => container.querySelector('input[type="file"]'));
        expect(fileInput.getAttribute("accept")).toBe(".bin,.key,.identity,application/octet-stream,*/*");
    });
});
