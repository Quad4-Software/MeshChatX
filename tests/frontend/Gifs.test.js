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

describe("Gifs (ConversationViewer)", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                if (url === "/api/v1/stickers") {
                    return Promise.resolve({ data: { stickers: [] } });
                }
                if (url === "/api/v1/gifs") {
                    return Promise.resolve({
                        data: {
                            gifs: [
                                { id: 11, image_type: "gif", name: "G1", usage_count: 3 },
                                { id: 22, image_type: "webp", name: "G2", usage_count: 0 },
                            ],
                        },
                    });
                }
                if (url.includes("/api/v1/gifs/") && url.endsWith("/image")) {
                    return Promise.resolve({
                        data: new Blob([Uint8Array.from([0x47, 0x49, 0x46, 0x38, 0x39, 0x61])], {
                            type: "image/gif",
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
                    this.result = "data:image/gif;base64,mock";
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

    it("loadUserGifs populates userGifs from GET /api/v1/gifs", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        await wrapper.vm.loadUserGifs();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs");
        expect(wrapper.vm.userGifs).toHaveLength(2);
        expect(wrapper.vm.userGifs[0].id).toBe(11);
        expect(wrapper.vm.userGifs[0].usage_count).toBe(3);
    });

    it("gifImageUrl builds attachment URL for a gif id", () => {
        const wrapper = mountConversationViewer(axiosMock);
        expect(wrapper.vm.gifImageUrl(42)).toBe("/api/v1/gifs/42/image");
    });

    it("onGifsTabSelected switches the picker tab and loads gifs", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        axiosMock.get.mockClear();
        await wrapper.vm.onGifsTabSelected();
        expect(wrapper.vm.emojiStickerTab).toBe("gifs");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs");
    });

    it("addGifFromLibrary fetches blob, attaches, and posts /use to record usage", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        await wrapper.vm.loadUserGifs();
        const onSpy = vi.spyOn(wrapper.vm, "onImageSelected").mockImplementation(() => {});
        await wrapper.vm.addGifFromLibrary({ id: 11, image_type: "gif", usage_count: 3 });
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs/11/image", { responseType: "blob" });
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/gifs/11/use");
        expect(onSpy).toHaveBeenCalled();
        expect(wrapper.vm.isStickerPickerOpen).toBe(false);
        const updated = wrapper.vm.userGifs.find((g) => g.id === 11);
        expect(updated.usage_count).toBe(4);
        onSpy.mockRestore();
    });

    it("uploadGifFiles posts gif content with image_bytes and refreshes list", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const file = new File([new Uint8Array([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x00, 0x00])], "x.gif", {
            type: "image/gif",
        });
        const b64Spy = vi.spyOn(Utils, "arrayBufferToBase64").mockReturnValue("R0lGODlhAA==");
        await wrapper.vm.uploadGifFiles([file]);
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/gifs",
            expect.objectContaining({ image_type: "gif", image_bytes: "R0lGODlhAA==" })
        );
        expect(ToastUtils.success).toHaveBeenCalledWith("gifs.uploaded_count");
        b64Spy.mockRestore();
    });

    it("uploadGifFiles rejects oversize files", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const big = new File([new Uint8Array(6 * 1024 * 1024)], "x.gif", { type: "image/gif" });
        await wrapper.vm.uploadGifFiles([big]);
        expect(ToastUtils.error).toHaveBeenCalledWith("gifs.file_too_large");
        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/gifs", expect.anything());
    });

    it("uploadGifFiles rejects non-gif/webp files", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const png = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "x.png", { type: "image/png" });
        await wrapper.vm.uploadGifFiles([png]);
        expect(ToastUtils.error).toHaveBeenCalledWith("gifs.unsupported_type");
    });

    it("canSaveMessageImageAsGif only matches gif/webp images", () => {
        const wrapper = mountConversationViewer(axiosMock);
        expect(
            wrapper.vm.canSaveMessageImageAsGif({
                lxmf_message: { fields: { image: { image_type: "gif" } } },
            })
        ).toBe(true);
        expect(
            wrapper.vm.canSaveMessageImageAsGif({
                lxmf_message: { fields: { image: { image_type: "image/webp" } } },
            })
        ).toBe(true);
        expect(
            wrapper.vm.canSaveMessageImageAsGif({
                lxmf_message: { fields: { image: { image_type: "png" } } },
            })
        ).toBe(false);
        expect(wrapper.vm.canSaveMessageImageAsGif({ lxmf_message: { fields: {} } })).toBe(false);
        expect(wrapper.vm.canSaveMessageImageAsGif(null)).toBe(false);
    });

    it("saveMessageImageToGifs POSTs image_bytes when present on message", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const chatItem = {
            lxmf_message: {
                hash: "h1",
                fields: { image: { image_type: "gif", image_bytes: "R0lGODlh" } },
            },
        };
        await wrapper.vm.saveMessageImageToGifs(chatItem);
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/gifs",
            expect.objectContaining({
                image_bytes: "R0lGODlh",
                image_type: "gif",
                source_message_hash: "h1",
            })
        );
        expect(ToastUtils.success).toHaveBeenCalledWith("gifs.saved");
    });

    it("saveMessageImageToGifs fetches attachment when image_bytes missing", async () => {
        const wrapper = mountConversationViewer(axiosMock);
        const chatItem = {
            lxmf_message: { hash: "abc", fields: { image: { image_type: "gif" } } },
        };
        const b64Spy = vi.spyOn(Utils, "arrayBufferToBase64").mockReturnValue("R0lGODlh");
        await wrapper.vm.saveMessageImageToGifs(chatItem);
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf-messages/attachment/abc/image", {
            responseType: "arraybuffer",
        });
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/gifs",
            expect.objectContaining({ image_bytes: "R0lGODlh", image_type: "gif" })
        );
        b64Spy.mockRestore();
    });

    it("saveMessageImageToGifs shows duplicate info when API returns duplicate_gif", async () => {
        const dup = { response: { data: { error: "duplicate_gif" } } };
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/gifs") return Promise.reject(dup);
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountConversationViewer(axiosMock);
        await wrapper.vm.saveMessageImageToGifs({
            lxmf_message: {
                hash: "h2",
                fields: { image: { image_type: "gif", image_bytes: "QQ==" } },
            },
        });
        expect(ToastUtils.info).toHaveBeenCalledWith("gifs.duplicate");
    });

    it("onStickerPickerClickOutside also resets gif drop state", () => {
        const wrapper = mountConversationViewer(axiosMock);
        wrapper.vm.gifDropActive = true;
        wrapper.vm.onStickerPickerClickOutside();
        expect(wrapper.vm.gifDropActive).toBe(false);
    });
});

