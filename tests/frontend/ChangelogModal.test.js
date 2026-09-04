import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChangelogModal from "@/components/ChangelogModal.vue";
import { appPackageVersion } from "./fixtures/repoPackageVersion.js";

describe("ChangelogModal.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;
    });

    const mountChangelogModal = (props = {}) => {
        return mount(ChangelogModal, {
            props,
            global: {
                mocks: {
                    $t: (key, def) => def || key,
                    $route: {
                        meta: {
                            isPage: props.isPage || false,
                        },
                    },
                },
                stubs: {
                    AppModal: {
                        template: '<div class="app-modal"><slot name="header" /><slot /><slot name="actions" /></div>',
                        props: ["modelValue"],
                    },
                    LoadingState: {
                        template: '<div class="loading-state"></div>',
                    },
                    MaterialDesignIcon: true,
                },
            },
        });
    };

    it("displays logo in modal version", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: appPackageVersion,
            },
        });

        const wrapper = mountChangelogModal();
        await wrapper.vm.show();
        await wrapper.vm.$nextTick();

        const img = wrapper.find("img");
        expect(img.exists()).toBe(true);
        expect(img.attributes("src")).toContain("logo.png");
    });

    it("displays logo in page version", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: appPackageVersion,
            },
        });

        const wrapper = mountChangelogModal({ isPage: true });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const img = wrapper.find("img");
        expect(img.exists()).toBe(true);
        expect(img.attributes("src")).toContain("logo.png");
    });

    it("has hover classes on close button", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: appPackageVersion,
            },
        });

        const wrapper = mountChangelogModal();
        await wrapper.vm.show();
        await wrapper.vm.$nextTick();

        const closeBtn = wrapper.find("button.primary-chip");
        expect(closeBtn.exists()).toBe(true);
    });
});
