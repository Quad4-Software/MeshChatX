package com.meshchatx.rnode;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.Map;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Minimal ESP32 ROM bootloader flasher over USB serial (Apache-2.0 protocol).
 *
 * Implements the subset used by RNode firmware installs: sync, SPI attach,
 * baud change, flash begin/data/end, and hard reset via DTR/RTS.
 */
public final class Esp32SerialFlasher {
    public interface Progress {
        void onStatus(String message);

        void onProgress(int percent);
    }

    public static final class Image {
        public final int address;
        public final byte[] data;

        public Image(int address, byte[] data) {
            this.address = address;
            this.data = data;
        }
    }

    private static final int DEFAULT_TIMEOUT_MS = 3000;
    private static final int SYNC_TIMEOUT_MS = 100;
    private static final byte[] MAGIC_SYNC =
        new byte[] {
            0x07,
            0x07,
            0x12,
            0x20,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
            0x55,
        };

    private static final int OP_FLASH_BEGIN = 0x02;
    private static final int OP_FLASH_DATA = 0x03;
    private static final int OP_FLASH_END = 0x04;
    private static final int OP_SYNC = 0x08;
    private static final int OP_SPI_ATTACH = 0x0d;
    private static final int OP_CHANGE_BAUDRATE = 0x0f;

    private final UsbSerialHub hub;
    private final Progress progress;
    private int sequence = 0;

    public Esp32SerialFlasher(UsbSerialHub hub, Progress progress) {
        this.hub = hub;
        this.progress = progress != null ? progress : new Progress() {
            @Override
            public void onStatus(String message) {
            }

            @Override
            public void onProgress(int percent) {
            }
        };
    }

    public void flash(List<Image> images, int flashBaud) throws IOException, InterruptedException {
        if (images == null || images.isEmpty()) {
            throw new IOException("No firmware images to flash");
        }
        progress.onStatus("Entering bootloader…");
        enterBootloader();
        progress.onStatus("Syncing…");
        sync();
        progress.onStatus("Attaching SPI flash…");
        spiAttach();
        if (flashBaud > 115200) {
            progress.onStatus("Raising baud to " + flashBaud + "…");
            changeBaud(flashBaud);
        }

        long totalBytes = 0;
        for (Image image : images) {
            totalBytes += image.data.length;
        }
        long written = 0;

        for (int i = 0; i < images.size(); i++) {
            Image image = images.get(i);
            progress.onStatus(
                String.format(
                    Locale.US,
                    "Flashing file %d/%d at 0x%X (%d bytes)…",
                    i + 1,
                    images.size(),
                    image.address,
                    image.data.length
                )
            );
            flashImage(image, written, totalBytes);
            written += image.data.length;
            progress.onProgress((int) Math.min(100, (written * 100) / Math.max(1, totalBytes)));
        }

        progress.onStatus("Finishing…");
        command(OP_FLASH_END, intLe(1), 0, DEFAULT_TIMEOUT_MS);
        progress.onStatus("Resetting device…");
        hardReset();
        progress.onProgress(100);
        progress.onStatus("Flash complete");
    }

    private void enterBootloader() throws IOException, InterruptedException {
        // Classic ESP auto-reset: RTS=EN, DTR=IO0
        hub.setDtrRts(false, false);
        Thread.sleep(100);
        hub.setDtrRts(true, false);
        Thread.sleep(100);
        hub.setDtrRts(false, true);
        Thread.sleep(50);
        hub.setDtrRts(false, false);
        Thread.sleep(400);
    }

    private void hardReset() throws IOException, InterruptedException {
        hub.setDtrRts(false, true);
        Thread.sleep(100);
        hub.setDtrRts(false, false);
        Thread.sleep(200);
    }

