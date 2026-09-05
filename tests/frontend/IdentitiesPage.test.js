// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import IdentitiesPage from "@/features/settings/components/IdentitiesPage.svelte";
import GlobalEmitter from "@/js/GlobalEmitter";
import ToastUtils from "@/js/ToastUtils";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

describe("IdentitiesPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/identities") {
                    return Promise.resolve({
                        data: {
                            identities: [
                                {
                                    hash: "hash1",
                                    display_name: "Identity 1",
                                    is_current: true,
                                    lxmf_address: "a1b2c3d4e5f6",
                                    message_count: 42,
                                },
                                {
                                    hash: "hash2",
                                    display_name: "Identity 2",
                                    is_current: false,
                                    lxmf_address: null,
                                },
                            ],
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({
                data: {
                    hotswapped: true,
                    identity_hash: "hash2",
                    display_name: "Identity 2",
                },
            }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("shows skeleton when loading and no identities", async () => {
        axiosMock.get.mockImplementation(() => new Promise(() => {}));
        const { container } = render(IdentitiesPage);
        const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it("renders identity list correctly", async () => {
        const { container, findByText } = render(IdentitiesPage);
        await findByText("Identity 1");

        expect(container.textContent).toContain("Identity 1");
        expect(container.textContent).toContain("Identity 2");
        const rows = container.querySelectorAll(".identity-row");
        expect(rows.length).toBe(1);
    });

    it("exposes current identity with LXMF and message_count", async () => {
        const { findByText } = render(IdentitiesPage);
        await findByText("a1b2c3d4e5f6");
        await findByText("42 messages");
    });

    it("shows Import and Export all when identities exist", async () => {
        const { findByText } = render(IdentitiesPage);
        await findByText("Import");
        await findByText("Backup all");
    });

    it("opens create modal and creates identity", async () => {
        const { findByText, container } = render(IdentitiesPage);
        const newBtn = await findByText("New Identity");
        await fireEvent.click(newBtn);

        const input = container.querySelector("#new-identity-name-input");
        await fireEvent.input(input, { target: { value: "New Identity" } });
        const createBtn = await findByText("Add");
        await fireEvent.click(createBtn);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/create", {
            display_name: "New Identity",
        });
    });

    it("switches identity", async () => {
        const { findByTitle } = render(IdentitiesPage);
        const switchBtn = await findByTitle("Switch to this identity");
        await fireEvent.click(switchBtn);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/switch", {
            identity_hash: "hash2",
        });
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "identity-switched-apply",
            expect.objectContaining({
                identity_hash: "hash2",
                display_name: "Identity 2",
            })
        );
    });

    it("emits identity-switched-apply using list row when API omits hash fields (legacy server)", async () => {
        axiosMock.post.mockResolvedValue({ data: { hotswapped: true } });
        const { findByTitle } = render(IdentitiesPage);
        const switchBtn = await findByTitle("Switch to this identity");
        await fireEvent.click(switchBtn);

        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "identity-switched-apply",
            expect.objectContaining({
                identity_hash: "hash2",
                display_name: "Identity 2",
            })
        );
    });

    it("emits identity-switching-start before identity-switched-apply", async () => {
        const { findByTitle } = render(IdentitiesPage);
        const switchBtn = await findByTitle("Switch to this identity");
        await fireEvent.click(switchBtn);

        const names = GlobalEmitter.emit.mock.calls.map((c) => c[0]);
        const startAt = names.indexOf("identity-switching-start");
        const applyAt = names.indexOf("identity-switched-apply");
        expect(startAt).toBeGreaterThanOrEqual(0);
        expect(applyAt).toBeGreaterThanOrEqual(0);
        expect(startAt).toBeLessThan(applyAt);
    });

    it("schedules window.location.reload when hotswap is not used", async () => {
        const reloadFn = vi.fn();
        vi.stubGlobal("location", { ...window.location, reload: reloadFn });
        axiosMock.post.mockResolvedValue({
            data: { hotswapped: false, should_restart: true },
        });
        vi.useFakeTimers();
        try {
            const { findByTitle } = render(IdentitiesPage);
            const switchBtn = await findByTitle("Switch to this identity");
            await fireEvent.click(switchBtn);

            expect(reloadFn).not.toHaveBeenCalled();
            await vi.advanceTimersByTimeAsync(2000);
            expect(reloadFn).toHaveBeenCalledTimes(1);
        } finally {
            vi.unstubAllGlobals();
            vi.useRealTimers();
        }
    });

    it("restores identity from base32 with whitespace normalization and offers switch", async () => {
        DialogUtils.confirm.mockResolvedValue(false);
        axiosMock.post.mockImplementation((url, body) => {
            if (url === "/api/v1/identity/restore") {
                expect(body).toEqual({ base32: "ABCD1234" });
                return Promise.resolve({
                    data: {
                        message: "Identity restored. Restart app to use the new identity.",
                        identity: { hash: "restored_hash", display_name: "Restored" },
                    },
                });
            }
            return Promise.resolve({ data: { hotswapped: true } });
        });

        const { findByText, container } = render(IdentitiesPage);
        const importBtn = await findByText("Import");
        await fireEvent.click(importBtn);

        const base32Input = container.querySelector("#identity-restore-b32");
        await fireEvent.input(base32Input, { target: { value: "AB CD\n1234" } });
        const restoreBtn = await findByText("Confirm restore");
        await fireEvent.click(restoreBtn);

        await waitFor(() => {
            expect(ToastUtils.success).toHaveBeenCalled();
            expect(DialogUtils.confirm).toHaveBeenCalled();
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/identities");
        });
    });

    it("rejects empty identity restore files with toast", async () => {
        const { findByText, container } = render(IdentitiesPage);
        const importBtn = await findByText("Import");
        await fireEvent.click(importBtn);

        const fileInput = container.querySelector('input[type="file"]');
        const empty = new File([], "identity.bin", { type: "application/octet-stream" });
        await fireEvent.change(fileInput, { target: { files: [empty] } });

        expect(ToastUtils.error).toHaveBeenCalledWith("Identity file is empty.");
    });

    it("keeps import modal open and surfaces API error on file restore failure", async () => {
        axiosMock.post.mockRejectedValue({
            response: { data: { message: "Identity file is empty" } },
        });
        const { findByText, container } = render(IdentitiesPage);
        const importBtn = await findByText("Import");
        await fireEvent.click(importBtn);

        const fileInput = container.querySelector('input[type="file"]');
        const file = new File([new Uint8Array([1, 2, 3])], "identity.bin");
        await fireEvent.change(fileInput, { target: { files: [file] } });

        await waitFor(() => {
            expect(ToastUtils.error).toHaveBeenCalledWith("Identity file is empty");
        });
    });

    it("performance: measures identity list rendering for many identities", async () => {
        const numIdentities = 500;
        const identities = Array.from({ length: numIdentities }, (_, i) => ({
            hash: `hash${i}`,
            display_name: `Identity ${i}`,
            is_current: i === 0,
        }));

        axiosMock.get.mockResolvedValue({ data: { identities } });

        const start = performance.now();
        const { container, findByText } = render(IdentitiesPage);
        await findByText("Identity 0");
        const end = performance.now();

        const renderTime = end - start;
        expect(container.querySelectorAll(".identity-row").length).toBe(numIdentities - 1);
        expect(renderTime).toBeLessThan(2000);
    });
});
