export default class Nrf52DfuFlasher {
    DFU_TOUCH_BAUD = 1200;
    SERIAL_PORT_OPEN_WAIT_TIME = 0.1;
    TOUCH_RESET_WAIT_TIME = 1.5;

    FLASH_BAUD = 115200;

    HEX_TYPE_APPLICATION = 4;

    DFU_INIT_PACKET = 1;
    DFU_START_PACKET = 3;
    DFU_DATA_PACKET = 4;
    DFU_STOP_DATA_PACKET = 5;

    DATA_INTEGRITY_CHECK_PRESENT = 1;
    RELIABLE_PACKET = 1;
    HCI_PACKET_TYPE = 14;

    FLASH_PAGE_SIZE = 4096;
    FLASH_PAGE_ERASE_TIME = 0.0897;
    FLASH_WORD_WRITE_TIME = 0.0001;
    FLASH_PAGE_WRITE_TIME = (this.FLASH_PAGE_SIZE / 4) * this.FLASH_WORD_WRITE_TIME;

    // The DFU packet max size
    DFU_PACKET_MAX_SIZE = 512;

    constructor(serialPort) {
        this.serialPort = serialPort;
        this.sequenceNumber = 0;
        this.sd_size = 0;
        this.total_size = 0;
    }

    /**
     * Waits for the provided milliseconds, and then resolves.
     * @param millis
     * @returns {Promise<void>}
     */
    async sleepMillis(millis) {
        await new Promise((resolve) => {
            setTimeout(resolve, millis);
        });
    }

    /**
     * Writes the provided data to the Serial Port.
     * @param data
     * @returns {Promise<void>}
     */
    async sendPacket(data) {
        const writer = this.serialPort.writable.getWriter();
        try {
            await writer.write(new Uint8Array(data));
        } finally {
            writer.releaseLock();
        }
    }

    /**
     * Puts an nRF52 board into DFU mode by quickly opening and closing a serial port.
     * @returns {Promise<void>}
     */
    async enterDfuMode() {
        await this.serialPort.open({
            baudRate: this.DFU_TOUCH_BAUD,
        });

        await this.sleepMillis(this.SERIAL_PORT_OPEN_WAIT_TIME * 1000);
        await this.serialPort.close();
        await this.sleepMillis(this.TOUCH_RESET_WAIT_TIME * 1000);
    }

    /**
     * Flashes the provided firmware zip.
     * @param firmwareZipBlob
     * @param progressCallback
     * @returns {Promise<void>}
     */
    async flash(firmwareZipBlob, progressCallback) {
        const blobReader = new window.zip.BlobReader(firmwareZipBlob);
        const zipReader = new window.zip.ZipReader(blobReader);
        const zipEntries = await zipReader.getEntries();

        const manifestFile = zipEntries.find((zipEntry) => zipEntry.filename === "manifest.json");
        if (!manifestFile) {
            throw new Error("manifest.json not found in firmware file!");
        }

        const text = await manifestFile.getData(new window.zip.TextWriter());
        const json = JSON.parse(text);
        const manifest = json.manifest;

        if (manifest.application) {
            await this.dfuSendImage(this.HEX_TYPE_APPLICATION, zipEntries, manifest.application, progressCallback);
        }
    }

    /**
     * Sends the firmware image to the device in DFU mode.
     * @param programMode
     * @param zipEntries
     * @param firmwareManifest
     * @param progressCallback
     * @returns {Promise<void>}
     */
    async dfuSendImage(programMode, zipEntries, firmwareManifest, progressCallback) {
        await this.serialPort.open({
            baudRate: this.FLASH_BAUD,
        });

        await this.sleepMillis(this.SERIAL_PORT_OPEN_WAIT_TIME * 1000);

        var softdeviceSize = 0;
        var bootloaderSize = 0;
        var applicationSize = 0;

        const binFile = zipEntries.find((zipEntry) => zipEntry.filename === firmwareManifest.bin_file);
        const firmware = await binFile.getData(new window.zip.Uint8ArrayWriter());

        const datFile = zipEntries.find((zipEntry) => zipEntry.filename === firmwareManifest.dat_file);
        const init_packet = await datFile.getData(new window.zip.Uint8ArrayWriter());

        if (programMode !== this.HEX_TYPE_APPLICATION) {
            throw new Error("not implemented");
        }

        if (programMode === this.HEX_TYPE_APPLICATION) {
            applicationSize = firmware.length;
        }

        await this.sendStartDfu(programMode, softdeviceSize, bootloaderSize, applicationSize);
        await this.sendInitPacket(init_packet);
        await this.sendFirmware(firmware, progressCallback);
    }

