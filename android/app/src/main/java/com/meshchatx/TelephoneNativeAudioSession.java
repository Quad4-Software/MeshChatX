package com.meshchatx;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.os.Build;
import android.text.TextUtils;
import android.webkit.CookieManager;
import android.webkit.WebView;

import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;

import org.json.JSONObject;

import java.util.concurrent.atomic.AtomicBoolean;

import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

/**
 * Native mic send + speaker receive for {@code /ws/telephone/audio} (same protocol as the web
 * audio bridge). Do not use on the UI thread for {@link #start()} other than the initial schedule.
 */
public final class TelephoneNativeAudioSession {
    public static final int SAMPLE_RATE = 48000;
    private static final int IN_CHANNEL = AudioFormat.CHANNEL_IN_MONO;
    private static final int OUT_CHANNEL = AudioFormat.CHANNEL_OUT_MONO;
    private static final int FORMAT = AudioFormat.ENCODING_PCM_16BIT;

    private final Context appContext;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final AtomicBoolean pipelinesReady = new AtomicBoolean(false);
    private final MainActivity activity;

    @Nullable
    private WebSocket webSocket;
    @Nullable
    private AudioRecord audioRecord;
    @Nullable
    private AudioTrack audioTrack;
    @Nullable
    private Thread sendThread;
    @Nullable
    private Thread connectThread;
    @Nullable
    private AudioManager audioManager;
    @Nullable
    private AudioFocusRequest audioFocusRequest;
    private final AudioManager.OnAudioFocusChangeListener audioFocusListener = focusChange -> {
    };

    public TelephoneNativeAudioSession(MainActivity activity) {
        this.activity = activity;
        this.appContext = activity.getApplicationContext();
    }

    public static boolean canRun(Context ctx) {
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        return AudioRecord.getMinBufferSize(SAMPLE_RATE, IN_CHANNEL, FORMAT) > 0;
    }

    public boolean isActive() {
        return running.get();
    }

    public void start() {
        if (running.get() || connectThread != null) {
            return;
        }
        if (!canRun(appContext)) {
            postDispatch("error", "no_record_audio_permission", null);
            return;
        }
        connectThread = new Thread(
            () -> {
                try {
                    openWebSocket();
                } finally {
                    connectThread = null;
                }
            },
            "meshchatx-tel-ws"
        );
        connectThread.setPriority(Thread.NORM_PRIORITY);
        connectThread.start();
    }

    public void stop() {
        running.set(false);
        pipelinesReady.set(false);
        if (webSocket != null) {
            try {
                webSocket.close(1000, "client stop");
            } catch (Exception ignored) {
            }
            webSocket = null;
        }
        if (sendThread != null) {
            try {
                sendThread.join(2000L);
            } catch (InterruptedException ignored) {
            }
            sendThread = null;
        }
        releaseAudio();
    }

    private void postReleaseAfterStop() {
        if (sendThread == null) {
            releaseTx();
            return;
        }
        new Thread(
            () -> {
                if (sendThread != null) {
                    try {
                        sendThread.join(2000L);
                    } catch (InterruptedException ignored) {
                    }
                }
                releaseTx();
            },
            "meshchatx-tel-cleanup"
        ).start();
    }

    @SuppressWarnings("WeakerAccess")
    void onDestroy() {
        stop();
    }

