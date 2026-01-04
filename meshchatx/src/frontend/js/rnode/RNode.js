import RNodeUtils from "./RNodeUtils.js";
import ROM from "./ROM.js";

export default class RNode {
    KISS_FEND = 0xc0;
    KISS_FESC = 0xdb;
    KISS_TFEND = 0xdc;
    KISS_TFESC = 0xdd;

    CMD_FREQUENCY = 0x01;
    CMD_BANDWIDTH = 0x02;
    CMD_TXPOWER = 0x03;
    CMD_SF = 0x04;
    CMD_CR = 0x05;
    CMD_RADIO_STATE = 0x06;

    CMD_STAT_RX = 0x21;
    CMD_STAT_TX = 0x22;
    CMD_STAT_RSSI = 0x23;
    CMD_STAT_SNR = 0x24;

    CMD_BOARD = 0x47;
    CMD_PLATFORM = 0x48;
    CMD_MCU = 0x49;
    CMD_RESET = 0x55;
    CMD_RESET_BYTE = 0xf8;
    CMD_DEV_HASH = 0x56;
    CMD_FW_VERSION = 0x50;
    CMD_ROM_READ = 0x51;
    CMD_ROM_WRITE = 0x52;
    CMD_CONF_SAVE = 0x53;
    CMD_CONF_DELETE = 0x54;
    CMD_FW_HASH = 0x58;
    CMD_UNLOCK_ROM = 0x59;
    ROM_UNLOCK_BYTE = 0xf8;
    CMD_HASHES = 0x60;
    CMD_FW_UPD = 0x61;
    CMD_DISP_ROT = 0x67;
    CMD_DISP_RCND = 0x68;

    CMD_BT_CTRL = 0x46;
    CMD_BT_PIN = 0x62;

    CMD_DISP_READ = 0x66;

    CMD_DETECT = 0x08;
    DETECT_REQ = 0x73;
    DETECT_RESP = 0x46;

    RADIO_STATE_OFF = 0x00;
    RADIO_STATE_ON = 0x01;
    RADIO_STATE_ASK = 0xff;

    CMD_ERROR = 0x90;
    ERROR_INITRADIO = 0x01;
    ERROR_TXFAILED = 0x02;
    ERROR_EEPROM_LOCKED = 0x03;

    PLATFORM_AVR = 0x90;
    PLATFORM_ESP32 = 0x80;
    PLATFORM_NRF52 = 0x70;

    MCU_1284P = 0x91;
    MCU_2560 = 0x92;
    MCU_ESP32 = 0x81;
    MCU_NRF52 = 0x71;

    BOARD_RNODE = 0x31;
    BOARD_HMBRW = 0x32;
    BOARD_TBEAM = 0x33;
    BOARD_HUZZAH32 = 0x34;
    BOARD_GENERIC_ESP32 = 0x35;
    BOARD_LORA32_V2_0 = 0x36;
    BOARD_LORA32_V2_1 = 0x37;
    BOARD_RAK4631 = 0x51;

    HASH_TYPE_TARGET_FIRMWARE = 0x01;
    HASH_TYPE_FIRMWARE = 0x02;

    constructor(serialPort) {
        this.serialPort = serialPort;
        this.reader = serialPort.readable.getReader();
        this.writable = serialPort.writable;
        this.callbacks = {};
        this.readLoop();
    }

    static async fromSerialPort(serialPort) {
        await serialPort.open({
            baudRate: 115200,
        });

        return new RNode(serialPort);
    }

    async close() {
        try {
            this.reader.releaseLock();
        } catch {
            // ignore
        }

        try {
            await this.serialPort.close();
        } catch {
            // ignore
        }
    }

    async write(bytes) {
        const writer = this.writable.getWriter();
        try {
            await writer.write(new Uint8Array(bytes));
        } finally {
            writer.releaseLock();
        }
    }

    async readLoop() {
        try {
            let buffer = [];
            let inFrame = false;
            while (true) {
                const { value, done } = await this.reader.read();
                if (done) {
                    break;
                }

                for (const byte of value) {
                    if (byte === this.KISS_FEND) {
                        if (inFrame) {
                            const decodedFrame = this.decodeKissFrame(buffer);
                            if (decodedFrame) {
                                this.onCommandReceived(decodedFrame);
                            } else {
                                console.warn("Invalid frame ignored.");
                            }
                            buffer = [];
                        }
                        inFrame = !inFrame;
                    } else if (inFrame) {
                        buffer.push(byte);
                    }
                }
            }
        } catch (error) {
            if (error instanceof TypeError) {
                return;
            }
            console.error("Error reading from serial port: ", error);
        } finally {
            try {
                this.reader.releaseLock();
            } catch {
                // ignore
            }
        }
    }

