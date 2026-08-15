import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import ManagementIdentityPicker from "@/components/tools/ManagementIdentityPicker.vue";

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
        const wrapper = mount(ManagementIdentityPicker, {
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>", props: ["iconName"] },
                },
            },
        });
        await flushPromises();
        const createBtn = wrapper.findAll("button").at(1);
        await createBtn.trigger("click");
        await flushPromises();
        expect(DialogUtils.prompt).toHaveBeenCalledWith("remote_mgmt.create_identity_prompt", "mgmt");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/management-identities", { name: "ops" });
        wrapper.unmount();
    });

    it("does not create an identity when the prompt is cancelled", async () => {
        DialogUtils.prompt.mockResolvedValue(null);
        const wrapper = mount(ManagementIdentityPicker, {
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>", props: ["iconName"] },
                },
            },
        });
        await flushPromises();
        const createBtn = wrapper.findAll("button").at(1);
        await createBtn.trigger("click");
        await flushPromises();
        expect(axiosMock.post).not.toHaveBeenCalled();
        wrapper.unmount();
    });
});
