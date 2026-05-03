package com.meshchatx;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.util.Base64;

import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * 16-bit mono PCM at 48kHz, packaged as RIFF WAV. Capped in duration to keep memory use bounded.
 */
public final class WavPcmAttachmentRecorder {
    public static final int SAMPLE_RATE = 48000;
    public static final int MAX_DURATION_MS = 120_000;
    private static final int CHANNEL = AudioFormat.CHANNEL_IN_MONO;
    private static final int ENCODING = AudioFormat.ENCODING_PCM_16BIT;
    private static final int MAX_RAW_PCM = SAMPLE_RATE * 2 * (MAX_DURATION_MS / 1000);
    private static final int IO_BYTES = 4096;

    private final Context ctx;
    private final java.util.concurrent.atomic.AtomicBoolean rec = new java.util.concurrent.atomic.AtomicBoolean(false);
    @Nullable
    private AudioRecord audioRecord;
    @Nullable
    private Thread thread;
    private final ByteArrayOutputStream pcm = new ByteArrayOutputStream(65536);

    public WavPcmAttachmentRecorder(Context ctx) {
        this.ctx = ctx.getApplicationContext();
    }

    public static boolean canStart(Context c) {
        if (ContextCompat.checkSelfPermission(c, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        return AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL, ENCODING) > 0;
    }

    public String start() {
        if (rec.get()) {
            return "err: already recording";
        }
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return "err: record_audio";
        }
        int min = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL, ENCODING);
        if (min <= 0) {
            return "err: buffer";
        }
        try {
            audioRecord = new AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                SAMPLE_RATE,
                CHANNEL,
                ENCODING,
                min * 2
            );
            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                return "err: state";
            }
            pcm.reset();
            rec.set(true);
            thread = new Thread(
                this::pump,
                "meshchatx-attach-pcm"
            );
            audioRecord.startRecording();
            thread.start();
        } catch (Exception e) {
            stopInternal();
            return e.getMessage() != null ? e.getMessage() : "err: start";
        }
        return "ok";
    }

    private void pump() {
        byte[] buf = new byte[IO_BYTES];
        while (rec.get() && audioRecord != null) {
            int n;
            try {
                n = audioRecord.read(buf, 0, buf.length);
            } catch (Exception e) {
                break;
            }
            if (n <= 0) {
                break;
            }
            if (pcm.size() + n > MAX_RAW_PCM) {
                rec.set(false);
                break;
            }
            try {
                pcm.write(buf, 0, n);
            } catch (Exception e) {
                break;
            }
        }
    }

    @Nullable
    public String stopBase64Wav() {
        if (!rec.get() && thread == null && audioRecord == null) {
            return null;
        }
        rec.set(false);
        if (thread != null) {
            try {
                thread.join(4000L);
            } catch (InterruptedException ignored) {
            }
        }
        thread = null;
        if (audioRecord != null) {
            try {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord.stop();
                }
            } catch (Exception ignored) {
            }
            try {
                audioRecord.release();
            } catch (Exception ignored) {
            }
            audioRecord = null;
        }
        int rawLen = pcm.size();
        if (rawLen == 0) {
            return "";
        }
        try {
            byte[] raw = pcm.toByteArray();
            return Base64.encodeToString(wrapWav(raw, SAMPLE_RATE), Base64.NO_WRAP);
        } catch (OutOfMemoryError e) {
            return null;
        } finally {
            try {
                pcm.reset();
            } catch (Exception ignored) {
            }
        }
    }

    private void stopInternal() {
        rec.set(false);
        if (audioRecord != null) {
            try {
                audioRecord.release();
            } catch (Exception ignored) {
            }
            audioRecord = null;
        }
    }

    public void cancel() {
        rec.set(false);
        if (thread != null) {
            try {
                thread.join(2000L);
            } catch (InterruptedException ignored) {
            }
        }
        thread = null;
        stopInternal();
        try {
            pcm.reset();
        } catch (Exception ignored) {
        }
    }

    public boolean isRunning() {
        return rec.get();
    }

    static byte[] wrapWav(byte[] pcmS16, int rate) {
        int data = pcmS16.length;
        int rsize = 36 + data;
        int byteRate = rate * 2;
        ByteBuffer bb = ByteBuffer.allocate(44 + data).order(ByteOrder.LITTLE_ENDIAN);
        bb.put("RIFF".getBytes());
        bb.putInt(rsize);
        bb.put("WAVE".getBytes());
        bb.put("fmt ".getBytes());
        bb.putInt(16);
        bb.putShort((short) 1);
        bb.putShort((short) 1);
        bb.putInt(rate);
        bb.putInt(byteRate);
        bb.putShort((short) 2);
        bb.putShort((short) 16);
        bb.put("data".getBytes());
        bb.putInt(data);
        bb.put(pcmS16);
        return bb.array();
    }
}
