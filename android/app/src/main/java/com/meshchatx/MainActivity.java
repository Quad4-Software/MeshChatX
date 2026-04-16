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
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
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
    private TextView loadingText;
    private TextView errorText;
    private static final String SERVER_URL = "https://127.0.0.1:8000";
    private static final int SERVER_PORT = 8000;
    private static final int RUNTIME_PERMISSIONS_REQUEST_CODE = 1001;
    private static final int MAX_CONNECTION_ATTEMPTS = 30;
    private static final long CONNECTION_RETRY_DELAY_MS = 1000;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private PermissionRequest pendingWebPermissionRequest = null;
    private ValueCallback<Uri[]> filePathCallback = null;
    private boolean startupPageLoaded = false;
    private boolean backendFailed = false;
    private int connectionAttempts = 0;
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
        loadingText = findViewById(R.id.loadingText);
        errorText = findViewById(R.id.errorText);
        showLoading("Starting MeshChatX backend...");

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        requestRuntimePermissionsIfNeeded();

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
                startupPageLoaded = true;
                mainHandler.removeCallbacksAndMessages(null);
                progressBar.setVisibility(android.view.View.GONE);
                loadingText.setVisibility(android.view.View.GONE);
                errorText.setVisibility(android.view.View.GONE);
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(android.view.View.VISIBLE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request != null && request.isForMainFrame() && isStartupRequest(request.getUrl().toString())) {
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
                    requestRuntimePermissionsIfNeeded();
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

    private void addIfMissing(List<String> missingPermissions, String permission) {
        if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
            missingPermissions.add(permission);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != RUNTIME_PERMISSIONS_REQUEST_CODE) {
            return;
        }
        for (int i = 0; i < permissions.length; i++) {
            if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                if (Manifest.permission.RECORD_AUDIO.equals(permissions[i]) && pendingWebPermissionRequest != null) {
                    pendingWebPermissionRequest.deny();
                    pendingWebPermissionRequest = null;
                }
                return;
            }
        }
        if (pendingWebPermissionRequest != null) {
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
        mainHandler.postDelayed(() -> {
            if (startupPageLoaded || backendFailed) {
                return;
            }
            connectionAttempts += 1;
            if (connectionAttempts > MAX_CONNECTION_ATTEMPTS) {
                showStartupError("Failed to connect to local MeshChatX server.");
                return;
            }
            webView.loadUrl(SERVER_URL);
            scheduleConnectionRetry("Retrying connection...");
        }, CONNECTION_RETRY_DELAY_MS);
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
            progressBar.setVisibility(android.view.View.VISIBLE);
            errorText.setVisibility(android.view.View.GONE);
            if (loadingText != null) {
                loadingText.setText(message);
                loadingText.setVisibility(android.view.View.VISIBLE);
            }
        });
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

