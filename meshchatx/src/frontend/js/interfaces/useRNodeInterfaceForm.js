// @ts-check

import { computed, reactive, ref, watch } from "vue";

/**
 * RNode interface form state for AddInterfacePage: transport selection
 * (serial / TCP / BLE), GHz/MHz/kHz frequency fields, LoRa radio
 * parameters with derived link-budget calculations, and the
 * RNodeMultiInterface sub-interface list.
 *
 * The bandwidth / spreading-factor / coding-rate / txpower refs and the
 * antenna-gain field are watched so the derived LoRa parameters stay in
 * sync, matching the previous Options API watchers on the host.
 */
export function useRNodeInterfaceForm() {
    const RNodeMultiInterface = reactive({
        port: null,
        subInterfaces: [],
    });

    const newInterfaceRNodeUseIP = ref(false);
    const newInterfaceRNodeUseBle = ref(false);
    const newInterfaceRNodeBlePeer = ref("");
    const newInterfaceRNodeIPHost = ref("");

    const RNodeGHzValue = ref(0);
    const RNodeMHzValue = ref(0);
    const RNodekHzValue = ref(0);
    const newInterfaceFrequency = ref(null);
    const newInterfaceBandwidth = ref(125000);
    const newInterfaceTxpower = ref(7);
    const newInterfaceSpreadingFactor = ref(12);
    const newInterfaceCodingRate = ref(5);

    const RNodeInterfaceDefaults = reactive({
        // bandwidth in hz
        bandwidths: [
            7800, // 7.8 kHz
            10400, // 10.4 kHz
            15600, // 15.6 kHz
            20800, // 20.8 kHz
            31250, // 31.25 kHz
            41700, // 41.7 kHz
            62500, // 62.5 kHz
            125000, // 125 kHz
            250000, // 250 kHz
            500000, // 500 kHz
            1625000, // 1625 kHz (for 2.4 GHz SX1280)
        ],
        codingrates: [
            5, // 4:5
            6, // 4:6
            7, // 4:7
            8, // 4:8
        ],
        spreadingfactors: [5, 6, 7, 8, 9, 10, 11, 12],
        txpowerMin: 0,
        txpowerMax: 37,
    });

    const RNodeInterfaceLoRaParameters = reactive({
        antennaGain: 0,
        noiseFloor: 5,
        sensitivity: null,
        dataRate: null,
        linkBudget: null,
    });

    function calculateFrequencyInHz() {
        return Math.round(RNodeGHzValue.value * 1e9 + RNodeMHzValue.value * 1e6 + RNodekHzValue.value * 1e3);
    }

    const formattedFrequency = computed(() => {
        const totalHz = Math.round(calculateFrequencyInHz());
        if (totalHz >= 1e9) {
            return `${(totalHz / 1e9).toFixed(3)} GHz`;
        } else if (totalHz >= 1e6) {
            return `${(totalHz / 1e6).toFixed(3)} MHz`;
        } else if (totalHz >= 1e3) {
            return `${(totalHz / 1e3).toFixed(3)} kHz`;
        }
        return `${totalHz} Hz`;
    });

    function buildRNodeTcpPort() {
        let h = String(newInterfaceRNodeIPHost.value ?? "").trim();
        while (h.endsWith(":")) {
            h = h.slice(0, -1);
        }
        if (!h) {
            return "";
        }
        return `tcp://${h}`;
    }

    function parseRnodeTcpHostFromPort(portStr) {
        const s = String(portStr || "");
        if (!s.startsWith("tcp://")) {
            return "localhost";
        }
        let rest = s.slice(6);
        while (rest.endsWith(":")) {
            rest = rest.slice(0, -1);
        }
        if (!rest) {
            return "";
        }
        if (rest.startsWith("[")) {
            const close = rest.indexOf("]");
            if (close !== -1 && rest[close + 1] === ":") {
                return rest.slice(0, close + 1);
            }
            return rest;
        }
        if (rest.includes(":") && rest.indexOf(":") === rest.lastIndexOf(":")) {
            const idx = rest.indexOf(":");
            const tail = rest.slice(idx + 1);
            if (/^\d{1,5}$/.test(tail) && Number(tail) <= 65535) {
                return rest.slice(0, idx);
            }
        }
        return rest;
    }

    function effectiveRNodeBlePort() {
        let p = (newInterfaceRNodeBlePeer.value || "").trim();
        if (!p) {
            return "ble://";
        }
        if (p.toLowerCase().startsWith("ble://")) {
            return p;
        }
        return `ble://${p}`;
    }

    function setRNodeTransportIp(v) {
        newInterfaceRNodeUseIP.value = Boolean(v);
        if (newInterfaceRNodeUseIP.value) {
            newInterfaceRNodeUseBle.value = false;
        }
    }

    function setRNodeTransportBle(v) {
        newInterfaceRNodeUseBle.value = Boolean(v);
        if (newInterfaceRNodeUseBle.value) {
            newInterfaceRNodeUseIP.value = false;
        }
    }

    function updateRNodeCalculations() {
        calculateRNodeParameters(
            newInterfaceBandwidth.value,
            newInterfaceSpreadingFactor.value,
            newInterfaceCodingRate.value,
            RNodeInterfaceLoRaParameters.noiseFloor,
            RNodeInterfaceLoRaParameters.antennaGain,
            newInterfaceTxpower.value
        );
    }

    function calculateRNodeParameters(bandwidth, spreadingFactor, codingRate, noiseFloor, antennaGain, transmitPower) {
        if (!bandwidth || !spreadingFactor || !codingRate) return;
        const crn = { 5: 1, 6: 2, 7: 3, 8: 4 };
        const cr = crn[codingRate];
        const sfn = { 5: -2.5, 6: -5, 7: -7.5, 8: -10, 9: -12.5, 10: -15, 11: -17.5, 12: -20 };
        let dataRate = spreadingFactor * (4 / (4 + cr) / (Math.pow(2, spreadingFactor) / (bandwidth / 1000))) * 1000;
        let sensitivity = -174 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
        if (bandwidth === 203125 || bandwidth === 406250 || bandwidth > 500000) {
            sensitivity = -165.6 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
        }
        let linkBudget = transmitPower - sensitivity + antennaGain;
        RNodeInterfaceLoRaParameters.dataRate =
            dataRate < 1000 ? `${dataRate.toFixed(0)} bps` : `${(dataRate / 1000).toFixed(2)} kbps`;
        RNodeInterfaceLoRaParameters.linkBudget = `${linkBudget.toFixed(1)} dB`;
        RNodeInterfaceLoRaParameters.sensitivity = `${sensitivity.toFixed(1)} dBm`;
    }

    watch(newInterfaceBandwidth, updateRNodeCalculations);
    watch(newInterfaceSpreadingFactor, updateRNodeCalculations);
    watch(newInterfaceCodingRate, updateRNodeCalculations);
    watch(newInterfaceTxpower, updateRNodeCalculations);
    watch(() => RNodeInterfaceLoRaParameters.antennaGain, updateRNodeCalculations);

    function addSubInterface() {
        RNodeMultiInterface.subInterfaces.push({
            name: "",
            frequency: null,
            bandwidth: null,
            txpower: null,
            spreadingfactor: null,
            codingrate: null,
            vport: null,
        });
    }

    function removeSubInterface(idx) {
        RNodeMultiInterface.subInterfaces.splice(idx, 1);
    }

    return {
        RNodeMultiInterface,
        newInterfaceRNodeUseIP,
        newInterfaceRNodeUseBle,
        newInterfaceRNodeBlePeer,
        newInterfaceRNodeIPHost,
        RNodeGHzValue,
        RNodeMHzValue,
        RNodekHzValue,
        newInterfaceFrequency,
        newInterfaceBandwidth,
        newInterfaceTxpower,
        newInterfaceSpreadingFactor,
        newInterfaceCodingRate,
        RNodeInterfaceDefaults,
        RNodeInterfaceLoRaParameters,
        formattedFrequency,
        calculateFrequencyInHz,
        buildRNodeTcpPort,
        parseRnodeTcpHostFromPort,
        effectiveRNodeBlePort,
        setRNodeTransportIp,
        setRNodeTransportBle,
        updateRNodeCalculations,
        calculateRNodeParameters,
        addSubInterface,
        removeSubInterface,
    };
}
