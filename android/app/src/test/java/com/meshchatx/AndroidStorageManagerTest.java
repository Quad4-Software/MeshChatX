package com.meshchatx;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class AndroidStorageManagerTest {

    @Rule
    public TemporaryFolder temp = new TemporaryFolder();

    @Test
    public void hasMeshchatData_falseWhenMissingOrEmpty() throws IOException {
        File root = temp.newFolder("meshchatx");
        Assert.assertFalse(AndroidStorageManager.hasMeshchatData(root));
        File storage = new File(root, "storage");
        Assert.assertTrue(storage.mkdirs());
        Assert.assertFalse(AndroidStorageManager.hasMeshchatData(root));
    }

    @Test
    public void hasMeshchatData_trueWhenStorageHasFiles() throws IOException {
        File root = temp.newFolder("meshchatx2");
        File storage = new File(root, "storage");
        Assert.assertTrue(storage.mkdirs());
        try (FileOutputStream out = new FileOutputStream(new File(storage, "identity"))) {
            out.write(1);
        }
        Assert.assertTrue(AndroidStorageManager.hasMeshchatData(root));
    }

    @Test
    public void copyDirectory_copiesNestedFiles() throws IOException {
        File src = temp.newFolder("src");
        File nested = new File(src, "storage");
        Assert.assertTrue(nested.mkdirs());
        try (FileOutputStream out = new FileOutputStream(new File(nested, "db.sqlite"))) {
            out.write(new byte[] { 1, 2, 3 });
        }
        File dst = temp.newFolder("dst");
        AndroidStorageManager.copyDirectory(src, dst);
        File copied = new File(dst, "storage/db.sqlite");
        Assert.assertTrue(copied.isFile());
        Assert.assertEquals(3L, copied.length());
    }
}
