import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import IdentitiesPage from "@/components/settings/IdentitiesPage.vue";
import GlobalEmitter from "@/js/GlobalEmitter";

// Mock dependencies
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

describe("IdentitiesPage.vue", () => {
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

    const mountPage = () => {
        return mount(IdentitiesPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: '<div class="mdi"></div>' },
                    LxmfUserIcon: { template: '<div class="lxmf-user-icon"></div>' },
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });
    };

    it("shows skeleton when loading and no identities", async () => {
        axiosMock.get.mockImplementation(() => new Promise(() => {}));
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isLoading).toBe(true);
        const skeletons = wrapper.findAll('[class*="animate-pulse"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it("renders identity list correctly", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Identity 1");
        expect(wrapper.text()).toContain("Identity 2");
        expect(wrapper.vm.isLoading).toBe(false);
        const rows = wrapper.findAll(".identity-row");
        expect(rows.length).toBe(1);
    });

    it("exposes current identity with LXMF and message_count", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("a1b2c3d4e5f6");
        const current = wrapper.vm.currentIdentity;
        expect(current).toBeTruthy();
        expect(current.message_count).toBe(42);
    });

    it("shows Import and Export all when identities exist", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.currentIdentity).toBeTruthy();
        expect(wrapper.text()).toContain("identities.import");
        expect(wrapper.text()).toContain("identities.export_all");
    });

    it("opens create modal and creates identity", async () => {
        const wrapper = mountPage();
        await wrapper.find("button").trigger("click"); // New Identity button
        expect(wrapper.vm.showCreateModal).toBe(true);

        wrapper.vm.newIdentityName = "New Identity";
        await wrapper.vm.createIdentity();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/create", {
            display_name: "New Identity",
        });
        expect(wrapper.vm.showCreateModal).toBe(false);
    });

    it("switches identity", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const switchButton = wrapper.findAll("button").find((b) => b.attributes("title") === "identities.switch");
        await switchButton.trigger("click");

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
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const switchButton = wrapper.findAll("button").find((b) => b.attributes("title") === "identities.switch");
        await switchButton.trigger("click");

        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "identity-switched-apply",
            expect.objectContaining({
                identity_hash: "hash2",
                display_name: "Identity 2",
            })
        );
    });

    it("emits identity-switching-start before identity-switched-apply", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const switchButton = wrapper.findAll("button").find((b) => b.attributes("title") === "identities.switch");
        await switchButton.trigger("click");

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
            const wrapper = mountPage();
            await wrapper.vm.$nextTick();
            await wrapper.vm.$nextTick();

            const switchButton = wrapper.findAll("button").find((b) => b.attributes("title") === "identities.switch");
            await switchButton.trigger("click");

            expect(reloadFn).not.toHaveBeenCalled();
            await vi.advanceTimersByTimeAsync(2000);
            expect(reloadFn).toHaveBeenCalledTimes(1);
        } finally {
            vi.unstubAllGlobals();
            vi.useRealTimers();
        }
    });

    it("restores identity from base32 with whitespace normalization and offers switch", async () => {
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        const DialogUtils = (await import("@/js/DialogUtils")).default;
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

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        wrapper.vm.showImportModal = true;
        wrapper.vm.identityRestoreBase32 = "AB CD\n1234";
        await wrapper.vm.restoreIdentityBase32();

        expect(ToastUtils.success).toHaveBeenCalled();
        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(wrapper.vm.showImportModal).toBe(false);
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/identities");
    });

    it("rejects empty identity restore files with toast", async () => {
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        wrapper.vm.showImportModal = true;
        const empty = new File([], "identity.bin", { type: "application/octet-stream" });
        wrapper.vm.onIdentityRestoreFileChange({ target: { files: [empty], value: "x" } });
        expect(wrapper.vm.identityRestoreFile).toBeNull();
        expect(ToastUtils.error).toHaveBeenCalledWith("identities.identity_restore_empty_file");
        expect(wrapper.vm.showImportModal).toBe(true);
    });

    it("keeps import modal open and surfaces API error on file restore failure", async () => {
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        axiosMock.post.mockRejectedValue({
            response: { data: { message: "Identity file is empty" } },
        });
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        wrapper.vm.showImportModal = true;
        wrapper.vm.identityRestoreFile = new File([new Uint8Array([1, 2, 3])], "identity.bin");
        await wrapper.vm.restoreIdentityFile();
        expect(wrapper.vm.identityRestoreError).toBe("Identity file is empty");
        expect(ToastUtils.error).toHaveBeenCalledWith("Identity file is empty");
        expect(wrapper.vm.showImportModal).toBe(true);
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
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        const end = performance.now();

        const renderTime = end - start;
        console.log(`Rendered ${numIdentities} identities in ${renderTime.toFixed(2)}ms`);

        expect(wrapper.findAll(".identity-row").length).toBe(numIdentities - 1);
        expect(renderTime).toBeLessThan(2000);
    });

    it("memory: tracks growth after multiple identity list refreshes", async () => {
        const wrapper = mountPage();
        const getMemory = () => process.memoryUsage().heapUsed / (1024 * 1024);

        const initialMem = getMemory();

        for (let i = 0; i < 20; i++) {
            await wrapper.vm.getIdentities();
            await wrapper.vm.$nextTick();
        }

        const finalMem = getMemory();
        const growth = finalMem - initialMem;
        console.log(`Memory growth after 20 refreshes: ${growth.toFixed(2)}MB`);

        expect(growth).toBeLessThan(50); // Arbitrary limit for 500 identities refresh
    });
});
