import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import SettingsPage from "@/components/settings/SettingsPage.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import ToastUtils from "@/js/ToastUtils";
import Utils from "@/js/Utils";
import GlobalState from "@/js/GlobalState";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        loading: vi.fn(),
        info: vi.fn(),
    },
}));

function mountConversationViewer(axiosMock) {
    return mount(ConversationViewer, {
        props: {
            selectedPeer: { destination_hash: "a".repeat(32), display_name: "Peer" },
            myLxmfAddressHash: "b".repeat(32),
            conversations: [],
        },
        global: {
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            mocks: { $t: (key) => key, $i18n: { locale: "en" } },
            stubs: {
                MaterialDesignIcon: true,
                AddImageButton: true,
                AddAudioButton: true,
                SendMessageButton: true,
                ConversationDropDownMenu: true,
                PaperMessageModal: true,
                AudioWaveformPlayer: true,
                LxmfUserIcon: true,
            },
        },
    });
}

describe("Stickers (ConversationViewer)", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn().mockImplementation((url, config) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                if (url === "/api/v1/stickers") {
                    return Promise.resolve({ data: { stickers: [{ id: 7, image_type: "png", name: "S" }] } });
                }
                if (url.includes("/api/v1/stickers/") && url.endsWith("/image")) {
                    return Promise.resolve({
                        data: new Blob([Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])], {
                            type: "image/png",
                        }),
                    });
                }
                if (url.includes("/lxmf-messages/attachment/") && url.includes("/image")) {
                    return Promise.resolve({ data: new ArrayBuffer(8) });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;

        GlobalState.blockedDestinations = [];
        GlobalState.config = { banished_effect_enabled: false };

        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
        window.URL.createObjectURL = vi.fn(() => "mock-url");
        vi.stubGlobal(
            "FileReader",
            vi.fn(() => ({
                readAsDataURL: vi.fn(function () {
                    this.result = "data:image/png;base64,mock";
                    this.onload?.({ target: { result: this.result } });
                }),
            }))
        );
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        WebSocketConnection.destroy();
    });

    it("loadUserStickers populates userStickers from GET /api/v1/stickers", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        await wrapper.vm.loadUserStickers();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers");
        expect(wrapper.vm.userStickers).toHaveLength(1);
        expect(wrapper.vm.userStickers[0].id).toBe(7);
    });

    it("mounted calls loadUserStickers so stickers can be listed", async () => {
        mountConversationViewer(axiosMock);
        await flushPromises();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers");
    });

    it("stickerImageUrl builds attachment URL for a sticker id", () => {
        const wrapper = mountConversationViewer(axiosMock);
        expect(wrapper.vm.stickerImageUrl(42)).toBe("/api/v1/stickers/42/image");
    });

    it("toggleStickerPicker loads stickers when opening", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        axiosMock.get.mockClear();
        wrapper.vm.isStickerPickerOpen = false;
        await wrapper.vm.toggleStickerPicker();
        expect(wrapper.vm.isStickerPickerOpen).toBe(true);
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers");
    });

    it("addStickerFromLibrary fetches image blob and attaches via onImageSelected", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const onSpy = vi.spyOn(wrapper.vm, "onImageSelected").mockImplementation(() => {});
        await wrapper.vm.addStickerFromLibrary({ id: 7, image_type: "png" });
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers/7/image", { responseType: "blob" });
        expect(onSpy).toHaveBeenCalled();
        expect(wrapper.vm.isStickerPickerOpen).toBe(false);
        onSpy.mockRestore();
    });

    it("saveMessageImageToStickers POSTs image_bytes when present on message", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const chatItem = {
            lxmf_message: {
                hash: "h1",
                fields: {
                    image: {
                        image_type: "png",
                        image_bytes: "cG5nLWRhdGE=",
                    },
                },
            },
        };
        await wrapper.vm.saveMessageImageToStickers(chatItem);
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/stickers",
            expect.objectContaining({
                image_bytes: "cG5nLWRhdGE=",
                image_type: "png",
                source_message_hash: "h1",
            })
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("saveMessageImageToStickers fetches attachment when image_bytes missing", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        vi.mocked(ToastUtils.success).mockClear();

        const chatItem = {
            lxmf_message: {
                hash: "abc123hash",
                fields: {
                    image: { image_type: "png" },
                },
            },
        };

        const b64Spy = vi.spyOn(Utils, "arrayBufferToBase64").mockReturnValue("YmFzZTY0");

        await wrapper.vm.saveMessageImageToStickers(chatItem);

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf-messages/attachment/abc123hash/image", {
            responseType: "arraybuffer",
        });
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/stickers",
            expect.objectContaining({
                image_bytes: "YmFzZTY0",
                image_type: "png",
            })
        );
        b64Spy.mockRestore();
    });

    it("saveMessageImageToStickers shows duplicate info when API returns duplicate_sticker", async () => {
        const dup = { response: { data: { error: "duplicate_sticker" } } };
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/stickers") {
                return Promise.reject(dup);
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountConversationViewer(axiosMock);
        vi.mocked(ToastUtils.info).mockClear();
        await wrapper.vm.saveMessageImageToStickers({
            lxmf_message: {
                hash: "h2",
                fields: { image: { image_type: "png", image_bytes: "QQ==" } },
            },
        });
        expect(ToastUtils.info).toHaveBeenCalledWith("stickers.duplicate");
    });

    it("onStickerPickerClickOutside closes the picker", () => {
        const wrapper = mountConversationViewer(axiosMock);
        wrapper.vm.isStickerPickerOpen = true;
        wrapper.vm.onStickerPickerClickOutside();
        expect(wrapper.vm.isStickerPickerOpen).toBe(false);
    });
});