    calcCrc16(binaryData, crc = 0xffff) {
        if (!(binaryData instanceof Uint8Array)) {
            throw new Error("calcCrc16 requires Uint8Array input");
        }

        for (let b of binaryData) {
            crc = ((crc >> 8) & 0x00ff) | ((crc << 8) & 0xff00);
            crc ^= b;
            crc ^= (crc & 0x00ff) >> 4;
            crc ^= (crc << 8) << 4;
            crc ^= ((crc & 0x00ff) << 4) << 1;
        }

        return crc & 0xffff;
    }

    slipEncodeEscChars(dataIn) {
        let result = [];
        for (let i = 0; i < dataIn.length; i++) {
            let char = dataIn[i];
            if (char === 0xc0) {
                result.push(0xdb);
                result.push(0xdc);
            } else if (char === 0xdb) {
                result.push(0xdb);
                result.push(0xdd);
            } else {
                result.push(char);
            }
        }
        return result;
    }

    createHciPacketFromFrame(frame) {
        this.sequenceNumber = (this.sequenceNumber + 1) % 8;
        const slipHeaderBytes = this.createSlipHeader(
            this.sequenceNumber,
            this.DATA_INTEGRITY_CHECK_PRESENT,
            this.RELIABLE_PACKET,
            this.HCI_PACKET_TYPE,
            frame.length
        );

        let data = [...slipHeaderBytes, ...frame];
        const crc = this.calcCrc16(new Uint8Array(data), 0xffff);
        data.push(crc & 0xff);
        data.push((crc & 0xff00) >> 8);

        return [0xc0, ...this.slipEncodeEscChars(data), 0xc0];
    }

    getEraseWaitTime() {
        return Math.max(0.5, (this.total_size / this.FLASH_PAGE_SIZE + 1) * this.FLASH_PAGE_ERASE_TIME);
    }

    createImageSizePacket(softdeviceSize = 0, bootloaderSize = 0, appSize = 0) {
        return [
            ...this.int32ToBytes(softdeviceSize),
            ...this.int32ToBytes(bootloaderSize),
            ...this.int32ToBytes(appSize),
        ];
    }

    async sendStartDfu(mode, softdevice_size = 0, bootloader_size = 0, app_size = 0) {
        const frame = [
            ...this.int32ToBytes(this.DFU_START_PACKET),
            ...this.int32ToBytes(mode),
            ...this.createImageSizePacket(softdevice_size, bootloader_size, app_size),
        ];

        await this.sendPacket(this.createHciPacketFromFrame(frame));
        this.sd_size = softdevice_size;
        this.total_size = softdevice_size + bootloader_size + app_size;
        await this.sleepMillis(this.getEraseWaitTime() * 1000);
    }

    async sendInitPacket(initPacket) {
        const frame = [...this.int32ToBytes(this.DFU_INIT_PACKET), ...initPacket, ...this.int16ToBytes(0x0000)];
        await this.sendPacket(this.createHciPacketFromFrame(frame));
    }

    async sendFirmware(firmware, progressCallback) {
        const packets = [];
        var packetsSent = 0;

        for (let i = 0; i < firmware.length; i += this.DFU_PACKET_MAX_SIZE) {
            packets.push(
                this.createHciPacketFromFrame([
                    ...this.int32ToBytes(this.DFU_DATA_PACKET),
                    ...firmware.slice(i, i + this.DFU_PACKET_MAX_SIZE),
                ])
            );
        }

        if (progressCallback) {
            progressCallback(0);
        }

        for (var i = 0; i < packets.length; i++) {
            await this.sendPacket(packets[i]);
            await this.sleepMillis(this.FLASH_PAGE_WRITE_TIME * 1000);
            packetsSent++;
            if (progressCallback) {
                const progress = Math.floor((packetsSent / packets.length) * 100);
                progressCallback(progress);
            }
        }

        await this.sendPacket(this.createHciPacketFromFrame([...this.int32ToBytes(this.DFU_STOP_DATA_PACKET)]));
    }

    createSlipHeader(seq, dip, rp, pktType, pktLen) {
        let ints = [0, 0, 0, 0];
        ints[0] = seq | (((seq + 1) % 8) << 3) | (dip << 6) | (rp << 7);
        ints[1] = pktType | ((pktLen & 0x000f) << 4);
        ints[2] = (pktLen & 0x0ff0) >> 4;
        ints[3] = (~(ints[0] + ints[1] + ints[2]) + 1) & 0xff;
        return new Uint8Array(ints);
    }

    int32ToBytes(num) {
        return [num & 0x000000ff, (num & 0x0000ff00) >> 8, (num & 0x00ff0000) >> 16, (num & 0xff000000) >> 24];
    }

    int16ToBytes(num) {
        return [num & 0x00ff, (num & 0xff00) >> 8];
    }
}
