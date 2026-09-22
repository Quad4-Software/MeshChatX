// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import ManagementIdentityPicker from "@/features/rnpath/components/ManagementIdentityPicker.svelte";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        prompt: vi.fn(),
        confirm: vi.fn(),
        alert: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("ManagementIdentityPicker", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({ data: { identities: [] } }),
            post: vi.fn().mockResolvedValue({
                data: { identity: { path: "/tmp/mgmt", name: "mgmt", hash: "abcd1234ffff" } },
            }),
        };
        window.api = axiosMock;
        DialogUtils.prompt.mockReset();
        ToastUtils.success.mockReset();
        ToastUtils.error.mockReset();
    });

    afterEach(() => {
        delete window.api;
    });

    it("asks for a name with the in-app prompt instead of window.prompt", async () => {
        DialogUtils.prompt.mockResolvedValue("ops");
        const { container } = render(ManagementIdentityPicker, {
            props: { defaultName: "mgmt" },
        });

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        const buttons = container.querySelectorAll("button");
        const createBtn = buttons[1];
        await fireEvent.click(createBtn);

        await waitFor(() => {
            expect(DialogUtils.prompt).toHaveBeenCalledWith("Name for the new management identity file", "mgmt");
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/management-identities", { name: "ops" });
        });
    });

    it("does not create an identity when the prompt is cancelled", async () => {
        DialogUtils.prompt.mockResolvedValue(null);
        const { container } = render(ManagementIdentityPicker, {
            props: { defaultName: "mgmt" },
        });

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        const buttons = container.querySelectorAll("button");
        const createBtn = buttons[1];
        await fireEvent.click(createBtn);

        await waitFor(() => {
            expect(DialogUtils.prompt).toHaveBeenCalled();
            expect(axiosMock.post).not.toHaveBeenCalled();
        });
    });
});