describe("Stickers (SettingsPage)", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config")) {
                    return Promise.resolve({
                        data: {
                            config: {
                                display_name: "User",
                                identity_hash: "c".repeat(64),
                                lxmf_address_hash: "d".repeat(64),
                                theme: "dark",
                                is_transport_enabled: false,
                                backup_max_count: 5,
                                block_attachments_from_strangers: true,
                                block_all_from_strangers: false,
                                show_unknown_contact_banner: true,
                                banished_effect_enabled: false,
                                banished_text: "BANISHED",
                                banished_color: "#dc2626",
                            },
                        },
                    });
                }
                if (url === "/api/v1/stickers") {
                    return Promise.resolve({
                        data: { stickers: [{ id: 1 }, { id: 2 }, { id: 3 }] },
                    });
                }
                if (url.includes("/api/v1/telemetry/trusted-peers")) {
                    return Promise.resolve({ data: { trusted_peers: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({
                data: { imported: 2, skipped_duplicates: 1, skipped_invalid: 0 },
            }),
            patch: vi.fn().mockResolvedValue({ data: { config: {} } }),
            delete: vi.fn().mockResolvedValue({ data: { deleted: 3 } }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
        WebSocketConnection.destroy();
    });

    function mountSettings() {
        return mount(SettingsPage, {
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: { $t: (key) => key, $i18n: { locale: "en" } },
                stubs: {
                    MaterialDesignIcon: true,
                    Toggle: true,
                    ShortcutRecorder: true,
                    LxmfUserIcon: true,
                },
            },
        });
    }

    it("loadStickerCount sets stickerCount from GET /api/v1/stickers", async () => {
        const wrapper = mountSettings();
        await flushPromises();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers");
        expect(wrapper.vm.stickerCount).toBe(3);
    });

    it("exportStickers downloads JSON from GET /api/v1/stickers/export", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/config")) {
                return Promise.resolve({
                    data: {
                        config: {
                            display_name: "User",
                            identity_hash: "c".repeat(64),
                            lxmf_address_hash: "d".repeat(64),
                            theme: "dark",
                            is_transport_enabled: false,
                            backup_max_count: 5,
                            block_attachments_from_strangers: true,
                            block_all_from_strangers: false,
                            show_unknown_contact_banner: true,
                            banished_effect_enabled: false,
                            banished_text: "BANISHED",
                            banished_color: "#dc2626",
                        },
                    },
                });
            }
            if (url === "/api/v1/stickers/export") {
                return Promise.resolve({
                    data: { format: "meshchatx-stickers", version: 1, stickers: [] },
                });
            }
            if (url === "/api/v1/stickers") {
                return Promise.resolve({ data: { stickers: [] } });
            }
            if (url.includes("/api/v1/telemetry/trusted-peers")) {
                return Promise.resolve({ data: { trusted_peers: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountSettings();
        await flushPromises();
        await wrapper.vm.exportStickers();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers/export");
        expect(ToastUtils.success).toHaveBeenCalledWith("stickers.export_done");
    });

    it("importStickers posts sticker file JSON with replace_duplicates", async () => {
        const doc = {
            format: "meshchatx-stickers",
            version: 1,
            stickers: [],
        };
        class MockFileReader {
            readAsText() {
                queueMicrotask(() => {
                    this.onload({ target: { result: JSON.stringify(doc) } });
                });
            }
        }
        const OriginalFileReader = globalThis.FileReader;
        globalThis.FileReader = MockFileReader;

        try {
            const wrapper = mountSettings();
            await flushPromises();
            wrapper.vm.stickerImportReplaceDuplicates = true;

            const file = new File([JSON.stringify(doc)], "stickers.json", { type: "application/json" });
            const ev = { target: { files: [file], value: "" } };
            await wrapper.vm.importStickers(ev);
            await flushPromises();

            expect(axiosMock.post).toHaveBeenCalledWith(
                "/api/v1/stickers/import",
                expect.objectContaining({
                    format: "meshchatx-stickers",
                    version: 1,
                    replace_duplicates: true,
                })
            );
            expect(ToastUtils.success).toHaveBeenCalled();
        } finally {
            globalThis.FileReader = OriginalFileReader;
        }
    });

    it("clearStickers calls DELETE maintenance/stickers and refreshes count", async () => {
        const wrapper = mountSettings();
        await flushPromises();
        axiosMock.get.mockClear();

        await wrapper.vm.clearStickers();
        await flushPromises();

        expect(axiosMock.delete).toHaveBeenCalledWith("/api/v1/maintenance/stickers");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/stickers");
        expect(ToastUtils.success).toHaveBeenCalledWith("maintenance.stickers_cleared");
    });
});
