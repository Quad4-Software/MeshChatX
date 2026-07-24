// SPDX-License-Identifier: 0BSD
package com.meshchatx;

import androidx.annotation.Nullable;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/**
 * Normalize and validate a MeshChatX remote backend origin for the Android shell.
 *
 * Empty or null means use the on-device local backend. Only http(s) origins are
 * accepted so the WebView never loads javascript or file schemes as the app root.
 */
public final class RemoteBackendUrl {
    public static final String LOCAL_BACKEND_URL = "https://127.0.0.1:8000";

    private RemoteBackendUrl() {}

    /**
     * @return normalized origin without trailing slash, or null for local backend
     */
    @Nullable
    public static String normalize(@Nullable String raw) {
        if (raw == null) {
            return null;
        }
        String trimmed = raw.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        URI uri;
        try {
            uri = new URI(trimmed);
        } catch (URISyntaxException e) {
            return null;
        }
        String scheme = uri.getScheme();
        if (scheme == null) {
            return null;
        }
        String schemeLower = scheme.toLowerCase(Locale.ROOT);
        if (!"http".equals(schemeLower) && !"https".equals(schemeLower)) {
            return null;
        }
        if (uri.getUserInfo() != null && !uri.getUserInfo().isEmpty()) {
            return null;
        }
        String host = uri.getHost();
        if (host == null || host.isEmpty()) {
            return null;
        }
        int port = uri.getPort();
        StringBuilder out = new StringBuilder();
        out.append(schemeLower).append("://").append(host.toLowerCase(Locale.ROOT));
        if (port != -1) {
            out.append(':').append(port);
        }
        String path = uri.getRawPath();
        if (path != null && !path.isEmpty() && !"/".equals(path)) {
            while (path.endsWith("/") && path.length() > 1) {
                path = path.substring(0, path.length() - 1);
            }
            out.append(path);
        }
        return out.toString();
    }

    public static boolean isValid(@Nullable String raw) {
        if (raw == null) {
            return true;
        }
        String trimmed = raw.trim();
        if (trimmed.isEmpty()) {
            return true;
        }
        return normalize(trimmed) != null;
    }

    public static String resolveEffectiveUrl(@Nullable String storedRemote) {
        String normalized = normalize(storedRemote);
        return normalized != null ? normalized : LOCAL_BACKEND_URL;
    }

    public static boolean isLocalBackendUrl(String url) {
        if (url == null) {
            return false;
        }
        String n = normalize(url);
        return LOCAL_BACKEND_URL.equals(n);
    }

    public static boolean isLoopbackHost(@Nullable String host) {
        if (host == null) {
            return false;
        }
        String h = host.toLowerCase(Locale.ROOT);
        return "127.0.0.1".equals(h)
            || "localhost".equals(h)
            || "[::1]".equals(h)
            || "::1".equals(h);
    }

    /**
     * True when url is the backend root or a same-origin path under it.
     */
    public static boolean matchesBackend(@Nullable String url, @Nullable String backendUrl) {
        if (url == null || backendUrl == null) {
            return false;
        }
        if ("about:blank".equalsIgnoreCase(url)) {
            return false;
        }
        URI page;
        URI backend;
        try {
            page = new URI(url);
            backend = new URI(backendUrl);
        } catch (URISyntaxException e) {
            return false;
        }
        if (page.getScheme() == null || backend.getScheme() == null) {
            return false;
        }
        if (!page.getScheme().equalsIgnoreCase(backend.getScheme())) {
            return false;
        }
        if (page.getHost() == null || backend.getHost() == null) {
            return false;
        }
        if (!page.getHost().equalsIgnoreCase(backend.getHost())) {
            return false;
        }
        int pagePort = effectivePort(page);
        int backendPort = effectivePort(backend);
        if (pagePort != backendPort) {
            return false;
        }
        String backendPath = backend.getRawPath();
        if (backendPath == null || backendPath.isEmpty() || "/".equals(backendPath)) {
            return true;
        }
        String pagePath = page.getRawPath();
        if (pagePath == null) {
            pagePath = "";
        }
        return pagePath.equals(backendPath)
            || pagePath.startsWith(backendPath.endsWith("/") ? backendPath : backendPath + "/");
    }

    private static int effectivePort(URI uri) {
        int port = uri.getPort();
        if (port != -1) {
            return port;
        }
        String scheme = uri.getScheme();
        if (scheme != null && scheme.equalsIgnoreCase("https")) {
            return 443;
        }
        return 80;
    }
}