    private void openWebSocket() {
        String cookie = "";
        try {
            String c = CookieManager.getInstance().getCookie("https://127.0.0.1:8000");
            if (!TextUtils.isEmpty(c)) {
                cookie = c;
            }
        } catch (Exception ignored) {
        }
        running.set(true);
        pipelinesReady.set(false);
        Request.Builder rb = new Request.Builder().url("wss://127.0.0.1:8000/ws/telephone/audio");
        if (!TextUtils.isEmpty(cookie)) {
            rb.addHeader("Cookie", cookie);
        }
        try {
            webSocket = LocalhostTrustOkHttpClient.get()
                .newWebSocket(
                    rb.build(),
                    new WebSocketListener() {
                        @Override
                        public void onOpen(WebSocket w, Response r) {
                            w.send("{\"type\":\"attach\"}");
                        }

                        @Override
                        public void onMessage(WebSocket w, String t) {
                            if (t == null) {
                                return;
                            }
                            try {
                                JSONObject o = new JSONObject(t);
                                if ("error".equals(o.optString("type"))) {
                                    String msg = o.optString("message", "error");
                                    if (msg.contains("Web audio is disabled")
                                        || (msg.equals("error") && o.length() < 2)) {
                                        // keep generic
                                    }
                                    postDispatch("error", "server", msg);
                                } else if ("web_audio.ready".equals(o.optString("type"))) {
                                    activity.runOnUiThread(TelephoneNativeAudioSession.this::onWebAudioReadyPipelines);
                                }
                            } catch (Exception e) {
                                if (t.contains("web_audio.ready") || t.contains("frame_ms")) {
                                    activity.runOnUiThread(TelephoneNativeAudioSession.this::onWebAudioReadyPipelines);
                                }
                            }
                        }

                        @Override
                        public void onMessage(WebSocket w, ByteString bytes) {
                            playPcm(bytes);
                        }

                        @Override
                        public void onFailure(WebSocket w, Throwable t, @Nullable Response r) {
                            webSocket = null;
                            running.set(false);
                            pipelinesReady.set(false);
                            String msg = t != null && t.getMessage() != null ? t.getMessage() : "connect_failed";
                            postDispatch("error", "websocket", msg);
                            postReleaseAfterStop();
                        }

                        @Override
                        public void onClosed(WebSocket w, int c, @Nullable String r) {
                            webSocket = null;
                            running.set(false);
                            pipelinesReady.set(false);
                            postDispatch("closed", null, null);
                            postReleaseAfterStop();
                        }
                    }
                );
        } catch (Exception e) {
            running.set(false);
            String m = e.getMessage() != null ? e.getMessage() : "okhttp";
            postDispatch("error", "connect", m);
        }
    }

    private void onWebAudioReadyPipelines() {
        if (pipelinesReady.getAndSet(true)) {
            return;
        }
        if (!running.get()) {
            return;
        }
        try {
            if (ContextCompat.checkSelfPermission(appContext, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                postDispatch("error", "no_record_audio_permission", null);
                return;
            }
            acquireCallAudioMode();
            int inBuf = Math.max(
                AudioRecord.getMinBufferSize(SAMPLE_RATE, IN_CHANNEL, FORMAT),
                4096
            );
            audioRecord = createVoiceAudioRecord(inBuf);
            if (audioRecord == null) {
                postDispatch("error", "no_record_audio_permission", null);
                return;
            }
            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                releaseTx();
                postDispatch("error", "record_init", null);
                return;
            }
            int outMin = AudioTrack.getMinBufferSize(SAMPLE_RATE, OUT_CHANNEL, FORMAT);
            if (outMin <= 0) {
                outMin = 4096;
            }
            int trackBuf = Math.max(outMin * 2, outMin);
            AudioAttributes playbackAttr = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build();
            AudioFormat trackFmt = new AudioFormat.Builder()
                .setSampleRate(SAMPLE_RATE)
                .setEncoding(FORMAT)
                .setChannelMask(OUT_CHANNEL)
                .build();
            audioTrack = new AudioTrack.Builder()
                .setAudioAttributes(playbackAttr)
                .setAudioFormat(trackFmt)
                .setBufferSizeInBytes(trackBuf)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build();
            if (audioTrack.getState() != AudioTrack.STATE_INITIALIZED) {
                releaseTx();
                postDispatch("error", "track_init", null);
                return;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                try {
                    audioTrack.setVolume(AudioTrack.getMaxVolume());
                } catch (Exception ignored) {
                }
            }
            try {
                audioRecord.startRecording();
            } catch (Exception e) {
                releaseTx();
                postDispatch("error", "record_start", e.getMessage() != null ? e.getMessage() : "");
                return;
            }
            try {
                audioTrack.play();
            } catch (Exception e) {
                releaseTx();
                postDispatch("error", "track_start", e.getMessage() != null ? e.getMessage() : "");
                return;
            }
            sendThread = new Thread(this::drainMicrophone, "meshchatx-tel-mic");
            sendThread.setPriority(Thread.NORM_PRIORITY);
            sendThread.start();
            postDispatch("ready", null, null);
        } catch (Exception e) {
            releaseTx();
            postDispatch("error", "setup", e.getMessage() != null ? e.getMessage() : "setup");
        }
    }

