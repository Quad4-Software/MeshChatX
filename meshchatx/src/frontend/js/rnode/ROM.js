import RNodeUtils from "./RNodeUtils.js";

export default class ROM {
    static PLATFORM_AVR = 0x90;
    static PLATFORM_ESP32 = 0x80;
    static PLATFORM_NRF52 = 0x70;

    static MCU_1284P = 0x91;
    static MCU_2560 = 0x92;
    static MCU_ESP32 = 0x81;
    static MCU_NRF52 = 0x71;

    static PRODUCT_RAK4631 = 0x10;
    static MODEL_11 = 0x11;
    static MODEL_12 = 0x12;

    static PRODUCT_RNODE = 0x03;
    static MODEL_A1 = 0xa1;
    static MODEL_A6 = 0xa6;
    static MODEL_A4 = 0xa4;
    static MODEL_A9 = 0xa9;
    static MODEL_A3 = 0xa3;
    static MODEL_A8 = 0xa8;
    static MODEL_A2 = 0xa2;
    static MODEL_A7 = 0xa7;
    static MODEL_A5 = 0xa5;
    static MODEL_AA = 0xaa;
    static MODEL_AC = 0xac;

    static PRODUCT_T32_10 = 0xb2;
    static MODEL_BA = 0xba;
    static MODEL_BB = 0xbb;

    static PRODUCT_T32_20 = 0xb0;
    static MODEL_B3 = 0xb3;
    static MODEL_B8 = 0xb8;

    static PRODUCT_T32_21 = 0xb1;
    static MODEL_B4 = 0xb4;
    static MODEL_B9 = 0xb9;
    static MODEL_B4_TCXO = 0x04;
    static MODEL_B9_TCXO = 0x09;

    static PRODUCT_H32_V2 = 0xc0;
    static MODEL_C4 = 0xc4;
    static MODEL_C9 = 0xc9;

    static PRODUCT_H32_V3 = 0xc1;
    static MODEL_C5 = 0xc5;
    static MODEL_CA = 0xca;

    static PRODUCT_HELTEC_T114 = 0xc2;
    static MODEL_C6 = 0xc6;
    static MODEL_C7 = 0xc7;

    static PRODUCT_TBEAM = 0xe0;
    static MODEL_E4 = 0xe4;
    static MODEL_E9 = 0xe9;
    static MODEL_E3 = 0xe3;
    static MODEL_E8 = 0xe8;

    static PRODUCT_TBEAM_S_V1 = 0xea;
    static MODEL_DB = 0xdb;
    static MODEL_DC = 0xdc;

    static PRODUCT_TDECK = 0xd0;
    static MODEL_D4 = 0xd4;
    static MODEL_D9 = 0xd9;

    static PRODUCT_TECHO = 0x15;
    static MODEL_16 = 0x16;
    static MODEL_17 = 0x17;

    static PRODUCT_HMBRW = 0xf0;
    static MODEL_FF = 0xff;
    static MODEL_FE = 0xfe;

    static ADDR_PRODUCT = 0x00;
    static ADDR_MODEL = 0x01;
    static ADDR_HW_REV = 0x02;
    static ADDR_SERIAL = 0x03;
    static ADDR_MADE = 0x07;
    static ADDR_CHKSUM = 0x0b;
    static ADDR_SIGNATURE = 0x1b;
    static ADDR_INFO_LOCK = 0x9b;
    static ADDR_CONF_SF = 0x9c;
    static ADDR_CONF_CR = 0x9d;
    static ADDR_CONF_TXP = 0x9e;
    static ADDR_CONF_BW = 0x9f;
    static ADDR_CONF_FREQ = 0xa3;
    static ADDR_CONF_OK = 0xa7;

    static INFO_LOCK_BYTE = 0x73;
    static CONF_OK_BYTE = 0x73;

    static BOARD_RNODE = 0x31;
    static BOARD_HMBRW = 0x32;
    static BOARD_TBEAM = 0x33;
    static BOARD_HUZZAH32 = 0x34;
    static BOARD_GENERIC_ESP32 = 0x35;
    static BOARD_LORA32_V2_0 = 0x36;
    static BOARD_LORA32_V2_1 = 0x37;
    static BOARD_RAK4631 = 0x51;

    static MANUAL_FLASH_MODELS = [ROM.MODEL_A1, ROM.MODEL_A6];