    private void sync() throws IOException, InterruptedException {
        IOException last = null;
        for (int attempt = 0; attempt < 10; attempt++) {
            try {
                flushInput();
                command(OP_SYNC, MAGIC_SYNC, 0, SYNC_TIMEOUT_MS);
                // Drain extra sync responses
                for (int i = 0; i < 7; i++) {
                    try {
                        readResponse(OP_SYNC, SYNC_TIMEOUT_MS);
                    } catch (IOException ignored) {
                        break;
                    }
                }
                return;
            } catch (IOException e) {
                last = e;
                enterBootloader();
            }
        }
        throw last != null ? last : new IOException("Failed to sync with ESP bootloader");
    }

    private void spiAttach() throws IOException {
        command(OP_SPI_ATTACH, intLe(0), 0, DEFAULT_TIMEOUT_MS);
    }

    private void changeBaud(int baud) throws IOException, InterruptedException {
        ByteBuffer buf = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
        buf.putInt(baud);
        buf.putInt(0);
        command(OP_CHANGE_BAUDRATE, buf.array(), 0, DEFAULT_TIMEOUT_MS);
        Thread.sleep(100);
        hub.setBaudRate(baud);
        Thread.sleep(50);
        flushInput();
    }

    private void flashImage(Image image, long alreadyWritten, long totalBytes)
        throws IOException {
        final int blockSize = 0x400;
        int numBlocks = (image.data.length + blockSize - 1) / blockSize;
        ByteBuffer begin = ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN);
        begin.putInt(image.data.length);
        begin.putInt(numBlocks);
        begin.putInt(blockSize);
        begin.putInt(image.address);
        command(OP_FLASH_BEGIN, begin.array(), 0, DEFAULT_TIMEOUT_MS);

