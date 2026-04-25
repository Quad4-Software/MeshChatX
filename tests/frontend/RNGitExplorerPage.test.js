import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createRouter, createWebHistory } from "vue-router";
import RNGitExplorerPage from "@/components/tools/RNGitExplorerPage.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("RNGitExplorerPage.vue", () => {
    let axiosMock;
    const router = createRouter({
        history: createWebHistory(),
        routes: [{ path: "/tools", name: "tools", component: { template: "div" } }],
    });

    beforeEach(() => {
        axiosMock = {
            post: vi.fn(),
            get: vi.fn().mockResolvedValue({ data: { announces: [] } }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountPage = () =>
        mount(RNGitExplorerPage, {
            global: {
                plugins: [router],
                mocks: { $t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key) },
                stubs: {
                    MaterialDesignIcon: { template: "<span />", props: ["iconName"] },
                    RouterLink: { template: "<a><slot /></a>", props: ["to"] },
                },
            },
        });

    it("posts probe with textarea names", async () => {
        axiosMock.post.mockResolvedValue({
            data: {
                ok: true,
                results: [
                    {
                        repository: "MeshChatX",
                        reachable: true,
                        refs_preview: "abc\tHEAD",
                        refs_truncated: false,
                        clone_command: "git clone rns://h/quad4/MeshChatX",
                        error: null,
                    },
                ],
            },
        });
        const wrapper = mountPage();
        await wrapper.setData({
            destinationHash: "a".repeat(32),
            groupName: "quad4",
            repoNamesText: "MeshChatX",
        });
        await wrapper.vm.runProbe();
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/rngit-tool/probe",
            expect.objectContaining({
                destination_hash: "a".repeat(32),
                group_name: "quad4",
                repository_names_text: "MeshChatX",
                for_push: false,
            })
        );
        expect(wrapper.vm.results.length).toBe(1);
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("heardNodeTitle prefers custom_display_name then display_name", () => {
        const wrapper = mountPage();
        expect(
            wrapper.vm.heardNodeTitle({
                custom_display_name: "  Mine  ",
                display_name: "Other",
                destination_hash: "a".repeat(32),
            })
        ).toBe("Mine");
        expect(
            wrapper.vm.heardNodeTitle({
                custom_display_name: "",
                display_name: "  Bob ",
                destination_hash: "b".repeat(32),
            })
        ).toBe("Bob");
    });

    it("heardNodeTitle uses short hash when display is Anonymous Peer", () => {
        const wrapper = mountPage();
        expect(
            wrapper.vm.heardNodeTitle({
                display_name: "Anonymous Peer",
                destination_hash: "926baefe13daf5178c174f158dae1b45",
            })
        ).toBe('rngit_explorer.heard_title_short:{"prefix":"926baefe"}');
    });

    it("separates for-push checkbox row from probe button", () => {
        const wrapper = mountPage();
        const row = wrapper.find(".flex.flex-col.gap-3.sm\\:flex-row");
        expect(row.exists()).toBe(true);
        expect(row.find('input[type="checkbox"]').exists()).toBe(true);
        expect(row.find("button").exists()).toBe(true);
    });
});