    onCommandReceived(data) {
        try {
            const [command, ...bytes] = data;
            const callback = this.callbacks[command];
            if (!callback) {
                return;
            }
            callback(bytes);
            delete this.callbacks[command];
        } catch (e) {
            console.log("failed to handle received command", data, e);
        }
    }

    decodeKissFrame(frame) {
        const data = [];
        let escaping = false;

        for (const byte of frame) {
            if (escaping) {
                if (byte === this.KISS_TFEND) {
                    data.push(this.KISS_FEND);
                } else if (byte === this.KISS_TFESC) {
                    data.push(this.KISS_FESC);
                } else {
                    return null;
                }
                escaping = false;
            } else if (byte === this.KISS_FESC) {
                escaping = true;
            } else {
                data.push(byte);
            }
        }

        return escaping ? null : data;
    }

    createKissFrame(data) {
        let frame = [this.KISS_FEND];
        for (let byte of data) {
            if (byte === this.KISS_FEND) {
                frame.push(this.KISS_FESC, this.KISS_TFEND);
            } else if (byte === this.KISS_FESC) {
                frame.push(this.KISS_FESC, this.KISS_TFESC);
            } else {
                frame.push(byte);
            }
        }
        frame.push(this.KISS_FEND);
        return new Uint8Array(frame);
    }

    async sendKissCommand(data) {
        await this.write(this.createKissFrame(data));
    }

    async sendCommand(command, data) {
        return new Promise((resolve, reject) => {
            this.callbacks[command] = (response) => {
                resolve(response);
            };

            this.sendKissCommand([command, ...data]).catch((e) => {
                reject(e);
            });
        });
    }

    async reset() {
        await this.sendKissCommand([this.CMD_RESET, this.CMD_RESET_BYTE]);
    }