        int seq = 0;
        int offset = 0;
        while (offset < image.data.length) {
            int chunkLen = Math.min(blockSize, image.data.length - offset);
            byte[] block = Arrays.copyOfRange(image.data, offset, offset + chunkLen);
            if (block.length < blockSize) {
                block = Arrays.copyOf(block, blockSize);
            }
            ByteBuffer data = ByteBuffer.allocate(16 + block.length).order(ByteOrder.LITTLE_ENDIAN);
            data.putInt(block.length);
            data.putInt(seq);
            data.putInt(0);
            data.putInt(0);
            data.put(block);
            int checksum = 0xef;
            for (byte b : block) {
                checksum ^= (b & 0xff);
            }
            command(OP_FLASH_DATA, data.array(), checksum, DEFAULT_TIMEOUT_MS);
            seq++;
            offset += chunkLen;
            long approx = alreadyWritten + offset;
            progress.onProgress((int) Math.min(99, (approx * 100) / Math.max(1, totalBytes)));
        }
    }

    private byte[] command(int op, byte[] data, int checksum, int timeoutMs) throws IOException {
        sequence = (sequence + 1) & 0xff;
        ByteBuffer packet = ByteBuffer.allocate(8 + data.length).order(ByteOrder.LITTLE_ENDIAN);
        packet.put((byte) 0x00);
        packet.put((byte) op);
        packet.putShort((short) data.length);
        packet.putInt(checksum);
        packet.put(data);
        hub.write(slipEncode(packet.array()));
        return readResponse(op, timeoutMs);
    }

    private byte[] readResponse(int expectedOp, int timeoutMs) throws IOException {
        long deadline = System.currentTimeMillis() + timeoutMs;
        ByteArrayOutputStream frame = new ByteArrayOutputStream();
        boolean inFrame = false;
        byte[] buf = new byte[256];
        while (System.currentTimeMillis() < deadline) {
            int n = hub.read(buf, 50);
            if (n <= 0) {
                continue;
            }
            for (int i = 0; i < n; i++) {
                int b = buf[i] & 0xff;
                if (!inFrame) {
                    if (b == 0xc0) {
                        inFrame = true;
                        frame.reset();
                    }
                    continue;
                }
                if (b == 0xc0) {
                    byte[] decoded = slipDecode(frame.toByteArray());
                    if (decoded.length < 8) {
                        inFrame = false;
                        continue;
                    }
                    int direction = decoded[0] & 0xff;
                    int op = decoded[1] & 0xff;
                    if (direction != 0x01 || op != expectedOp) {
                        inFrame = false;
                        continue;
                    }
                    int size =
                        (decoded[2] & 0xff) | ((decoded[3] & 0xff) << 8);
                    if (decoded.length < 8 + size) {
                        inFrame = false;
                        continue;
                    }
                    // status bytes at end of value for ROM protocol
                    if (size >= 2) {
                        int status = decoded[8 + size - 2] & 0xff;
                        int error = decoded[8 + size - 1] & 0xff;
                        if (status != 0) {
                            throw new IOException(
                                "ESP bootloader error op=0x"
                                    + Integer.toHexString(expectedOp)
                                    + " status="
                                    + status
                                    + " err="
                                    + error
                            );
                        }
                    }
                    return Arrays.copyOfRange(decoded, 8, 8 + size);
                }
                frame.write(b);
            }
        }
        throw new IOException("Timeout waiting for ESP response op=0x" + Integer.toHexString(expectedOp));
    }

    private void flushInput() throws IOException {
        byte[] buf = new byte[512];
        for (int i = 0; i < 5; i++) {
            int n = hub.read(buf, 20);
            if (n <= 0) {
                break;
            }
        }
    }

    private static byte[] slipEncode(byte[] data) {
        ByteArrayOutputStream out = new ByteArrayOutputStream(data.length + 16);
        out.write(0xc0);
        for (byte value : data) {
            int b = value & 0xff;
            if (b == 0xc0) {
                out.write(0xdb);
                out.write(0xdc);
            } else if (b == 0xdb) {
                out.write(0xdb);
                out.write(0xdd);
            } else {
                out.write(b);
            }
        }
        out.write(0xc0);
        return out.toByteArray();
    }

    private static byte[] slipDecode(byte[] data) {
        ByteArrayOutputStream out = new ByteArrayOutputStream(data.length);
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xff;
            if (b == 0xdb && i + 1 < data.length) {
                int n = data[++i] & 0xff;
                if (n == 0xdc) {
                    out.write(0xc0);
                } else if (n == 0xdd) {
                    out.write(0xdb);
                }
            } else {
                out.write(b);
            }
        }
        return out.toByteArray();
    }

    private static byte[] intLe(int value) {
        return ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array();
    }

    public static List<Image> imagesFromZip(
        byte[] zipBytes,
        Map<String, String> addressToFilename
    ) throws IOException {
        List<Image> images = new ArrayList<>();
        try (java.util.zip.ZipInputStream zis =
            new java.util.zip.ZipInputStream(new java.io.ByteArrayInputStream(zipBytes))) {
            java.util.zip.ZipEntry entry;
            java.util.Map<String, byte[]> files = new java.util.HashMap<>();
            byte[] buf = new byte[8192];
            while ((entry = zis.getNextEntry()) != null) {
                if (entry.isDirectory()) {
                    continue;
                }
                String name = entry.getName();
                int slash = name.lastIndexOf('/');
                if (slash >= 0) {
                    name = name.substring(slash + 1);
                }
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                int n;
                while ((n = zis.read(buf)) > 0) {
                    bos.write(buf, 0, n);
                }
                files.put(name, bos.toByteArray());
            }
            for (Map.Entry<String, String> mapping : addressToFilename.entrySet()) {
                int address = Integer.decode(mapping.getKey());
                byte[] data = files.get(mapping.getValue());
                if (data == null) {
                    throw new IOException("Missing firmware file in zip: " + mapping.getValue());
                }
                images.add(new Image(address, data));
            }
        }
        // Flash lower addresses first
        images.sort((a, b) -> Integer.compare(a.address, b.address));
        return images;
    }

    public static String md5Hex(byte[] data) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] dig = md.digest(data);
            StringBuilder sb = new StringBuilder(dig.length * 2);
            for (byte b : dig) {
                sb.append(String.format(Locale.US, "%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }
}
