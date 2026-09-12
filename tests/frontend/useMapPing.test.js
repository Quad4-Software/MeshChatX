// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useMapPing } from "../../meshchatx/src/frontend/js/map/useMapPing.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("useMapPing", () => {
    beforeEach(() => {
        window.api = {
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    it("openPingModalAt sets the target and opens the modal", () => {
        const ping = useMapPing();
        ping.pingDestinationHash.value = "abc";
        ping.openPingModalAt(52.5, 13.4, 12.6);
        expect(ping.mapPingLat.value).toBe(52.5);
        expect(ping.mapPingLon.value).toBe(13.4);
        expect(ping.mapPingZoom.value).toBe(12.6);
        expect(ping.pingDestinationHash.value).toBe("");
        expect(ping.showMapPingModal.value).toBe(true);
    });

    it("mapPingSummary formats lat lon and rounded zoom", () => {
        const ping = useMapPing();
        ping.openPingModalAt(1.23456789, 2.34567891, 12.6);
        expect(ping.mapPingSummary.value).toBe("1.234568, 2.345679 @ z13");
    });

    it("sendMapPing rejects an empty destination hash", async () => {
        const t = vi.fn((key) => key);
        const ping = useMapPing({ t });
        await ping.sendMapPing();
        expect(window.api.post).not.toHaveBeenCalled();
        expect(t).toHaveBeenCalledWith("map.ping_invalid_destination");
        expect(ToastUtils.error).toHaveBeenCalledWith("map.ping_invalid_destination");
    });

    it("sendMapPing rejects a destination hash of the wrong length", async () => {
        const ping = useMapPing();
        ping.pingDestinationHash.value = "tooshort";
        await ping.sendMapPing();
        expect(window.api.post).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalledWith("map.ping_invalid_destination");
    });

    it("sendMapPing posts a meshchat map uri and closes the modal", async () => {
        const t = vi.fn((key) => key);
        const ping = useMapPing({ t, getLayers: () => "discovered" });
        ping.openPingModalAt(52.5, 13.4, 11);
        ping.pingDestinationHash.value = "a".repeat(32);

        await ping.sendMapPing();

        expect(window.api.post).toHaveBeenCalledTimes(1);
        const [path, body] = window.api.post.mock.calls[0];
        expect(path).toContain("/lxmf-messages/send");
        expect(body.lxmf_message.destination_hash).toBe("a".repeat(32));
        expect(body.lxmf_message.content).toContain("map.ping_message_prefix");
        expect(body.lxmf_message.content).toContain("meshchatx://map?");
        expect(body.lxmf_message.content).toContain("lat=52.5");
        expect(body.lxmf_message.content).toContain("lon=13.4");
        expect(body.lxmf_message.content).toContain("z=11");
        expect(body.lxmf_message.content).toContain("layers=discovered");
        expect(body.lxmf_message.content).toContain("label=Ping");
        expect(ToastUtils.success).toHaveBeenCalledWith("map.ping_sent");
        expect(ping.showMapPingModal.value).toBe(false);
    });

    it("sendMapPing keeps the modal open when the request fails", async () => {
        window.api.post = vi.fn().mockRejectedValue(new Error("boom"));
        const ping = useMapPing({ t: (key) => key });
        ping.openPingModalAt(52.5, 13.4, 11);
        ping.pingDestinationHash.value = "b".repeat(32);

        await ping.sendMapPing();

        expect(ToastUtils.error).toHaveBeenCalledWith("map.ping_failed");
        expect(ping.showMapPingModal.value).toBe(true);
    });
});
