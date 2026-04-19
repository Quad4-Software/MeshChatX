import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";

const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
};
window.api = mockAxios;

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const mountPage = () =>
    mount(AddInterfacePage, {
        global: {
            mocks: {
                $route: { query: {} },
                $router: { push: vi.fn() },
                $t: (msg) => msg,
            },
            stubs: ["RouterLink", "MaterialDesignIcon", "Toggle", "ExpandingSection", "FormLabel", "FormSubLabel"],
        },
    });

describe("AddInterfacePage.vue interface options", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockResolvedValue({ data: {} });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    it("sends AutoInterface group/discovery/data port settings", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "AutoLAN";
        wrapper.vm.newInterfaceType = "AutoInterface";
        wrapper.vm.newInterfaceGroupID = "homelab";
        wrapper.vm.newInterfaceDiscoveryScope = "site";
        wrapper.vm.newInterfaceDiscoveryPort = 35000;
        wrapper.vm.newInterfaceDataPort = 35001;
        wrapper.vm.newInterfaceMulticastAddressType = "permanent";
        wrapper.vm.newInterfaceDevices = "eth0,wlan0";
        wrapper.vm.newInterfaceIgnoredDevices = "tun0";
        wrapper.vm.newInterfaceConfiguredBitrate = 5000000;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                type: "AutoInterface",
                group_id: "homelab",
                discovery_scope: "site",
                discovery_port: 35000,
                data_port: 35001,
                multicast_address_type: "permanent",
                devices: "eth0,wlan0",
                ignored_devices: "tun0",
                configured_bitrate: 5000000,
            })
        );
    });

    it("sends TCP client advanced options (kiss/i2p/timeout/mtu)", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "TCPC";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = 4242;
        wrapper.vm.newInterfaceKISSFramingEnabled = true;
        wrapper.vm.newInterfaceI2PTunnelingEnabled = true;
        wrapper.vm.newInterfaceConnectTimeout = 12;
        wrapper.vm.newInterfaceMaxReconnectTries = 7;
        wrapper.vm.newInterfaceFixedMTU = 480;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                kiss_framing: true,
                i2p_tunneled: true,
                connect_timeout: 12,
                max_reconnect_tries: 7,
                fixed_mtu: 480,
            })
        );
    });

    it("sends TCP server device/prefer_ipv6/i2p_tunneled options", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "TCPS";
        wrapper.vm.newInterfaceType = "TCPServerInterface";
        wrapper.vm.newInterfaceListenIp = "0.0.0.0";
        wrapper.vm.newInterfaceListenPort = 4242;
        wrapper.vm.newInterfaceNetworkDevice = "eth0";
        wrapper.vm.newInterfacePreferIPV6 = true;
        wrapper.vm.newInterfaceI2PTunnelingEnabled = true;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                device: "eth0",
                prefer_ipv6: true,
                i2p_tunneled: true,
            })
        );
    });

    it("sends BackboneInterface listener payload when listener mode is on", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "Backbone";
        wrapper.vm.newInterfaceType = "BackboneInterface";
        wrapper.vm.newInterfaceBackboneListenMode = true;
        wrapper.vm.newInterfaceBackboneListenIp = "0.0.0.0";
        wrapper.vm.newInterfaceBackboneListenPort = 5151;
        wrapper.vm.newInterfaceBackboneListenDevice = "eth1";
        wrapper.vm.newInterfacePreferIPV6 = true;
        wrapper.vm.newInterfaceTargetHost = "leaked.example";
        wrapper.vm.newInterfaceTargetPort = 9999;

        await wrapper.vm.saveInterface();

        const payload = mockAxios.post.mock.calls[0][1];
        expect(payload.listen_ip).toBe("0.0.0.0");
        expect(payload.listen_port).toBe(5151);
        expect(payload.device).toBe("eth1");
        expect(payload.prefer_ipv6).toBe(true);
        expect(payload.target_host).toBe(null);
        expect(payload.target_port).toBe(null);
    });

    it("sends RNode flow_control + id_callsign + id_interval", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "Radio";
        wrapper.vm.newInterfaceType = "RNodeInterface";
        wrapper.vm.newInterfacePort = "/dev/ttyUSB0";
        wrapper.vm.RNodeMHzValue = 868;
        wrapper.vm.newInterfaceBandwidth = 125000;
        wrapper.vm.newInterfaceTxpower = 7;
        wrapper.vm.newInterfaceSpreadingFactor = 8;
        wrapper.vm.newInterfaceCodingRate = 5;
        wrapper.vm.newInterfaceFlowControl = true;
        wrapper.vm.newInterfaceIDCallsign = "NOCALL";
        wrapper.vm.newInterfaceIDInterval = 600;
        wrapper.vm.newInterfaceAirtimeLimitLong = 1.5;
        wrapper.vm.newInterfaceAirtimeLimitShort = 33.0;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                flow_control: true,
                id_callsign: "NOCALL",
                id_interval: 600,
                airtime_limit_long: 1.5,
                airtime_limit_short: 33.0,
            })
        );
    });

    it("sends KISS serial + framing options", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "KISS";
        wrapper.vm.newInterfaceType = "KISSInterface";
        wrapper.vm.newInterfacePort = "/dev/ttyACM0";
        wrapper.vm.newInterfaceSpeed = 19200;
        wrapper.vm.newInterfaceDatabits = 8;
        wrapper.vm.newInterfaceParity = "N";
        wrapper.vm.newInterfaceStopbits = 1;
        wrapper.vm.newInterfacePreamble = 200;
        wrapper.vm.newInterfaceTXTail = 30;
        wrapper.vm.newInterfacePersistence = 128;
        wrapper.vm.newInterfaceSlotTime = 25;
        wrapper.vm.newInterfaceFlowControl = true;
        wrapper.vm.newInterfaceIDCallsign = "BEACON";
        wrapper.vm.newInterfaceIDInterval = 1200;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                speed: 19200,
                databits: 8,
                parity: "N",
                stopbits: 1,
                preamble: 200,
                txtail: 30,
                persistence: 128,
                slottime: 25,
                flow_control: true,
                id_callsign: "BEACON",
                id_interval: 1200,
            })
        );
    });

    it("sends AX25KISS callsign + ssid", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "AX25";
        wrapper.vm.newInterfaceType = "AX25KISSInterface";
        wrapper.vm.newInterfacePort = "/dev/ttyACM1";
        wrapper.vm.newInterfaceCallsign = "N0CALL";
        wrapper.vm.newInterfaceSSID = 7;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                callsign: "N0CALL",
                ssid: 7,
            })
        );
    });

    it("sends I2P connectable=false when peer disables it", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "I2P";
        wrapper.vm.newInterfaceType = "I2PInterface";
        wrapper.vm.I2PSettings.newInterfacePeers = ["abcdef.b32.i2p"];
        wrapper.vm.newInterfaceConnectable = false;

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                type: "I2PInterface",
                peers: ["abcdef.b32.i2p"],
                connectable: false,
            })
        );
    });

    it("surfaces backend port-in-use errors to the user", async () => {
        const wrapper = mountPage();
        const ToastUtils = (await import("../../meshchatx/src/frontend/js/ToastUtils")).default;

        mockAxios.post.mockRejectedValueOnce({
            response: {
                status: 409,
                data: { message: "The TCP port 4242 on 0.0.0.0 is already in use" },
            },
        });

        wrapper.vm.newInterfaceName = "TCPS";
        wrapper.vm.newInterfaceType = "TCPServerInterface";
        wrapper.vm.newInterfaceListenIp = "0.0.0.0";
        wrapper.vm.newInterfaceListenPort = 4242;

        await wrapper.vm.saveInterface();

        expect(ToastUtils.error).toHaveBeenCalledWith(expect.stringContaining("already in use"));
    });
});
