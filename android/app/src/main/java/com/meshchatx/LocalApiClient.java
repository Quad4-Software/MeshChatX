// SPDX-License-Identifier: 0BSD
package com.meshchatx;

import android.content.Context;
import android.content.SharedPreferences;
import android.text.TextUtils;
import android.webkit.CookieManager;

import androidx.annotation.Nullable;

import org.json.JSONObject;

import java.io.IOException;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * Cookie + CSRF HTTP calls to the MeshChatX backend from native code
 * (Android Auto reply / mark-as-read, and similar background paths).
 */
public final class LocalApiClient {
    private static final String SHELL_PREFS = "meshchatx_shell";
    private static final String PREF_REMOTE_BACKEND_URL = "remote_backend_url";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private static volatile OkHttpClient remoteClient;
    private static volatile OkHttpClient localApiClient;

    private LocalApiClient() {
    }

    public static String resolveBackendBase(Context ctx) {
        SharedPreferences prefs =
            ctx.getApplicationContext().getSharedPreferences(SHELL_PREFS, Context.MODE_PRIVATE);
        return RemoteBackendUrl.resolveEffectiveUrl(
            RemoteBackendUrl.normalize(prefs.getString(PREF_REMOTE_BACKEND_URL, null))
        );
    }

    public static boolean markConversationRead(Context ctx, String destinationHash) {
        String hash = normalizeDestinationHash(destinationHash);
        if (hash == null) {
            return false;
        }
        String base = resolveBackendBase(ctx);
        try {
            String csrf = fetchCsrfToken(base);
            if (csrf == null) {
                return false;
            }
            Request.Builder rb =
                new Request.Builder()
                    .url(base + "/api/v1/lxmf/conversations/" + hash + "/mark-as-read")
                    .post(RequestBody.create("{}", JSON))
                    .header("X-CSRF-Token", csrf)
                    .header("Accept", "application/json");
            attachCookie(rb, base);
            try (Response response = clientFor(base).newCall(rb.build()).execute()) {
                return response.isSuccessful();
            }
        } catch (Exception ignored) {
            return false;
        }
    }

    public static boolean sendLxmfText(Context ctx, String destinationHash, String content) {
        String hash = normalizeDestinationHash(destinationHash);
        if (hash == null || TextUtils.isEmpty(content)) {
            return false;
        }
        String base = resolveBackendBase(ctx);
        try {
            String csrf = fetchCsrfToken(base);
            if (csrf == null) {
                return false;
            }
            JSONObject lxmf = new JSONObject();
            lxmf.put("destination_hash", hash);
            lxmf.put("content", content);
            JSONObject body = new JSONObject();
            body.put("lxmf_message", lxmf);
            Request.Builder rb =
                new Request.Builder()
                    .url(base + "/api/v1/lxmf-messages/send")
                    .post(RequestBody.create(body.toString(), JSON))
                    .header("X-CSRF-Token", csrf)
                    .header("Accept", "application/json")
                    .header("Content-Type", "application/json");
            attachCookie(rb, base);
            try (Response response = clientFor(base).newCall(rb.build()).execute()) {
                return response.isSuccessful();
            }
        } catch (Exception ignored) {
            return false;
        }
    }

    @Nullable
    static String normalizeDestinationHash(@Nullable String raw) {
        if (raw == null) {
            return null;
        }
        String hash = raw.trim().toLowerCase(Locale.ROOT);
        if (hash.length() < 8 || hash.length() > 64) {
            return null;
        }
        for (int i = 0; i < hash.length(); i++) {
            char c = hash.charAt(i);
            if ((c < '0' || c > '9') && (c < 'a' || c > 'f')) {
                return null;
            }
        }
        return hash;
    }

    @Nullable
    private static String fetchCsrfToken(String base) throws IOException {
        Request.Builder rb =
            new Request.Builder()
                .url(base + "/api/v1/auth/csrf")
                .get()
                .header("Accept", "application/json");
        attachCookie(rb, base);
        try (Response response = clientFor(base).newCall(rb.build()).execute()) {
            if (!response.isSuccessful() || response.body() == null) {
                return null;
            }
            String text = response.body().string();
            JSONObject json = new JSONObject(text);
            String token = json.optString("csrf_token", "");
            return TextUtils.isEmpty(token) ? null : token;
        } catch (Exception e) {
            if (e instanceof IOException) {
                throw (IOException) e;
            }
            return null;
        }
    }

    private static void attachCookie(Request.Builder rb, String base) {
        try {
            String cookie = CookieManager.getInstance().getCookie(base);
            if (!TextUtils.isEmpty(cookie)) {
                rb.header("Cookie", cookie);
            }
        } catch (Exception ignored) {
        }
    }

    private static OkHttpClient clientFor(String baseUrl) {
        if (isLocalBackend(baseUrl)) {
            return localApiClient();
        }
        return remoteApiClient();
    }

    private static boolean isLocalBackend(String baseUrl) {
        try {
            java.net.URI uri = java.net.URI.create(baseUrl);
            return RemoteBackendUrl.isLoopbackHost(uri.getHost());
        } catch (Exception e) {
            return true;
        }
    }

    private static OkHttpClient localApiClient() {
        OkHttpClient existing = localApiClient;
        if (existing != null) {
            return existing;
        }
        synchronized (LocalApiClient.class) {
            if (localApiClient == null) {
                localApiClient =
                    LocalhostTrustOkHttpClient.get()
                        .newBuilder()
                        .connectTimeout(15, TimeUnit.SECONDS)
                        .readTimeout(30, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .callTimeout(45, TimeUnit.SECONDS)
                        .build();
            }
            return localApiClient;
        }
    }

    private static OkHttpClient remoteApiClient() {
        OkHttpClient existing = remoteClient;
        if (existing != null) {
            return existing;
        }
        synchronized (LocalApiClient.class) {
            if (remoteClient == null) {
                remoteClient =
                    new OkHttpClient.Builder()
                        .connectTimeout(15, TimeUnit.SECONDS)
                        .readTimeout(30, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .callTimeout(45, TimeUnit.SECONDS)
                        .build();
            }
            return remoteClient;
        }
    }
}
