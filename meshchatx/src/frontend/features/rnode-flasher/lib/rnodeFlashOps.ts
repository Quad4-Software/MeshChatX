// SPDX-License-Identifier: 0BSD

import WifiTransport from "../../../js/rnode/transports/WifiTransport.js";
import SerialTransport from "../../../js/rnode/transports/SerialTransport.js";
import Nrf52DfuFlasher from "../../../js/rnode/Nrf52DfuFlasher.js";
import { readAsBinaryString } from "./rnodeVendorLibs.js";
import { t } from "../../../js/i18n.js";

export async function flashWifiOp(
    wifiHost: string,
    firmwareFile: File,
    selectedProduct: any,
    selectedModel: any,
    onProgress: (percentage: number, status: string) => void
): Promise<void> {
    if (!WifiTransport.isValidHost(wifiHost)) {
        throw new Error(t("tools.rnode_flasher.errors.invalid_host"));
    }
    const flashConfig = selectedModel?.flash_config ?? selectedProduct?.flash_config;
    const win = window as any;
    const blobReader = new win.zip.BlobReader(firmwareFile);
    const zipReader = new win.zip.ZipReader(blobReader);
    const zipEntries = await zipReader.getEntries();

    let mainBinFilename = flashConfig?.flash_files?.["0x10000"];
    if (!mainBinFilename) {
        const binEntry = zipEntries.find(
            (e: any) =>
                e.filename.endsWith(".bin") && !e.filename.includes("bootloader") && !e.filename.includes("partitions")
        );
        if (binEntry) mainBinFilename = binEntry.filename;
    }
    if (!mainBinFilename) {
        throw new Error(t("tools.rnode_flasher.errors.no_main_bin"));
    }
    const entry = zipEntries.find((e: any) => e.filename === mainBinFilename);
    if (!entry) {
        throw new Error(t("tools.rnode_flasher.errors.failed_extract", { file: mainBinFilename }));
    }
    const binBlob = await entry.getData(new win.zip.BlobWriter());

    const transport = new WifiTransport(wifiHost);
    await transport.upload(binBlob, (percentage: number) => {
        onProgress(percentage, t("tools.rnode_flasher.uploading", { percentage }));
    });
}

export async function flashNrf52Op(
    firmwareFile: File,
    onProgress: (percentage: number, status: string) => void
): Promise<void> {
    const transport = await SerialTransport.request();
    try {
        const flasher = new Nrf52DfuFlasher(transport.port);
        await flasher.flash(firmwareFile, (percentage: number) => {
            onProgress(percentage, t("tools.rnode_flasher.flashing", { percentage }));
        });
    } finally {
        if (transport) await transport.close().catch(() => {});
    }
}

export async function flashEsp32Op(
    firmwareFile: File,
    selectedProduct: any,
    selectedModel: any,
    onProgress: (percentage: number, status: string) => void
): Promise<void> {
    const win = window as any;
    if (!win.ESPLoader) {
        throw new Error(t("tools.rnode_flasher.errors.esptool_not_loaded"));
    }
    const flashConfig = selectedModel?.flash_config ?? selectedProduct?.flash_config;
    if (!flashConfig) {
        throw new Error(t("tools.rnode_flasher.errors.no_flash_config"));
    }

    const transport = await SerialTransport.request();
    try {
        const blobReader = new win.zip.BlobReader(firmwareFile);
        const zipReader = new win.zip.ZipReader(blobReader);
        const zipEntries = await zipReader.getEntries();

        const filesToFlash: Array<{ address: number; data: string }> = [];
        for (const [address, filename] of Object.entries(flashConfig.flash_files as Record<string, string>)) {
            const entry = zipEntries.find((e: any) => e.filename === filename);
            if (!entry) {
                throw new Error(t("tools.rnode_flasher.errors.failed_extract", { file: filename }));
            }
            const blob = await entry.getData(new win.zip.BlobWriter());
            filesToFlash.push({
                address: parseInt(address),
                data: await readAsBinaryString(blob),
            });
        }

        const espTransport = new win.Transport(transport.port, true);
        const esploader = new win.ESPLoader({
            transport: espTransport,
            baudrate: 921600,
            terminal: { writeLine: console.log, write: console.log, clean: () => {} },
        });

        await esploader.main();
        await esploader.writeFlash({
            fileArray: filesToFlash,
            flashSize: flashConfig.flash_size,
            flashMode: "DIO",
            flashFreq: "80MHz",
            calculateMD5Hash: (img: any) => win.CryptoJS.MD5(win.CryptoJS.enc.Latin1.parse(img)),
            reportProgress: (idx: number, written: number, total: number) => {
                const percentage = Math.floor((written / total) * 100);
                const status = t("tools.rnode_flasher.flashing_file_progress", {
                    current: idx + 1,
                    total: filesToFlash.length,
                    percentage,
                });
                onProgress(percentage, status);
            },
        });

        await espTransport.setDTR(false);
        await new Promise((r) => setTimeout(r, 100));
        await espTransport.setDTR(true);
    } finally {
        if (transport) await transport.close().catch(() => {});
    }
}
