// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { useRNodeInterfaceForm } from "../../meshchatx/src/frontend/js/interfaces/useRNodeInterfaceForm.js";

describe("useRNodeInterfaceForm", () => {
    it("computes frequency in Hz from GHz/MHz/kHz parts", () => {
        const form = useRNodeInterfaceForm();
        form.RNodeGHzValue.value = 0;
        form.RNodeMHzValue.value = 868;
        form.RNodekHzValue.value = 100;
        expect(form.calculateFrequencyInHz()).toBe(868100000);
    });

    it("formats frequency across units", () => {
        const form = useRNodeInterfaceForm();
        form.RNodeGHzValue.value = 2;
        form.RNodeMHzValue.value = 400;
        form.RNodekHzValue.value = 0;
        expect(form.formattedFrequency.value).toBe("2.400 GHz");
        form.RNodeGHzValue.value = 0;
        expect(form.formattedFrequency.value).toBe("400.000 MHz");
        form.RNodeMHzValue.value = 0;
        form.RNodekHzValue.value = 500;
        expect(form.formattedFrequency.value).toBe("500.000 kHz");
        form.RNodekHzValue.value = 0;
        expect(form.formattedFrequency.value).toBe("0 Hz");
    });

    it("builds a tcp port string from the RNode IP host", () => {
        const form = useRNodeInterfaceForm();
        form.newInterfaceRNodeIPHost.value = "10.0.0.1:";
        expect(form.buildRNodeTcpPort()).toBe("tcp://10.0.0.1");
        form.newInterfaceRNodeIPHost.value = "  ";
        expect(form.buildRNodeTcpPort()).toBe("");
    });

    it("parses tcp host back out of a port string", () => {
        const form = useRNodeInterfaceForm();
        expect(form.parseRnodeTcpHostFromPort("/dev/ttyUSB0")).toBe("localhost");
        expect(form.parseRnodeTcpHostFromPort("tcp://radio.local:7633")).toBe("radio.local");
        expect(form.parseRnodeTcpHostFromPort("tcp://[fd00::1]:7633")).toBe("[fd00::1]");
        expect(form.parseRnodeTcpHostFromPort("tcp://10.0.0.2")).toBe("10.0.0.2");
        expect(form.parseRnodeTcpHostFromPort("tcp://:")).toBe("");
    });

    it("derives the effective ble port with scheme prefix", () => {
        const form = useRNodeInterfaceForm();
        expect(form.effectiveRNodeBlePort()).toBe("ble://");
        form.newInterfaceRNodeBlePeer.value = "AA:BB:CC:DD:EE:FF";
        expect(form.effectiveRNodeBlePort()).toBe("ble://AA:BB:CC:DD:EE:FF");
        form.newInterfaceRNodeBlePeer.value = "ble://aa:bb";
        expect(form.effectiveRNodeBlePort()).toBe("ble://aa:bb");
    });

    it("transport toggles are mutually exclusive", () => {
        const form = useRNodeInterfaceForm();
        form.setRNodeTransportIp(true);
        expect(form.newInterfaceRNodeUseIP.value).toBe(true);
        expect(form.newInterfaceRNodeUseBle.value).toBe(false);
        form.setRNodeTransportBle(true);
        expect(form.newInterfaceRNodeUseBle.value).toBe(true);
        expect(form.newInterfaceRNodeUseIP.value).toBe(false);
        form.setRNodeTransportBle(false);
        expect(form.newInterfaceRNodeUseBle.value).toBe(false);
    });

    it("recalculates LoRa parameters when watched fields change", async () => {
        const form = useRNodeInterfaceForm();
        form.newInterfaceBandwidth.value = 250000;
        await nextTick();
        expect(form.RNodeInterfaceLoRaParameters.dataRate).toMatch(/bps|kbps/);
        expect(form.RNodeInterfaceLoRaParameters.linkBudget).toMatch(/dB$/);
        expect(form.RNodeInterfaceLoRaParameters.sensitivity).toMatch(/dBm$/);
        form.RNodeInterfaceLoRaParameters.antennaGain = 3;
        await nextTick();
        expect(form.RNodeInterfaceLoRaParameters.linkBudget).not.toBeNull();
    });

    it("calculateRNodeParameters derives data rate, sensitivity, and link budget", () => {
        const form = useRNodeInterfaceForm();
        form.calculateRNodeParameters(125000, 7, 5, 5, 0, 7);
        expect(form.RNodeInterfaceLoRaParameters.dataRate).toBe("5.47 kbps");
        expect(form.RNodeInterfaceLoRaParameters.sensitivity).toBe("-125.5 dBm");
        expect(form.RNodeInterfaceLoRaParameters.linkBudget).toBe("132.5 dB");
    });

    it("calculateRNodeParameters is a no-op without required params", () => {
        const form = useRNodeInterfaceForm();
        form.calculateRNodeParameters(null, 7, 5, 5, 0, 7);
        expect(form.RNodeInterfaceLoRaParameters.dataRate).toBeNull();
        expect(form.RNodeInterfaceLoRaParameters.linkBudget).toBeNull();
        expect(form.RNodeInterfaceLoRaParameters.sensitivity).toBeNull();
    });

    it("uses the wide-bandwidth sensitivity formula above 500 kHz", () => {
        const form = useRNodeInterfaceForm();
        form.calculateRNodeParameters(1625000, 7, 5, 5, 0, 7);
        // -165.6 + 10*log10(1625000) + 5 - 7.5 = -106.0
        expect(form.RNodeInterfaceLoRaParameters.sensitivity).toBe("-106.0 dBm");
    });

    it("adds and removes RNode multi sub-interfaces", () => {
        const form = useRNodeInterfaceForm();
        form.addSubInterface();
        form.addSubInterface();
        expect(form.RNodeMultiInterface.subInterfaces).toHaveLength(2);
        expect(form.RNodeMultiInterface.subInterfaces[0]).toEqual({
            name: "",
            frequency: null,
            bandwidth: null,
            txpower: null,
            spreadingfactor: null,
            codingrate: null,
            vport: null,
        });
        form.removeSubInterface(0);
        expect(form.RNodeMultiInterface.subInterfaces).toHaveLength(1);
    });

    it("exposes the RNode defaults used by the form selects", () => {
        const form = useRNodeInterfaceForm();
        expect(form.RNodeInterfaceDefaults.bandwidths).toContain(125000);
        expect(form.RNodeInterfaceDefaults.spreadingfactors).toEqual([5, 6, 7, 8, 9, 10, 11, 12]);
        expect(form.RNodeInterfaceDefaults.codingrates).toEqual([5, 6, 7, 8]);
        expect(form.RNodeInterfaceDefaults.txpowerMin).toBe(0);
        expect(form.RNodeInterfaceDefaults.txpowerMax).toBe(37);
    });
});
