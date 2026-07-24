package com.meshchatx.rnode;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import java.io.ByteArrayOutputStream;

public class Esp32SerialFlasherTest {
    @Test
    public void imagesFromZipMapsAddresses() throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            zos.putNextEntry(new ZipEntry("app.bin"));
            zos.write(new byte[] {1, 2, 3, 4});
            zos.closeEntry();
            zos.putNextEntry(new ZipEntry("bootloader.bin"));
            zos.write(new byte[] {9, 8});
            zos.closeEntry();
        }
        Map<String, String> map = new LinkedHashMap<>();
        map.put("0x1000", "bootloader.bin");
        map.put("0x10000", "app.bin");
        List<Esp32SerialFlasher.Image> images =
            Esp32SerialFlasher.imagesFromZip(bos.toByteArray(), map);
        assertEquals(2, images.size());
        assertEquals(0x1000, images.get(0).address);
        assertEquals(2, images.get(0).data.length);
        assertEquals(0x10000, images.get(1).address);
        assertEquals(4, images.get(1).data.length);
    }

    @Test
    public void md5HexIsStable() {
        String hex = Esp32SerialFlasher.md5Hex(new byte[] {1, 2, 3});
        assertFalse(hex.isEmpty());
        assertEquals(32, hex.length());
        assertTrue(hex.matches("[0-9a-f]+"));
    }
}
