package com.meshchatx;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.appcompat.app.AppCompatActivity;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private ProgressBar progressBar;
    private ImageView loadingLogo;
    private TextView loadingText;
    private TextView errorText;
    private static final String SERVER_URL = "https://127.0.0.1:8000";
    private static final int SERVER_PORT = 8000;
    private static final int RUNTIME_PERMISSIONS_REQUEST_CODE = 1001;
    private static final int MICROPHONE_WEB_PERMISSION_REQUEST_CODE = 1002;
    private static final String PREFS_NAME = "meshchatx";
    private static final String PREF_BATTERY_OPT_REQUESTED = "battery_opt_requested";
    private static final int MAX_CONNECTION_ATTEMPTS = 120;
    private static final long CONNECTION_RETRY_INITIAL_DELAY_MS = 500;
    private static final long CONNECTION_RETRY_MAX_DELAY_MS = 5000;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private PermissionRequest pendingWebPermissionRequest = null;
    private ValueCallback<Uri[]> filePathCallback = null;
    private boolean startupRequestHadLoadError = false;
    private boolean startupPageLoaded = false;
    private boolean backendFailed = false;
    private int connectionAttempts = 0;
    private static final String[] STARTUP_PHASES = new String[] {
        "Starting MeshChatX...",
        "Initializing Reticulum network stack...",
        "Loading MeshChatX frontend...",
        "Establishing secure local connection...",
        "Finalizing startup..."
    };
    private final ActivityResultLauncher<Intent> filePickerLauncher = registerForActivityResult(
        new ActivityResultContracts.StartActivityForResult(),
        result -> {
            Uri[] selection = null;
            if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                Intent data = result.getData();
                if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    selection = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        selection[i] = data.getClipData().getItemAt(i).getUri();
                    }
                } else if (data.getData() != null) {
                    selection = new Uri[] { data.getData() };
                }
            }
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(selection);
                filePathCallback = null;
            }
        }
    );

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        loadingLogo = findViewById(R.id.loadingLogo);
        loadingText = findViewById(R.id.loadingText);
        errorText = findViewById(R.id.errorText);
        webView.setVisibility(android.view.View.INVISIBLE);
        showLoading("Starting MeshChatX backend...");

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        requestRuntimePermissionsIfNeeded();
        requestBatteryOptimizationExemptionIfNeeded();

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (!isStartupRequest(url)) {
                    return;
                }
                if (startupRequestHadLoadError) {
                    return;
                }
                startupPageLoaded = true;
                mainHandler.removeCallbacksAndMessages(null);
                webView.setVisibility(android.view.View.VISIBLE);
                loadingLogo.setVisibility(android.view.View.GONE);
                progressBar.setVisibility(android.view.View.GONE);
                loadingText.setVisibility(android.view.View.GONE);
                errorText.setVisibility(android.view.View.GONE);
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (isStartupRequest(url)) {
                    startupRequestHadLoadError = false;
                    if (!startupPageLoaded) {
                        webView.setVisibility(android.view.View.INVISIBLE);
                    }
                }
                progressBar.setVisibility(android.view.View.VISIBLE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request != null && request.isForMainFrame() && isStartupRequest(request.getUrl().toString())) {
                    startupRequestHadLoadError = true;
                    view.stopLoading();
                    view.loadUrl("about:blank");
                    if (backendFailed && !startupPageLoaded) {
                        CharSequence description = (error != null) ? error.getDescription() : "Unknown error";
                        showStartupError("WebView failed to load MeshChatX: " + description);
                    }
                }
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                super.onReceivedError(view, errorCode, description, failingUrl);
                if (isStartupRequest(failingUrl) && !startupPageLoaded) {
                    startupRequestHadLoadError = true;
                    view.stopLoading();
                    view.loadUrl("about:blank");
                    if (backendFailed) {
                        showStartupError("WebView failed to load MeshChatX: " + description);
                    }
                }
            }

            @SuppressLint("WebViewClientOnReceivedSslError")
            @Override
            public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
                // Ignore SSL certificate errors for localhost
                handler.proceed();
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    if (request == null) {
                        return;
                    }

                    boolean needsAudioCapture = false;
                    for (String resource : request.getResources()) {
                        if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                            needsAudioCapture = true;
                            break;
                        }
                    }

                    if (!needsAudioCapture) {
                        request.grant(request.getResources());
                        return;
                    }

                    if (ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.RECORD_AUDIO)
                        == PackageManager.PERMISSION_GRANTED) {
                        request.grant(request.getResources());
                        return;
                    }

                    pendingWebPermissionRequest = request;
                    requestMicrophonePermissionForWebView();
                });
            }

            @Override
            public boolean onShowFileChooser(
                WebView webView,
                ValueCallback<Uri[]> filePathCallback,
                WebChromeClient.FileChooserParams fileChooserParams
            ) {
                if (MainActivity.this.filePathCallback != null) {
                    MainActivity.this.filePathCallback.onReceiveValue(null);
                }
                MainActivity.this.filePathCallback = filePathCallback;

                Intent chooserIntent;
                try {
                    chooserIntent = fileChooserParams != null
                        ? fileChooserParams.createIntent()
                        : new Intent(Intent.ACTION_GET_CONTENT);
                } catch (Exception e) {
                    chooserIntent = new Intent(Intent.ACTION_GET_CONTENT);
                }
                chooserIntent.addCategory(Intent.CATEGORY_OPENABLE);
                if (chooserIntent.getType() == null) {
                    chooserIntent.setType("*/*");
                }
                if (fileChooserParams != null && fileChooserParams.getAcceptTypes() != null) {
                    chooserIntent.putExtra(Intent.EXTRA_MIME_TYPES, fileChooserParams.getAcceptTypes());
                }
                chooserIntent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);

                try {
                    filePickerLauncher.launch(chooserIntent);
                } catch (ActivityNotFoundException e) {
                    if (MainActivity.this.filePathCallback != null) {
                        MainActivity.this.filePathCallback.onReceiveValue(null);
                        MainActivity.this.filePathCallback = null;
                    }
                    Toast.makeText(MainActivity.this, "No file picker available", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });

        startMeshChatServer();
        scheduleConnectionRetry("Connecting to local server...");
    }

    private void requestRuntimePermissionsIfNeeded() {
        List<String> missingPermissions = new ArrayList<>();
        addIfMissing(missingPermissions, Manifest.permission.RECORD_AUDIO);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            addIfMissing(missingPermissions, Manifest.permission.BLUETOOTH_CONNECT);
            addIfMissing(missingPermissions, Manifest.permission.BLUETOOTH_SCAN);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            addIfMissing(missingPermissions, Manifest.permission.POST_NOTIFICATIONS);
        }
        if (!missingPermissions.isEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                missingPermissions.toArray(new String[0]),
                RUNTIME_PERMISSIONS_REQUEST_CODE
            );
        }
    }

    private void requestMicrophonePermissionForWebView() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            if (pendingWebPermissionRequest != null) {
                pendingWebPermissionRequest.grant(pendingWebPermissionRequest.getResources());
                pendingWebPermissionRequest = null;
            }
            return;
        }

        ActivityCompat.requestPermissions(
            this,
            new String[] { Manifest.permission.RECORD_AUDIO },
            MICROPHONE_WEB_PERMISSION_REQUEST_CODE
        );
    }

    private void requestBatteryOptimizationExemptionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return;
        }

        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        if (powerManager != null && powerManager.isIgnoringBatteryOptimizations(getPackageName())) {
            return;
        }

        boolean requestedBefore = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getBoolean(PREF_BATTERY_OPT_REQUESTED, false);
        if (requestedBefore) {
            return;
        }
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit().putBoolean(PREF_BATTERY_OPT_REQUESTED, true).apply();

        Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
        intent.setData(Uri.parse("package:" + getPackageName()));
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException e) {
            try {
                startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            } catch (ActivityNotFoundException ignored) {
                Toast.makeText(this, "Open battery settings and allow unrestricted background usage for MeshChatX", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void addIfMissing(List<String> missingPermissions, String permission) {
        if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
            missingPermissions.add(permission);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == MICROPHONE_WEB_PERMISSION_REQUEST_CODE) {
            if (grantResults.length == 0 || grantResults[0] != PackageManager.PERMISSION_GRANTED) {
                if (pendingWebPermissionRequest != null) {
                    pendingWebPermissionRequest.deny();
                    pendingWebPermissionRequest = null;
                }
                return;
            }
            if (pendingWebPermissionRequest != null) {
                pendingWebPermissionRequest.grant(pendingWebPermissionRequest.getResources());
                pendingWebPermissionRequest = null;
            }
            return;
        }
        if (requestCode != RUNTIME_PERMISSIONS_REQUEST_CODE) {
            return;
        }
        for (int i = 0; i < permissions.length; i++) {
            if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                if (Manifest.permission.RECORD_AUDIO.equals(permissions[i]) && pendingWebPermissionRequest != null) {
                    pendingWebPermissionRequest.deny();
                    pendingWebPermissionRequest = null;
                }
            }
        }
        if (
            pendingWebPermissionRequest != null &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        ) {
            pendingWebPermissionRequest.grant(pendingWebPermissionRequest.getResources());
            pendingWebPermissionRequest = null;
        }
    }

    private void startMeshChatServer() {
        new Thread(() -> {
            try {
                Python py = Python.getInstance();
                String appFilesDir = getFilesDir().getAbsolutePath();
                py.getModule("meshchat_wrapper").callAttr("start_server", SERVER_PORT, appFilesDir);
            } catch (Exception e) {
                backendFailed = true;
                showStartupError("MeshChatX backend failed:\n" + toStackTrace(e));
            }
        }).start();
    }

    private boolean isStartupRequest(String url) {
        return url != null && url.startsWith(SERVER_URL);
    }

    private void scheduleConnectionRetry(String message) {
        if (startupPageLoaded || backendFailed) {
            return;
        }
        showLoading(message + " (" + (connectionAttempts + 1) + "/" + MAX_CONNECTION_ATTEMPTS + ")");
        long retryDelayMs = Math.min(
            CONNECTION_RETRY_MAX_DELAY_MS,
            CONNECTION_RETRY_INITIAL_DELAY_MS + (connectionAttempts * 250L)
        );
        mainHandler.postDelayed(() -> {
            if (startupPageLoaded || backendFailed) {
                return;
            }
            connectionAttempts += 1;
            if (connectionAttempts > MAX_CONNECTION_ATTEMPTS) {
                showStartupError("Failed to connect to local MeshChatX server after waiting for startup.");
                return;
            }
            webView.loadUrl(SERVER_URL);
            scheduleConnectionRetry("Retrying connection...");
        }, retryDelayMs);
    }

    private String toStackTrace(Throwable error) {
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        error.printStackTrace(pw);
        pw.flush();
        return sw.toString();
    }

    private void showStartupError(String message) {
        runOnUiThread(() -> {
            mainHandler.removeCallbacksAndMessages(null);
            webView.setVisibility(android.view.View.INVISIBLE);
            loadingLogo.setVisibility(android.view.View.GONE);
            progressBar.setVisibility(android.view.View.GONE);
            loadingText.setVisibility(android.view.View.GONE);
            if (errorText != null) {
                errorText.setText(message);
                errorText.setVisibility(android.view.View.VISIBLE);
            }
        });
    }

    private void showLoading(String message) {
        runOnUiThread(() -> {
            if (startupPageLoaded) {
                return;
            }
            webView.setVisibility(android.view.View.INVISIBLE);
            if (loadingLogo != null) {
                loadingLogo.setVisibility(android.view.View.VISIBLE);
            }
            progressBar.setVisibility(android.view.View.VISIBLE);
            errorText.setVisibility(android.view.View.GONE);
            if (loadingText != null) {
                loadingText.setText(formatLoadingMessage(message));
                loadingText.setVisibility(android.view.View.VISIBLE);
            }
        });
    }

    private String formatLoadingMessage(String fallbackMessage) {
        int phaseIndex = Math.min(
            STARTUP_PHASES.length - 1,
            (connectionAttempts * STARTUP_PHASES.length) / Math.max(1, MAX_CONNECTION_ATTEMPTS)
        );
        String phase = STARTUP_PHASES[phaseIndex];
        if (connectionAttempts == 0) {
            return phase;
        }
        return phase + " (" + connectionAttempts + "/" + MAX_CONNECTION_ATTEMPTS + ")";
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        mainHandler.removeCallbacksAndMessages(null);
        if (pendingWebPermissionRequest != null) {
            pendingWebPermissionRequest.deny();
            pendingWebPermissionRequest = null;
        }
        if (filePathCallback != null) {
            filePathCallback.onReceiveValue(null);
            filePathCallback = null;
        }
        if (webView != null) {
            webView.destroy();
        }
    }
}