describe("Gifs (SettingsPage)", () => {
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
                    return Promise.resolve({ data: { stickers: [] } });
                }
                if (url === "/api/v1/gifs") {
                    return Promise.resolve({ data: { gifs: [{ id: 1 }, { id: 2 }] } });
                }
                if (url.includes("/api/v1/telemetry/trusted-peers")) {
                    return Promise.resolve({ data: { trusted_peers: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({
                data: { imported: 4, skipped_duplicates: 1, skipped_invalid: 0 },
            }),
            patch: vi.fn().mockResolvedValue({ data: { config: {} } }),
            delete: vi.fn().mockResolvedValue({ data: { deleted: 2 } }),
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

    it("loadGifCount sets gifCount from GET /api/v1/gifs", async () => {
        const wrapper = mountSettings();
        await flushPromises();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs");
        expect(wrapper.vm.gifCount).toBe(2);
    });

    it("exportGifs downloads JSON from GET /api/v1/gifs/export", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/config")) {
                return Promise.resolve({
                    data: {
                        config: {
                            display_name: "U",
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
            if (url === "/api/v1/gifs/export") {
                return Promise.resolve({
                    data: { format: "meshchatx-gifs", version: 1, gifs: [] },
                });
            }
            if (url === "/api/v1/gifs") return Promise.resolve({ data: { gifs: [] } });
            if (url === "/api/v1/stickers") return Promise.resolve({ data: { stickers: [] } });
            if (url.includes("/api/v1/telemetry/trusted-peers")) {
                return Promise.resolve({ data: { trusted_peers: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountSettings();
        await flushPromises();
        await wrapper.vm.exportGifs();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs/export");
        expect(ToastUtils.success).toHaveBeenCalledWith("gifs.export_done");
    });

    it("importGifs posts JSON with replace_duplicates", async () => {
        const doc = { format: "meshchatx-gifs", version: 1, gifs: [] };
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
            wrapper.vm.gifImportReplaceDuplicates = true;
            const file = new File([JSON.stringify(doc)], "gifs.json", { type: "application/json" });
            const ev = { target: { files: [file], value: "" } };
            await wrapper.vm.importGifs(ev);
            await flushPromises();
            expect(axiosMock.post).toHaveBeenCalledWith(
                "/api/v1/gifs/import",
                expect.objectContaining({ format: "meshchatx-gifs", version: 1, replace_duplicates: true })
            );
            expect(ToastUtils.success).toHaveBeenCalled();
        } finally {
            globalThis.FileReader = OriginalFileReader;
        }
    });

    it("clearGifs calls DELETE maintenance/gifs and refreshes count", async () => {
        const wrapper = mountSettings();
        await flushPromises();
        axiosMock.get.mockClear();
        await wrapper.vm.clearGifs();
        await flushPromises();
        expect(axiosMock.delete).toHaveBeenCalledWith("/api/v1/maintenance/gifs");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/gifs");
        expect(ToastUtils.success).toHaveBeenCalledWith("maintenance.gifs_cleared");
    });
});
