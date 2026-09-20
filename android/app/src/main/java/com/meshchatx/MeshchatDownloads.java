package com.meshchatx;

import android.Manifest;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;

import androidx.core.content.ContextCompat;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLConnection;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Persists downloads into the user-visible Downloads collection.
 * On API 29+ inserts into MediaStore.Downloads. On older devices writes to the
 * public Downloads directory when WRITE_EXTERNAL_STORAGE is granted, falling
 * back to the app-specific external files dir otherwise. Also holds chunked
 * save sessions so the JS bridge can stream large files without carrying the
 * whole payload as one base64 string.
 */
final class MeshchatDownloads {

    private static final ConcurrentHashMap<String, PendingSave> pendingSaves = new ConcurrentHashMap<>();

    private MeshchatDownloads() {}

    private static final class PendingSave {
        final String fileName;
        final File tempFile;
        final FileOutputStream output;

        PendingSave(String fileName, File tempFile, FileOutputStream output) {
            this.fileName = fileName;
            this.tempFile = tempFile;
            this.output = output;
        }
    }

    static String begin(Context context, String fileName) throws IOException {
        String saveId = UUID.randomUUID().toString();
        File temp = File.createTempFile("mcx-dl-", ".part", context.getCacheDir());
        pendingSaves.put(saveId, new PendingSave(fileName, temp, new FileOutputStream(temp)));
        return saveId;
    }

    static void append(String saveId, String base64Data) throws IOException {
        PendingSave pending = pendingSaves.get(saveId);
        if (pending == null) {
            throw new IOException("unknown save id");
        }
        byte[] raw = Base64.decode(base64Data, Base64.DEFAULT);
        pending.output.write(raw);
    }

    static final class FinishedSave {
        final Uri uri;
        final String fileName;

        FinishedSave(Uri uri, String fileName) {
            this.uri = uri;
            this.fileName = fileName;
        }
    }

    static FinishedSave finish(Context context, String saveId) throws IOException {
        PendingSave pending = pendingSaves.remove(saveId);
        if (pending == null) {
            throw new IOException("unknown save id");
        }
        IOException closeError = null;
        try {
            pending.output.close();
        } catch (IOException e) {
            closeError = e;
        }
        try {
            if (closeError == null) {
                Uri uri = persist(context, pending.fileName, pending.tempFile);
                return new FinishedSave(uri, pending.fileName);
            }
            throw closeError;
        } finally {
            pending.tempFile.delete();
        }
    }

    static String fileNameFor(String saveId) {
        PendingSave pending = pendingSaves.get(saveId);
        return pending != null ? pending.fileName : null;
    }

    static void abort(String saveId) {
        PendingSave pending = pendingSaves.remove(saveId);
        if (pending == null) {
            return;
        }
        try {
            pending.output.close();
        } catch (IOException ignored) {
        }
        pending.tempFile.delete();
    }

    static Uri persist(Context context, String fileName, byte[] data) throws IOException {
        String safe = MeshchatDownloadUtils.sanitizeFileName(fileName);
        ContentResolver resolver = context.getContentResolver();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            Uri uri = insertPendingDownload(resolver, safe);
            try (OutputStream out = resolver.openOutputStream(uri)) {
                if (out == null) {
                    throw new IOException("openOutputStream failed");
                }
                out.write(data);
            } catch (IOException | RuntimeException e) {
                resolver.delete(uri, null, null);
                throw e instanceof IOException ? (IOException) e : new IOException("write failed", e);
            }
            markDownloadComplete(resolver, uri);
            return uri;
        }
        return persistLegacy(context, safe, data, null);
    }

    static Uri persist(Context context, String fileName, File sourceFile) throws IOException {
        String safe = MeshchatDownloadUtils.sanitizeFileName(fileName);
        ContentResolver resolver = context.getContentResolver();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            Uri uri = insertPendingDownload(resolver, safe);
            try (InputStream in = new FileInputStream(sourceFile);
                 OutputStream out = resolver.openOutputStream(uri)) {
                if (out == null) {
                    throw new IOException("openOutputStream failed");
                }
                copy(in, out);
            } catch (IOException | RuntimeException e) {
                resolver.delete(uri, null, null);
                throw e instanceof IOException ? (IOException) e : new IOException("write failed", e);
            }
            markDownloadComplete(resolver, uri);
            return uri;
        }
        return persistLegacy(context, safe, null, sourceFile);
    }

    private static Uri insertPendingDownload(ContentResolver resolver, String safe) throws IOException {
        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, safe);
        String mime = URLConnection.guessContentTypeFromName(safe);
        values.put(MediaStore.MediaColumns.MIME_TYPE, mime != null ? mime : "application/octet-stream");
        values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
        values.put(MediaStore.MediaColumns.IS_PENDING, 1);
        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) {
            throw new IOException("MediaStore insert failed");
        }
        return uri;
    }

    private static void markDownloadComplete(ContentResolver resolver, Uri uri) {
        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.IS_PENDING, 0);
        resolver.update(uri, values, null, null);
    }

    private static Uri persistLegacy(Context context, String safe, byte[] data, File sourceFile)
        throws IOException {
        File dir = legacyDownloadDir(context);
        if (dir == null) {
            throw new IOException("no download directory");
        }
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IOException("mkdirs failed");
        }
        File target = uniqueTarget(dir, safe);
        if (data != null) {
            try (FileOutputStream fos = new FileOutputStream(target)) {
                fos.write(data);
            }
        } else {
            try (InputStream in = new FileInputStream(sourceFile);
                 OutputStream out = new FileOutputStream(target)) {
                copy(in, out);
            }
        }
        MediaScannerConnection.scanFile(context, new String[] {target.getAbsolutePath()}, null, null);
        return Uri.fromFile(target);
    }

    private static File legacyDownloadDir(Context context) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE)
            == PackageManager.PERMISSION_GRANTED) {
            return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
        }
        return context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
    }

    private static File uniqueTarget(File dir, String safe) {
        File target = new File(dir, safe);
        if (!target.exists()) {
            return target;
        }
        int dot = safe.lastIndexOf('.');
        String stem = dot > 0 ? safe.substring(0, dot) : safe;
        String ext = dot > 0 ? safe.substring(dot) : "";
        for (int i = 1; i < 100; i++) {
            File candidate = new File(dir, stem + " (" + i + ")" + ext);
            if (!candidate.exists()) {
                return candidate;
            }
        }
        return target;
    }

    private static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] buffer = new byte[64 * 1024];
        int read;
        while ((read = in.read(buffer)) >= 0) {
            out.write(buffer, 0, read);
        }
    }
}