    async detect() {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                resolve(false);
            }, 2000);

            this.sendCommand(this.CMD_DETECT, [this.DETECT_REQ])
                .then((response) => {
                    clearTimeout(timeout);
                    const [responseByte] = response;
                    const isRnode = responseByte === this.DETECT_RESP;
                    resolve(isRnode);
                })
                .catch(() => {
                    resolve(false);
                });
        });
    }

    async getFirmwareVersion() {
        const response = await this.sendCommand(this.CMD_FW_VERSION, [0x00]);
        var [majorVersion, minorVersion] = response;
        if (minorVersion.length === 1) {
            minorVersion = "0" + minorVersion;
        }
        return majorVersion + "." + minorVersion;
    }

    async getPlatform() {
        const response = await this.sendCommand(this.CMD_PLATFORM, [0x00]);
        const [platformByte] = response;
        return platformByte;
    }

    async getMcu() {
        const response = await this.sendCommand(this.CMD_MCU, [0x00]);
        const [mcuByte] = response;
        return mcuByte;
    }

    async getBoard() {
        const response = await this.sendCommand(this.CMD_BOARD, [0x00]);
        const [boardByte] = response;
        return boardByte;
    }

    async getDeviceHash() {
        const response = await this.sendCommand(this.CMD_DEV_HASH, [0x01]);
        const [...deviceHash] = response;
        return deviceHash;
    }

    async getTargetFirmwareHash() {
        const response = await this.sendCommand(this.CMD_HASHES, [this.HASH_TYPE_TARGET_FIRMWARE]);
        const [, ...targetFirmwareHash] = response;
        return targetFirmwareHash;
    }

    async getFirmwareHash() {
        const response = await this.sendCommand(this.CMD_HASHES, [this.HASH_TYPE_FIRMWARE]);
        const [, ...firmwareHash] = response;
        return firmwareHash;
    }

    async getRom() {
        const response = await this.sendCommand(this.CMD_ROM_READ, [0x00]);
        const [...eepromBytes] = response;
        return eepromBytes;
    }

    async getFrequency() {
        const response = await this.sendCommand(this.CMD_FREQUENCY, [0x00, 0x00, 0x00, 0x00]);
        const [...frequencyBytes] = response;
        const frequencyInHz =
            (frequencyBytes[0] << 24) | (frequencyBytes[1] << 16) | (frequencyBytes[2] << 8) | frequencyBytes[3];
        return frequencyInHz;
    }

    async getBandwidth() {
        const response = await this.sendCommand(this.CMD_BANDWIDTH, [0x00, 0x00, 0x00, 0x00]);
        const [...bandwidthBytes] = response;
        const bandwidthInHz =
            (bandwidthBytes[0] << 24) | (bandwidthBytes[1] << 16) | (bandwidthBytes[2] << 8) | bandwidthBytes[3];
        return bandwidthInHz;
    }

    async getTxPower() {
        const response = await this.sendCommand(this.CMD_TXPOWER, [0xff]);
        const [txPower] = response;
        return txPower;
    }

    async getSpreadingFactor() {
        const response = await this.sendCommand(this.CMD_SF, [0xff]);
        const [spreadingFactor] = response;
        return spreadingFactor;
    }

    async getCodingRate() {
        const response = await this.sendCommand(this.CMD_CR, [0xff]);
        const [codingRate] = response;
        return codingRate;
    }

    async getRadioState() {
        const response = await this.sendCommand(this.CMD_RADIO_STATE, [0xff]);
        const [radioState] = response;
        return radioState;
    }

    async getRxStat() {
        const response = await this.sendCommand(this.CMD_STAT_RX, [0x00]);
        const [...statBytes] = response;
        const stat = (statBytes[0] << 24) | (statBytes[1] << 16) | (statBytes[2] << 8) | statBytes[3];
        return stat;
    }

    async getTxStat() {
        const response = await this.sendCommand(this.CMD_STAT_TX, [0x00]);
        const [...statBytes] = response;
        const stat = (statBytes[0] << 24) | (statBytes[1] << 16) | (statBytes[2] << 8) | statBytes[3];
        return stat;
    }

    async getRssiStat() {
        const response = await this.sendCommand(this.CMD_STAT_RSSI, [0x00]);
        const [rssi] = response;
        return rssi;
    }

    async disableBluetooth() {
        await this.sendKissCommand([this.CMD_BT_CTRL, 0x00]);
    }

    async enableBluetooth() {
        await this.sendKissCommand([this.CMD_BT_CTRL, 0x01]);
    }

    async startBluetoothPairing(pinCallback) {
        this.callbacks[this.CMD_BT_PIN] = (response) => {
            const [...pinBytes] = response;
            const pin = (pinBytes[0] << 24) | (pinBytes[1] << 16) | (pinBytes[2] << 8) | pinBytes[3];
            pinCallback(pin);
        };

        await this.sendKissCommand([this.CMD_BT_CTRL, 0x02]);
    }

    async readDisplay() {
        const response = await this.sendCommand(this.CMD_DISP_READ, [0x01]);
        const [...displayBuffer] = response;
        return displayBuffer;
    }

    async setFrequency(frequencyInHz) {
        const c1 = frequencyInHz >> 24;
        const c2 = (frequencyInHz >> 16) & 0xff;
        const c3 = (frequencyInHz >> 8) & 0xff;
        const c4 = frequencyInHz & 0xff;
        await this.sendKissCommand([this.CMD_FREQUENCY, c1, c2, c3, c4]);
    }

    async setBandwidth(bandwidthInHz) {
        const c1 = bandwidthInHz >> 24;
        const c2 = (bandwidthInHz >> 16) & 0xff;
        const c3 = (bandwidthInHz >> 8) & 0xff;
        const c4 = bandwidthInHz & 0xff;
        await this.sendKissCommand([this.CMD_BANDWIDTH, c1, c2, c3, c4]);
    }

    async setTxPower(db) {
        await this.sendKissCommand([this.CMD_TXPOWER, db]);
    }

    async setSpreadingFactor(spreadingFactor) {
        await this.sendKissCommand([this.CMD_SF, spreadingFactor]);
    }

    async setCodingRate(codingRate) {
        await this.sendKissCommand([this.CMD_CR, codingRate]);
    }

    async setRadioStateOn() {
        await this.sendKissCommand([this.CMD_RADIO_STATE, this.RADIO_STATE_ON]);
    }

    async setRadioStateOff() {
        await this.sendKissCommand([this.CMD_RADIO_STATE, this.RADIO_STATE_OFF]);
    }

    async saveConfig() {
        await this.sendKissCommand([this.CMD_CONF_SAVE, 0x00]);
    }

    async deleteConfig() {
        await this.sendKissCommand([this.CMD_CONF_DELETE, 0x00]);
    }

    async indicateFirmwareUpdate() {
        await this.sendKissCommand([this.CMD_FW_UPD, 0x01]);
    }

    async setFirmwareHash(hash) {
        await this.sendKissCommand([this.CMD_FW_HASH, ...hash]);
    }

    async writeRom(address, value) {
        await this.sendKissCommand([this.CMD_ROM_WRITE, address, value]);
        await RNodeUtils.sleepMillis(85);
    }

    async wipeRom() {
        await this.sendKissCommand([this.CMD_UNLOCK_ROM, this.ROM_UNLOCK_BYTE]);
        await RNodeUtils.sleepMillis(30000);
    }

    async getRomAsObject() {
        const rom = await this.getRom();
        return new ROM(rom);
    }

    async setDisplayRotation(rotation) {
        await this.sendKissCommand([this.CMD_DISP_ROT, rotation & 0xff]);
    }

    async startDisplayReconditioning() {
        await this.sendKissCommand([this.CMD_DISP_RCND, 0x01]);
    }
}