    @Nullable
    private AudioRecord createVoiceAudioRecord(int inBuf) {
        if (ContextCompat.checkSelfPermission(appContext, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return null;
        }
        return new AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            SAMPLE_RATE,
            IN_CHANNEL,
            FORMAT,
            inBuf * 2
        );
    }

    private void drainMicrophone() {
        byte[] buf = new byte[4096];
        while (running.get() && webSocket != null) {
            AudioRecord ar;
            WebSocket w;
            synchronized (this) {
                ar = audioRecord;
                w = webSocket;
            }
            if (ar == null || w == null) {
                break;
            }
            int n;
            try {
                n = ar.read(buf, 0, buf.length);
            } catch (Exception e) {
                break;
            }
            if (n > 0 && w != null) {
                try {
                    w.send(ByteString.of(buf, 0, n));
                } catch (Exception e) {
                    break;
                }
            } else if (n < 0) {
                break;
            }
        }
    }

    private void playPcm(ByteString bytes) {
        if (bytes == null || bytes.size() == 0) {
            return;
        }
        AudioTrack at;
        synchronized (this) {
            at = audioTrack;
        }
        if (at == null) {
            return;
        }
        byte[] raw = bytes.toByteArray();
        int off = 0;
        int left = raw.length;
        while (left > 0) {
            if (!running.get()) {
                return;
            }
            synchronized (this) {
                at = audioTrack;
            }
            if (at == null) {
                return;
            }
            int written = 0;
            try {
                written = at.write(raw, off, left);
            } catch (Exception e) {
                return;
            }
            if (written < 0) {
                return;
            }
            if (written == 0) {
                Thread.yield();
                continue;
            }
            off += written;
            left -= written;
        }
    }

    private void postDispatch(String a, @Nullable String b, @Nullable String c) {
        activity.runOnUiThread(() -> dispatchToPage(a, b, c));
    }

    private void dispatchToPage(String kind, @Nullable String sub, @Nullable String detail) {
        try {
            WebView wv = activity.getWebViewForNativeBridge();
            if (wv == null) {
                return;
            }
            JSONObject o = new JSONObject();
            o.put("type", "meshchatx-native-telephone-audio");
            o.put("kind", kind);
            if (sub != null) {
                o.put("sub", sub);
            }
            if (detail != null) {
                o.put("detail", detail);
            }
            String j = o.toString();
            wv.evaluateJavascript(
                "try{var d=" + j + ";"
                    + "window.dispatchEvent(new CustomEvent('meshchatx-native-telephone-audio',{detail:d}));}catch(e){}",
                null
            );
        } catch (Exception ignored) {
        }
    }

    private void acquireCallAudioMode() {
        releaseCallAudioMode();
        audioManager = (AudioManager) appContext.getSystemService(Context.AUDIO_SERVICE);
        if (audioManager == null) {
            return;
        }
        try {
            audioManager.setMode(AudioManager.MODE_IN_COMMUNICATION);
        } catch (Exception ignored) {
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                AudioAttributes aa = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build();
                audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(aa)
                    .setAcceptsDelayedFocusGain(false)
                    .build();
                audioManager.requestAudioFocus(audioFocusRequest);
            } else {
                audioManager.requestAudioFocus(
                    audioFocusListener,
                    AudioManager.STREAM_VOICE_CALL,
                    AudioManager.AUDIOFOCUS_GAIN_TRANSIENT
                );
            }
        } catch (Exception ignored) {
        }
    }

    private void releaseCallAudioMode() {
        if (audioManager == null) {
            return;
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && audioFocusRequest != null) {
                audioManager.abandonAudioFocusRequest(audioFocusRequest);
            } else {
                audioManager.abandonAudioFocus(audioFocusListener);
            }
        } catch (Exception ignored) {
        }
        try {
            audioManager.setMode(AudioManager.MODE_NORMAL);
        } catch (Exception ignored) {
        }
        audioFocusRequest = null;
        audioManager = null;
    }

    private void releaseTx() {
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
        if (audioTrack != null) {
            try {
                if (audioTrack.getPlayState() == AudioTrack.PLAYSTATE_PLAYING) {
                    audioTrack.stop();
                }
            } catch (Exception ignored) {
            }
            try {
                audioTrack.release();
            } catch (Exception ignored) {
            }
            audioTrack = null;
        }
        releaseCallAudioMode();
    }

    private void releaseAudio() {
        releaseTx();
    }
}