    constructor(eeprom) {
        this.eeprom = eeprom;
    }

    getProduct() {
        return this.eeprom[ROM.ADDR_PRODUCT];
    }

    getModel() {
        return this.eeprom[ROM.ADDR_MODEL];
    }

    getHardwareRevision() {
        return this.eeprom[ROM.ADDR_HW_REV];
    }

    getSerialNumber() {
        return [
            this.eeprom[ROM.ADDR_SERIAL],
            this.eeprom[ROM.ADDR_SERIAL + 1],
            this.eeprom[ROM.ADDR_SERIAL + 2],
            this.eeprom[ROM.ADDR_SERIAL + 3],
        ];
    }

    getMade() {
        return [
            this.eeprom[ROM.ADDR_MADE],
            this.eeprom[ROM.ADDR_MADE + 1],
            this.eeprom[ROM.ADDR_MADE + 2],
            this.eeprom[ROM.ADDR_MADE + 3],
        ];
    }

    getChecksum() {
        const checksum = [];
        for (var i = 0; i < 16; i++) {
            checksum.push(this.eeprom[ROM.ADDR_CHKSUM + i]);
        }
        return checksum;
    }

    getSignature() {
        const signature = [];
        for (var i = 0; i < 128; i++) {
            signature.push(this.eeprom[ROM.ADDR_SIGNATURE + i]);
        }
        return signature;
    }

    getCalculatedChecksum() {
        return RNodeUtils.md5([
            this.getProduct(),
            this.getModel(),
            this.getHardwareRevision(),
            ...this.getSerialNumber(),
            ...this.getMade(),
        ]);
    }

    getConfiguredSpreadingFactor() {
        return this.eeprom[ROM.ADDR_CONF_SF];
    }

    getConfiguredCodingRate() {
        return this.eeprom[ROM.ADDR_CONF_CR];
    }

    getConfiguredTxPower() {
        return this.eeprom[ROM.ADDR_CONF_TXP];
    }

    getConfiguredFrequency() {
        return (
            (this.eeprom[ROM.ADDR_CONF_FREQ] << 24) |
            (this.eeprom[ROM.ADDR_CONF_FREQ + 1] << 16) |
            (this.eeprom[ROM.ADDR_CONF_FREQ + 2] << 8) |
            this.eeprom[ROM.ADDR_CONF_FREQ + 3]
        );
    }

    getConfiguredBandwidth() {
        return (
            (this.eeprom[ROM.ADDR_CONF_BW] << 24) |
            (this.eeprom[ROM.ADDR_CONF_BW + 1] << 16) |
            (this.eeprom[ROM.ADDR_CONF_BW + 2] << 8) |
            this.eeprom[ROM.ADDR_CONF_BW + 3]
        );
    }

    isInfoLocked() {
        return this.eeprom[ROM.ADDR_INFO_LOCK] === ROM.INFO_LOCK_BYTE;
    }

    isConfigured() {
        return this.eeprom[ROM.ADDR_CONF_OK] === ROM.CONF_OK_BYTE;
    }

    parse() {
        if (!this.isInfoLocked()) {
            return null;
        }

        const checksumHex = RNodeUtils.bytesToHex(this.getChecksum());
        const calculatedChecksumHex = RNodeUtils.bytesToHex(this.getCalculatedChecksum());
        const signatureHex = RNodeUtils.bytesToHex(this.getSignature());

        var details = {
            is_provisioned: true,
            is_configured: this.isConfigured(),
            product: this.getProduct(),
            model: this.getModel(),
            hardware_revision: this.getHardwareRevision(),
            serial_number: RNodeUtils.unpackUInt32BE(this.getSerialNumber()),
            made: RNodeUtils.unpackUInt32BE(this.getMade()),
            checksum: checksumHex,
            calculated_checksum: calculatedChecksumHex,
            signature: signatureHex,
        };

        if (details.is_configured) {
            details = {
                ...details,
                configured_spreading_factor: this.getConfiguredSpreadingFactor(),
                configured_coding_rate: this.getConfiguredCodingRate(),
                configured_tx_power: this.getConfiguredTxPower(),
                configured_frequency: this.getConfiguredFrequency(),
                configured_bandwidth: this.getConfiguredBandwidth(),
            };
        }

        if (details.checksum !== details.calculated_checksum) {
            details.is_provisioned = false;
        }

        return details;
    }
}
