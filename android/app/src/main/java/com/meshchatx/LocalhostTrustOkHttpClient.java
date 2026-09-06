package com.meshchatx;

import java.security.SecureRandom;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.concurrent.TimeUnit;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import okhttp3.OkHttpClient;

/**
 * OkHttp for HTTPS to the embedded MeshChatX server on 127.0.0.1 only (self-signed cert, same
 * as WebView SSL ignore). Do not use for public hosts.
 */
public final class LocalhostTrustOkHttpClient {
    private static OkHttpClient instance;

    private LocalhostTrustOkHttpClient() {
    }

    public static synchronized OkHttpClient get() {
        if (instance == null) {
            instance = build();
        }
        return instance;
    }

    @SuppressWarnings("CustomX509TrustManager")
    private static OkHttpClient build() {
        try {
            final TrustManager[] allTrust = new TrustManager[] {
                new X509TrustManager() {
                    @Override
                    @SuppressWarnings("MethodDoesntCallSuperMethod")
                    public void checkClientTrusted(X509Certificate[] chain, String authType)
                            throws CertificateException {
                        validate(chain);
                    }

                    @Override
                    @SuppressWarnings("MethodDoesntCallSuperMethod")
                    public void checkServerTrusted(X509Certificate[] chain, String authType)
                            throws CertificateException {
                        validate(chain);
                    }

                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[0];
                    }

                    private void validate(X509Certificate[] chain) throws CertificateException {
                        if (chain == null || chain.length == 0) {
                            throw new CertificateException("empty certificate chain");
                        }
                        X509Certificate c = chain[0];
                        c.checkValidity();
                        try {
                            c.verify(c.getPublicKey());
                        } catch (java.security.GeneralSecurityException e) {
                            throw new CertificateException(
                                "not a self-signed MeshChatX certificate", e
                            );
                        }
                        String dn = c.getSubjectX500Principal().getName();
                        if (!dn.contains("O=Reticulum MeshChatX") || !dn.contains("CN=localhost")) {
                            throw new CertificateException("not a MeshChatX localhost certificate");
                        }
                    }
                }
            };
            SSLContext sc = SSLContext.getInstance("TLS");
            sc.init(null, allTrust, new SecureRandom());
            return new OkHttpClient.Builder()
                .sslSocketFactory(sc.getSocketFactory(), (X509TrustManager) allTrust[0])
                .hostnameVerifier(
                    (hostname, session) ->
                        "127.0.0.1".equals(hostname) || "localhost".equalsIgnoreCase(hostname)
                )
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .writeTimeout(0, TimeUnit.MILLISECONDS)
                .connectTimeout(15, TimeUnit.SECONDS)
                .callTimeout(0, TimeUnit.MILLISECONDS)
                .pingInterval(0, TimeUnit.SECONDS)
                .build();
        } catch (Exception e) {
            throw new IllegalStateException("localhost OkHttp", e);
        }
    }
}
