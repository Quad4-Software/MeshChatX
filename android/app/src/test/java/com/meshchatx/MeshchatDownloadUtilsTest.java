package com.meshchatx;

import org.junit.Assert;
import org.junit.Test;

public class MeshchatDownloadUtilsTest {

    @Test
    public void sanitize_returnsDefaultForNullOrEmpty() {
        Assert.assertEquals("download.bin", MeshchatDownloadUtils.sanitizeFileName(null));
        Assert.assertEquals("download.bin", MeshchatDownloadUtils.sanitizeFileName(""));
    }

    @Test
    public void sanitize_stripsPathSeparators() {
        Assert.assertEquals("a.json", MeshchatDownloadUtils.sanitizeFileName("/sdcard/foo/a.json"));
        Assert.assertEquals("b.json", MeshchatDownloadUtils.sanitizeFileName("C:\\fake\\path\\b.json"));
    }

    @Test
    public void sanitize_replacesUnsafeCharacters() {
        Assert.assertEquals("mesh_x_folders_.json", MeshchatDownloadUtils.sanitizeFileName("mesh:x?folders*.json"));
    }

    @Test
    public void sanitize_truncatesLongNames() {
        String raw = repeat('a', 200) + ".json";
        Assert.assertEquals(120, MeshchatDownloadUtils.sanitizeFileName(raw).length());
    }

    private static String repeat(char c, int n) {
        char[] buf = new char[n];
        java.util.Arrays.fill(buf, c);
        return new String(buf);
    }
}
