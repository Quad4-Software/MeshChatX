import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChangelogModal from "@/components/ChangelogModal.vue";
import { createVuetify } from "vuetify";

const vuetify = createVuetify();

describe("ChangelogModal.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.axios = axiosMock;
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
                    "v-dialog": {
                        template: '<div class="v-dialog"><slot v-if="modelValue"></slot></div>',
                        props: ["modelValue"],
                    },
                    "v-toolbar": {
                        template: '<div class="v-toolbar"><slot></slot></div>',
                    },
                    "v-toolbar-title": {
                        template: '<div class="v-toolbar-title"><slot></slot></div>',
                    },
                    "v-spacer": {
                        template: '<div class="v-spacer"></div>',
                    },
                    "v-btn": {
                        template: '<button class="v-btn" @click="$emit(\'click\')"><slot></slot></button>',
                    },
                    "v-icon": {
                        template: '<i class="v-icon"></i>',
                    },
                    "v-chip": {
                        template: '<span class="v-chip"><slot></slot></span>',
                    },
                    "v-card": {
                        template: '<div class="v-card"><slot></slot></div>',
                    },
                    "v-card-text": {
                        template: '<div class="v-card-text"><slot></slot></div>',
                    },
                    "v-card-actions": {
                        template: '<div class="v-card-actions"><slot></slot></div>',
                    },
                    "v-divider": {
                        template: '<hr class="v-divider" />',
                    },
                    "v-checkbox": {
                        template: '<div class="v-checkbox"></div>',
                    },
                    "v-progress-circular": {
                        template: '<div class="v-progress-circular"></div>',
                    },
                },
            },
        });
    };

    it("displays logo in modal version", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: "4.2.1",
            },
        });

        const wrapper = mountChangelogModal();
        await wrapper.vm.show();
        await wrapper.vm.$nextTick();

        const img = wrapper.find("img");
        expect(img.exists()).toBe(true);
        expect(img.attributes("src")).toContain("favicon-512x512.png");
    });

    it("displays logo in page version", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: "4.2.1",
            },
        });

        const wrapper = mountChangelogModal({ isPage: true });
        // Page version calls fetchChangelog on mount
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const img = wrapper.find("img");
        expect(img.exists()).toBe(true);
        expect(img.attributes("src")).toContain("favicon-512x512.png");
    });

    it("has hover classes on close button", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                html: "<h1>Test</h1>",
                version: "4.2.1",
            },
        });

        const wrapper = mountChangelogModal();
        await wrapper.vm.show();
        await wrapper.vm.$nextTick();

        const closeBtn = wrapper.find("button.v-btn");
        expect(closeBtn.exists()).toBe(true);
        expect(closeBtn.attributes("class")).toContain("dark:hover:bg-white/10");
        expect(closeBtn.attributes("class")).toContain("hover:bg-black/5");
    });
});
