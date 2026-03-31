import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("compressorjs", () => ({
    default: vi.fn(function (file, options) {
        options.success(file);
    }),
}));

import CallPage from "@/components/call/CallPage.vue";

describe("CallPage.vue - Custom Contact Images", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
            delete: vi.fn(),
        };
        window.api = axiosMock;

        // Mock FileReader
        const mockFileReader = {
            readAsDataURL: vi.fn(function (blob) {
                this.result = "data:image/webp;base64,mock";
                this.onload({ target: { result: this.result } });
            }),
        };
        vi.stubGlobal(
            "FileReader",
            vi.fn(function () {
                return mockFileReader;
            })
        );

        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/telephone/contacts")) return Promise.resolve({ data: [] });
            if (url.includes("/api/v1/telephone/status")) return Promise.resolve({ data: { enabled: true } });
            if (url.includes("/api/v1/telephone/voicemail/status")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        vi.resetAllMocks();
    });

    const mountCallPage = () => {
        return mount(CallPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                    Toggle: true,
                    RingtoneEditor: true,
                },
            },
        });
    };

    it("opens add contact modal and handles image upload", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        // Switch to contacts tab
        wrapper.vm.activeTab = "contacts";
        await wrapper.vm.$nextTick();

        // Open add contact modal
        await wrapper.vm.openAddContactModal();
        expect(wrapper.vm.isContactModalOpen).toBe(true);
        expect(wrapper.vm.contactForm.custom_image).toBeNull();

        // Simulate image selection
        const imageFile = new File([""], "profile.png", { type: "image/png" });
        await wrapper.vm.onContactImageChange({ target: { files: [imageFile], value: "" } });

        expect(wrapper.vm.contactForm.custom_image).toBe("data:image/webp;base64,mock");
    });

    it("saves contact with custom image", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.contactForm = {
            name: "New Contact",
            remote_identity_hash: "hash123",
            custom_image: "data:image/webp;base64,mock",
        };

        axiosMock.post.mockResolvedValue({ data: { message: "Contact added" } });

        await wrapper.vm.saveContact(wrapper.vm.contactForm);

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/telephone/contacts",
            expect.objectContaining({
                name: "New Contact",
                custom_image: "data:image/webp;base64,mock",
            })
        );
    });

    it("clears image when editing a contact", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        const contact = {
            id: 1,
            name: "Existing Contact",
            remote_identity_hash: "hash123",
            custom_image: "existing-img",
        };

        await wrapper.vm.openEditContactModal(contact);
        expect(wrapper.vm.contactForm.custom_image).toBe("existing-img");

        // Clear image
        wrapper.vm.contactForm.custom_image = null;

        axiosMock.patch.mockResolvedValue({ data: { message: "Contact updated" } });

        await wrapper.vm.saveContact(wrapper.vm.contactForm);

        expect(axiosMock.patch).toHaveBeenCalledWith(
            "/api/v1/telephone/contacts/1",
            expect.objectContaining({
                clear_image: true,
            })
        );
    });
});
