package com.meshchatx;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.hardware.usb.UsbManager;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.content.IntentFilter;
import android.provider.MediaStore;
import android.provider.Settings;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.JavascriptInterface;
import android.webkit.SslErrorHandler;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import androidx.core.view.WindowCompat;
import androidx.annotation.Nullable;
import androidx.annotation.RequiresApi;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import okhttp3.Request;
import okhttp3.Response;
import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {
    private static final String SHELL_PREFS = "meshchatx_shell";
    private static final String PREF_UI_THEME = "ui_theme";
    private static final String PREF_BLOCK_SCREENSHOTS = "block_screenshots";
    private static final String PREF_CLEAR_CLIPBOARD_ON_BACKGROUND = "clear_clipboard_on_background";
    private static final String PREF_REMOTE_BACKEND_URL = "remote_backend_url";
    private static final String THEME_DARK = "dark";
    private static final String THEME_LIGHT = "light";

    private WebView webView;
    private ProgressBar progressBar;
    private ImageView loadingLogo;
    private TextView loadingText;
    private TextView errorText;
    private static final int SERVER_PORT = 8000;
    private static final int RUNTIME_PERMISSIONS_REQUEST_CODE = 1001;
    private static final int WEB_MEDIA_PERMISSION_REQUEST_CODE = 1003;
    private static final int RNODE_BLUETOOTH_PERMISSION_REQUEST_CODE = 1004;
    private static final int WEBVIEW_GEOLOCATION_PERMISSION_REQUEST_CODE = 1006;
    private static final String PREFS_NAME = "meshchatx";
    private static final String PREF_BATTERY_OPT_REQUESTED = "battery_opt_requested";
    private static final int MAX_CONNECTION_ATTEMPTS = 120;
    private static final long CONNECTION_RETRY_INITIAL_DELAY_MS = 500;
    private static final long CONNECTION_RETRY_MAX_DELAY_MS = 5000;
    private static final int MESHCHAT_SERVER_START_MAX_ATTEMPTS = 4;
    private static final long MESHCHAT_SERVER_RETRY_DELAY_MS = 2000L;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private PermissionRequest pendingWebPermissionRequest = null;
    @Nullable
    private GeolocationPermissions.Callback pendingGeolocationPermissionCallback = null;
    @Nullable
    private String pendingGeolocationOrigin = null;
    private ValueCallback<Uri[]> filePathCallback = null;
    private boolean startupRequestHadLoadError = false;
    private boolean startupPageLoaded = false;
    private boolean backendFailed = false;
    private int meshchatServerStartAttempts = 0;
    private int connectionAttempts = 0;
    private String pendingIntentUri = null;
    @Nullable
    private String pendingCallNotificationAction;
    @Nullable
    TelephoneNativeAudioSession telephoneNativeSession;
    @Nullable
    WavPcmAttachmentRecorder attachmentPcmRecorder;
    private static final String[] STARTUP_PHASES = new String[] {
        "Starting MeshChatX…",
        "Getting the network ready…",
        "Almost there…",
        "Opening MeshChatX…",
        "Finishing up…"
    };
    private boolean isAllowedWebViewNavigationUri(Uri uri) {
        if (uri == null) {
            return false;
        }
        return RemoteBackendUrl.isAllowedShellNavigation(uri.toString(), resolveBackendUrl());
    }

    private void openExternalBrowserUri(Uri uri) {
        if (uri == null) {
            return;
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException ignored) {
            // no browser installed
        }
    }

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
        boolean darkShell = isDarkUiTheme(resolvePreferredUiTheme());
        getDelegate().setLocalNightMode(
            darkShell ? AppCompatDelegate.MODE_NIGHT_YES : AppCompatDelegate.MODE_NIGHT_NO
        );
        getTheme().applyStyle(R.style.OptOutEdgeToEdgeEnforcement, false);
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), true);
        setContentView(R.layout.activity_main);
        // Mitigate overlay tapjacking without changing user-visible behavior.
        getWindow().getDecorView().setFilterTouchesWhenObscured(true);
        applyBlockScreenshots(isBlockScreenshotsEnabled());

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        loadingLogo = findViewById(R.id.loadingLogo);
        loadingText = findViewById(R.id.loadingText);
        errorText = findViewById(R.id.errorText);
        // Match MeshChatX canvas so WebView never flashes default white during Chaquopy boot
        // or keyboard/resize gaps. Prefer last saved UI theme (default dark).
        applyShellCanvasTheme(resolvePreferredUiTheme());
        webView.setVisibility(android.view.View.INVISIBLE);
        final boolean remoteBackend = isRemoteBackendMode();
        showLoading(remoteBackend ? "Connecting to remote backend…" : "Starting MeshChatX…");

        if (!remoteBackend) {
            if (!Python.isStarted()) {
                try {
                    Python.start(new AndroidPlatform(this));
                } catch (Exception e) {
                    backendFailed = true;
                    showStartupError("MeshChatX Python runtime failed to start:", toStackTrace(e));
                    return;
                }
            }
            try {
                org.able.BLE.setAppContext(this);
            } catch (Exception ignored) {
                // BLE class may be unavailable in incomplete builds.
            }
        }
        requestRuntimePermissionsIfNeeded();

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        webSettings.setGeolocationEnabled(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            @RequiresApi(api = Build.VERSION_CODES.N)
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request != null ? request.getUrl() : null;
                if (isAllowedWebViewNavigationUri(uri)) {
                    return false;
                }
                openExternalBrowserUri(uri);
                return true;
            }

            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = url != null ? Uri.parse(url) : null;
                if (isAllowedWebViewNavigationUri(uri)) {
                    return false;
                }
                openExternalBrowserUri(uri);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (!startupPageLoaded) {
                    if (!isStartupRequest(url)) {
                        return;
                    }
                    if (startupRequestHadLoadError) {
                        return;
                    }
                    startupPageLoaded = true;
                    mainHandler.removeCallbacksAndMessages(null);
                    hideStartupLoadingOverlay();
                    dispatchPendingIntentUri();
                    dispatchCallNotificationAction();
                    return;
                }
                hideStartupLoadingOverlay();
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (!startupPageLoaded && isStartupRequest(url)) {
                    startupRequestHadLoadError = false;
                    webView.setVisibility(android.view.View.INVISIBLE);
                    progressBar.setVisibility(android.view.View.VISIBLE);
                    return;
                }
                if (!startupPageLoaded) {
                    progressBar.setVisibility(android.view.View.VISIBLE);
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request != null && request.isForMainFrame() && isStartupRequest(request.getUrl().toString())) {
                    startupRequestHadLoadError = true;
                    view.stopLoading();
                    view.loadUrl("about:blank");
                    if (backendFailed && !startupPageLoaded) {
                        String description = (error != null) ? error.getDescription().toString() : "Unknown error";
                        showStartupError("WebView failed to load MeshChatX:", description);
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
                        showStartupError("WebView failed to load MeshChatX:", description);
                    }
                }
            }

            @SuppressLint("WebViewClientOnReceivedSslError")
            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, android.net.http.SslError error) {
                if (handler == null) {
                    return;
                }
                String errorUrl = error != null ? error.getUrl() : null;
                Uri uri = errorUrl != null ? Uri.parse(errorUrl) : null;
                if (isAllowedWebViewNavigationUri(uri)) {
                    // Local and configured remote backends often use self-signed TLS.
                    handler.proceed();
                    return;
                }
                handler.cancel();
            }
        });
        webView.addJavascriptInterface(new MeshChatXAndroidBridge(this), "MeshChatXAndroid");
        webView.setDownloadListener(this::onWebViewDownloadStart);

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                runOnUiThread(() -> {
                    if (callback == null) {
                        return;
                    }
                    if (ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.ACCESS_FINE_LOCATION)
                            == PackageManager.PERMISSION_GRANTED
                        || ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.ACCESS_COARSE_LOCATION)
                            == PackageManager.PERMISSION_GRANTED) {
                        callback.invoke(origin, true, false);
                        return;
                    }
                    pendingGeolocationOrigin = origin;
                    pendingGeolocationPermissionCallback = callback;
                    ActivityCompat.requestPermissions(
                        MainActivity.this,
                        new String[] {
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION,
                        },
                        WEBVIEW_GEOLOCATION_PERMISSION_REQUEST_CODE
                    );
                });
            }

            @Override
            public void onGeolocationPermissionsHidePrompt() {
                runOnUiThread(() -> {
                    pendingGeolocationPermissionCallback = null;
                    pendingGeolocationOrigin = null;
                });
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    if (request == null) {
                        return;
                    }

                    boolean needsAudioCapture = false;
                    boolean needsVideoCapture = false;
                    for (String resource : request.getResources()) {
                        if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                            needsAudioCapture = true;
                        } else if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) {
                            needsVideoCapture = true;
                        }
                    }

                    if (!needsAudioCapture && !needsVideoCapture) {
                        request.grant(request.getResources());
                        return;
                    }

                    List<String> missingPermissions = new ArrayList<>();
                    if (
                        needsAudioCapture &&
                        ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.RECORD_AUDIO)
                            != PackageManager.PERMISSION_GRANTED
                    ) {
                        missingPermissions.add(Manifest.permission.RECORD_AUDIO);
                    }
                    if (
                        needsVideoCapture &&
                        ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.CAMERA)
                            != PackageManager.PERMISSION_GRANTED
                    ) {
                        missingPermissions.add(Manifest.permission.CAMERA);
                    }
                    if (missingPermissions.isEmpty()) {
                        String[] allowed = grantableWebPermissionResources(request);
                        if (allowed.length > 0) {
                            request.grant(allowed);
                        } else {
                            request.deny();
                        }
                        return;
                    }

                    pendingWebPermissionRequest = request;
                    ActivityCompat.requestPermissions(
                        MainActivity.this,
                        missingPermissions.toArray(new String[0]),
                        WEB_MEDIA_PERMISSION_REQUEST_CODE
                    );
                });
            }

            @Override
            public void onPermissionRequestCanceled(PermissionRequest request) {
                runOnUiThread(() -> {
                    if (pendingWebPermissionRequest == request) {
                        pendingWebPermissionRequest = null;
                    }
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
                    String[] acceptTypes = fileChooserParams.getAcceptTypes();
                    ArrayList<String> mimeTypes = new ArrayList<>();
                    for (String acceptType : acceptTypes) {
                        if (acceptType == null || acceptType.isEmpty()) {
                            continue;
                        }
                        String trimmed = acceptType.trim();
                        if (trimmed.startsWith(".")) {
                            // Extension filters are not valid MIME types for EXTRA_MIME_TYPES.
                            // Use octet-stream so identity backups without a MIME mapping remain selectable.
                            if (!mimeTypes.contains("application/octet-stream")) {
                                mimeTypes.add("application/octet-stream");
                            }
                            if (!mimeTypes.contains("*/*")) {
                                mimeTypes.add("*/*");
                            }
                        } else if (!mimeTypes.contains(trimmed)) {
                            mimeTypes.add(trimmed);
                        }
                    }
                    if (!mimeTypes.isEmpty()) {
                        chooserIntent.putExtra(
                            Intent.EXTRA_MIME_TYPES,
                            mimeTypes.toArray(new String[0])
                        );
                    } else {
                        chooserIntent.setType("*/*");
                    }
                }
                boolean allowMultiple = fileChooserParams != null && fileChooserParams.getMode()
                    == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE;
                chooserIntent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, allowMultiple);

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
        handleIncomingIntent(getIntent());
        consumeCallIntentForPending(getIntent());

        getOnBackPressedDispatcher().addCallback(
            this,
            new OnBackPressedCallback(true) {
                @Override
                public void handleOnBackPressed() {
                    if (webView != null && webView.canGoBack()) {
                        webView.goBack();
                    } else {
                        setEnabled(false);
                        MainActivity.this.getOnBackPressedDispatcher().onBackPressed();
                        setEnabled(true);
                    }
                }
            }
        );

        try {
            AndroidStorageManager.runPendingMigration(this);
        } catch (IOException migrationError) {
            showStartupError(
                "MeshChatX could not copy data to file-manager storage:",
                migrationError.getMessage()
            );
            return;
        }

        if (isRemoteBackendMode()) {
            webView.loadUrl(resolveBackendUrl());
            scheduleConnectionRetry("Connecting to remote backend…");
        } else {
            startMeshChatServer();
            scheduleConnectionRetry("Connecting to local server...");
        }
    }

    @Override
    protected void onStart() {
        super.onStart();
        stopService(new Intent(this, MeshChatForegroundService.class));
    }

    @Override
    protected void onStop() {
        if (isClearClipboardOnBackgroundEnabled()) {
            clearPrimaryClipboard();
        }
        if (!isFinishing() && !backendFailed) {
            ContextCompat.startForegroundService(this, new Intent(this, MeshChatForegroundService.class));
        }
        super.onStop();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncomingIntent(intent);
        consumeCallIntentForPending(intent);
        if (startupPageLoaded) {
            dispatchPendingIntentUri();
            dispatchCallNotificationAction();
        }
    }

    private void requestRuntimePermissionsIfNeeded() {
        List<String> missingPermissions = new ArrayList<>();
        addIfMissing(missingPermissions, Manifest.permission.RECORD_AUDIO);
        addIfMissing(missingPermissions, Manifest.permission.CAMERA);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            addIfMissing(missingPermissions, Manifest.permission.BLUETOOTH_CONNECT);
            addIfMissing(missingPermissions, Manifest.permission.BLUETOOTH_SCAN);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            addIfMissing(missingPermissions, Manifest.permission.POST_NOTIFICATIONS);
        }
        if (!missingPermissions.isEmpty()) {
            for (String permission : missingPermissions) {
                if (Manifest.permission.BLUETOOTH_CONNECT.equals(permission)
                    || Manifest.permission.BLUETOOTH_SCAN.equals(permission)) {
                    markBluetoothPermissionPrompted(permission);
                }
            }
            ActivityCompat.requestPermissions(
                this,
                missingPermissions.toArray(new String[0]),
                RUNTIME_PERMISSIONS_REQUEST_CODE
            );
        } else {
            requestBatteryOptimizationExemptionIfNeeded();
        }
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

    void addIfMissing(List<String> missingPermissions, String permission) {
        if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
            missingPermissions.add(permission);
        }
    }

    void openAppPermissionSettings() {
        AppSettingsLauncher.openAppDetails(this);
    }

    boolean openBluetoothPermissionSettings() {
        return AppSettingsLauncher.openBluetoothSettings(this);
    }

    private static final String PREF_BT_PERM_PROMPTED_PREFIX = "bt_perm_prompted_";

    boolean wasBluetoothPermissionDeniedPermanently(String permission) {
        if (ContextCompat.checkSelfPermission(this, permission)
            == PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        // No rationale means either never asked or permanently denied. Once we have
        // prompted (startup or explicit), treat no-rationale as permanent deny.
        boolean prompted =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .getBoolean(PREF_BT_PERM_PROMPTED_PREFIX + permission, false);
        if (!prompted) {
            return false;
        }
        return !ActivityCompat.shouldShowRequestPermissionRationale(this, permission);
    }

    boolean isBluetoothPermanentlyDenied() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            return false;
        }
        String[] needed = new String[] {
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
        };
        for (String permission : needed) {
            if (ContextCompat.checkSelfPermission(this, permission)
                == PackageManager.PERMISSION_GRANTED) {
                continue;
            }
            // After we have prompted once, denied + no rationale means permanent deny.
            // requestPermissions would show no dialog.
            if (wasBluetoothPermissionDeniedPermanently(permission)) {
                return true;
            }
        }
        return false;
    }

    void markBluetoothPermissionPrompted(String permission) {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit()
            .putBoolean(PREF_BT_PERM_PROMPTED_PREFIX + permission, true)
            .apply();
    }

    private String[] grantableWebPermissionResources(PermissionRequest request) {
        if (request == null) {
            return new String[0];
        }
        List<String> allowed = new ArrayList<>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED) {
                    allowed.add(resource);
                }
            } else if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                    == PackageManager.PERMISSION_GRANTED) {
                    allowed.add(resource);
                }
            } else {
                allowed.add(resource);
            }
        }
        return allowed.toArray(new String[0]);
    }

    private void completePendingWebPermissionRequestFromRuntimeState() {
        if (pendingWebPermissionRequest == null) {
            return;
        }
        String[] allowed = grantableWebPermissionResources(pendingWebPermissionRequest);
        if (allowed.length > 0) {
            pendingWebPermissionRequest.grant(allowed);
        } else {
            pendingWebPermissionRequest.deny();
        }
        pendingWebPermissionRequest = null;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == WEBVIEW_GEOLOCATION_PERMISSION_REQUEST_CODE) {
            boolean granted = false;
            if (permissions != null && grantResults != null) {
                for (int i = 0; i < permissions.length && i < grantResults.length; i++) {
                    if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                        continue;
                    }
                    if (Manifest.permission.ACCESS_FINE_LOCATION.equals(permissions[i])
                        || Manifest.permission.ACCESS_COARSE_LOCATION.equals(permissions[i])) {
                        granted = true;
                        break;
                    }
                }
            }
            if (pendingGeolocationPermissionCallback != null) {
                pendingGeolocationPermissionCallback.invoke(pendingGeolocationOrigin, granted, false);
                pendingGeolocationPermissionCallback = null;
                pendingGeolocationOrigin = null;
            }
            return;
        }
        if (requestCode == WEB_MEDIA_PERMISSION_REQUEST_CODE) {
            if (pendingWebPermissionRequest == null) {
                return;
            }
            boolean granted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    granted = false;
                    break;
                }
            }
            if (granted) {
                String[] allowed = grantableWebPermissionResources(pendingWebPermissionRequest);
                if (allowed.length > 0) {
                    pendingWebPermissionRequest.grant(allowed);
                } else {
                    pendingWebPermissionRequest.deny();
                }
            } else {
                pendingWebPermissionRequest.deny();
            }
            pendingWebPermissionRequest = null;
            return;
        }
        if (requestCode == RNODE_BLUETOOTH_PERMISSION_REQUEST_CODE) {
            boolean granted = true;
            if (grantResults == null || grantResults.length == 0) {
                granted = false;
            } else {
                for (int result : grantResults) {
                    if (result != PackageManager.PERMISSION_GRANTED) {
                        granted = false;
                        break;
                    }
                }
            }
            final boolean ok = granted;
            if (!ok && isBluetoothPermanentlyDenied()) {
                openBluetoothPermissionSettings();
                Toast.makeText(
                    this,
                    "Bluetooth blocked. Enable it in app settings.",
                    Toast.LENGTH_LONG
                ).show();
            }
            if (webView != null) {
                webView.evaluateJavascript(
                    "window.dispatchEvent(new CustomEvent('meshchatx-android-permission',"
                        + "{detail:{group:'bluetooth',granted:"
                        + ok
                        + "}}));",
                    null
                );
            }
            return;
        }
        if (requestCode != RUNTIME_PERMISSIONS_REQUEST_CODE) {
            return;
        }
        // Startup BT deny with no rationale: mark permanent path so later Allow
        // Bluetooth opens settings instead of a silent no-op request.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
            && permissions != null
            && grantResults != null) {
            for (int i = 0; i < permissions.length && i < grantResults.length; i++) {
                String permission = permissions[i];
                if (!Manifest.permission.BLUETOOTH_CONNECT.equals(permission)
                    && !Manifest.permission.BLUETOOTH_SCAN.equals(permission)) {
                    continue;
                }
                markBluetoothPermissionPrompted(permission);
            }
        }
        requestBatteryOptimizationExemptionIfNeeded();
        completePendingWebPermissionRequestFromRuntimeState();
    }

    private void startMeshChatServer() {
        new Thread(() -> {
            try {
                Python py = Python.getInstance();
                String appFilesDir = AndroidStorageManager.resolveActiveBaseDir(MainActivity.this).getAbsolutePath();
                // Pass Activity so usb4a / org.able.BLE can open RNode USB and BLE.
                py.getModule("meshchat_wrapper").callAttr(
                    "start_server", SERVER_PORT, appFilesDir, MainActivity.this);
            } catch (Exception e) {
                final String stack = toStackTrace(e);
                runOnUiThread(() -> {
                    if (startupPageLoaded) {
                        return;
                    }
                    meshchatServerStartAttempts += 1;
                    if (meshchatServerStartAttempts < MESHCHAT_SERVER_START_MAX_ATTEMPTS) {
                        backendFailed = false;
                        showLoading("Having trouble starting. Trying again…");
                        mainHandler.postDelayed(() -> startMeshChatServer(), MESHCHAT_SERVER_RETRY_DELAY_MS);
                    } else {
                        backendFailed = true;
                        showStartupError("MeshChatX backend failed:", stack);
                    }
                });
            }
        }).start();
    }

    private boolean isStartupRequest(String url) {
        return RemoteBackendUrl.matchesBackend(url, resolveBackendUrl());
    }

    @Nullable
    private String resolveStoredRemoteBackendUrl() {
        SharedPreferences prefs = getSharedPreferences(SHELL_PREFS, MODE_PRIVATE);
        return RemoteBackendUrl.normalize(prefs.getString(PREF_REMOTE_BACKEND_URL, null));
    }

    private String resolveBackendUrl() {
        return RemoteBackendUrl.resolveEffectiveUrl(resolveStoredRemoteBackendUrl());
    }

    private boolean isRemoteBackendMode() {
        return resolveStoredRemoteBackendUrl() != null;
    }

    private void persistRemoteBackendUrl(@Nullable String normalizedOrNull) {
        SharedPreferences.Editor editor = getSharedPreferences(SHELL_PREFS, MODE_PRIVATE).edit();
        if (normalizedOrNull == null || normalizedOrNull.isEmpty()) {
            editor.remove(PREF_REMOTE_BACKEND_URL);
        } else {
            editor.putString(PREF_REMOTE_BACKEND_URL, normalizedOrNull);
        }
        editor.apply();
    }

    private void restartAppForBackendChange() {
        Intent intent = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
        }
        finishAffinity();
        android.os.Process.killProcess(android.os.Process.myPid());
    }

    private void offerSwitchToLocalBackend(String title, @Nullable String detail) {
        final String message = StartupErrorReport.format(
            title,
            detail,
            StartupErrorReport.collect(this)
        );
        runOnUiThread(() -> {
            mainHandler.removeCallbacksAndMessages(null);
            if (webView != null) {
                webView.setVisibility(android.view.View.INVISIBLE);
            }
            if (loadingLogo != null) {
                loadingLogo.setVisibility(android.view.View.GONE);
            }
            if (progressBar != null) {
                progressBar.setVisibility(android.view.View.GONE);
            }
            if (loadingText != null) {
                loadingText.setVisibility(android.view.View.GONE);
            }
            if (errorText != null) {
                errorText.setText(message);
                errorText.setVisibility(android.view.View.VISIBLE);
            }
            if (isFinishing()) {
                return;
            }
            new AlertDialog.Builder(this)
                .setTitle(R.string.remote_backend_unreachable_title)
                .setMessage(R.string.remote_backend_unreachable_message)
                .setPositiveButton(R.string.remote_backend_use_local, (dialog, which) -> {
                    persistRemoteBackendUrl(null);
                    restartAppForBackendChange();
                })
                .setNegativeButton(R.string.remote_backend_keep_trying, (dialog, which) -> {
                    backendFailed = false;
                    startupPageLoaded = false;
                    startupRequestHadLoadError = false;
                    connectionAttempts = 0;
                    if (errorText != null) {
                        errorText.setVisibility(android.view.View.GONE);
                    }
                    webView.loadUrl(resolveBackendUrl());
                    scheduleConnectionRetry("Connecting to remote backend…");
                })
                .setCancelable(true)
                .show();
        });
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_VIEW.equals(intent.getAction())) {
            return;
        }
        Uri data = intent.getData();
        if (data == null || data.getScheme() == null) {
            return;
        }
        String scheme = data.getScheme().toLowerCase();
        if ("meshchatx".equals(scheme)) {
            if (data.getHost() == null) {
                return;
            }
            if (!"app".equalsIgnoreCase(data.getHost())) {
                return;
            }
            pendingIntentUri = data.toString();
            return;
        }
        if (!"lxma".equals(scheme) && !"lxmf".equals(scheme) && !"lxm".equals(scheme)) {
            return;
        }
        pendingIntentUri = data.toString();
    }

    private void consumeCallIntentForPending(Intent intent) {
        // Answer / decline / open are queued only by CallNotificationTrampolineActivity
        // (exported=false). Ignore CALL_ANSWER / CALL_DECLINE on this exported activity.
        String trusted = AndroidNotificationBridge.takeTrustedCallAction();
        if (trusted != null) {
            pendingCallNotificationAction = trusted;
        }
    }

    private void dispatchCallNotificationAction() {
        if (webView == null) {
            return;
        }
        if (pendingCallNotificationAction == null) {
            return;
        }
        String action = pendingCallNotificationAction;
        pendingCallNotificationAction = null;
        String js;
        if ("decline".equals(action)) {
            js =
                "(function(){" +
                "fetch('/api/v1/telephone/hangup', { credentials: 'include' }).catch(function(){});})();";
        } else if ("answer".equals(action)) {
            js =
                "(function(){" +
                "fetch('/api/v1/telephone/answer', { credentials: 'include' })" +
                ".then(function(){ try { window.location.hash = '#/call?tab=phone'; } catch (e) {}})" +
                ".catch(function(){});})();";
        } else if ("open".equals(action)) {
            js = "(function(){" + "try { window.location.hash = '#/call?tab=phone'; } catch (e) {}" + "})();";
        } else {
            return;
        }
        webView.evaluateJavascript(js, null);
    }

    private void dispatchPendingIntentUri() {
        if (webView == null || pendingIntentUri == null || pendingIntentUri.isEmpty()) {
            return;
        }
        String uri = pendingIntentUri;
        pendingIntentUri = null;
        String js =
            "window.dispatchEvent(new CustomEvent('meshchatx-intent-uri',{detail:" +
            JSONObject.quote(uri) +
            "}));";
        webView.evaluateJavascript(js, null);
    }

    private void scheduleConnectionRetry(String message) {
        if (startupPageLoaded || backendFailed) {
            return;
        }
        showLoading(message);
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
                if (isRemoteBackendMode()) {
                    backendFailed = true;
                    offerSwitchToLocalBackend(
                        "Failed to connect to remote MeshChatX backend after waiting for startup.",
                        resolveBackendUrl()
                    );
                } else {
                    showStartupError(
                        "Failed to connect to local MeshChatX server after waiting for startup.",
                        null
                    );
                }
                return;
            }
            webView.loadUrl(resolveBackendUrl());
            scheduleConnectionRetry(
                isRemoteBackendMode() ? "Still connecting to remote backend…" : "Still starting…"
            );
        }, retryDelayMs);
    }

    private String resolvePreferredUiTheme() {
        SharedPreferences prefs = getSharedPreferences(SHELL_PREFS, MODE_PRIVATE);
        String stored = prefs.getString(PREF_UI_THEME, null);
        if (THEME_LIGHT.equals(stored) || THEME_DARK.equals(stored)) {
            return stored;
        }
        return THEME_DARK;
    }

    private static boolean isDarkUiTheme(String theme) {
        return !THEME_LIGHT.equals(theme);
    }

    private void persistPreferredUiTheme(String theme) {
        String normalized = isDarkUiTheme(theme) ? THEME_DARK : THEME_LIGHT;
        getSharedPreferences(SHELL_PREFS, MODE_PRIVATE)
            .edit()
            .putString(PREF_UI_THEME, normalized)
            .apply();
    }

    private void applyShellCanvasTheme(String theme) {
        boolean dark = isDarkUiTheme(theme);
        int canvasColor = ContextCompat.getColor(
            this,
            dark ? R.color.meshchat_canvas_dark : R.color.meshchat_canvas_light
        );
        getWindow().getDecorView().setBackgroundColor(canvasColor);
        android.view.View content = findViewById(android.R.id.content);
        if (content != null) {
            content.setBackgroundColor(canvasColor);
        }
        if (webView != null) {
            webView.setBackgroundColor(canvasColor);
        }
        if (loadingText != null) {
            loadingText.setTextColor(
                ContextCompat.getColor(this, dark ? R.color.white : R.color.black)
            );
        }
    }

    private void setUiThemeFromBridge(String theme) {
        String normalized = isDarkUiTheme(theme) ? THEME_DARK : THEME_LIGHT;
        persistPreferredUiTheme(normalized);
        applyShellCanvasTheme(normalized);
        // Update night mode without forcing an immediate recreate mid-session.
        // Next cold start applies local night mode before setContentView.
        int desired =
            isDarkUiTheme(normalized)
                ? AppCompatDelegate.MODE_NIGHT_YES
                : AppCompatDelegate.MODE_NIGHT_NO;
        if (getDelegate().getLocalNightMode() != desired) {
            getDelegate().setLocalNightMode(desired);
        }
    }

    private boolean isBlockScreenshotsEnabled() {
        return getSharedPreferences(SHELL_PREFS, MODE_PRIVATE)
            .getBoolean(PREF_BLOCK_SCREENSHOTS, false);
    }

    private void setBlockScreenshotsEnabled(boolean enabled) {
        getSharedPreferences(SHELL_PREFS, MODE_PRIVATE)
            .edit()
            .putBoolean(PREF_BLOCK_SCREENSHOTS, enabled)
            .apply();
        applyBlockScreenshots(enabled);
    }

    private void applyBlockScreenshots(boolean enabled) {
        if (enabled) {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        } else {
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
        }
    }

    private boolean isClearClipboardOnBackgroundEnabled() {
        return getSharedPreferences(SHELL_PREFS, MODE_PRIVATE)
            .getBoolean(PREF_CLEAR_CLIPBOARD_ON_BACKGROUND, false);
    }

    private void setClearClipboardOnBackgroundEnabled(boolean enabled) {
        getSharedPreferences(SHELL_PREFS, MODE_PRIVATE)
            .edit()
            .putBoolean(PREF_CLEAR_CLIPBOARD_ON_BACKGROUND, enabled)
            .apply();
    }

    private void clearPrimaryClipboard() {
        try {
            ClipboardManager clipboard =
                (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard == null) {
                return;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                clipboard.clearPrimaryClip();
            } else {
                clipboard.setPrimaryClip(ClipData.newPlainText("", ""));
            }
        } catch (Exception ignored) {
            // Clipboard access can fail on locked devices or OEM builds.
        }
    }

    private String toStackTrace(Throwable error) {
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        error.printStackTrace(pw);
        pw.flush();
        return sw.toString();
    }

    private void hideStartupLoadingOverlay() {
        if (webView != null) {
            webView.setVisibility(android.view.View.VISIBLE);
        }
        if (loadingLogo != null) {
            loadingLogo.setVisibility(android.view.View.GONE);
        }
        if (progressBar != null) {
            progressBar.setVisibility(android.view.View.GONE);
        }
        if (loadingText != null) {
            loadingText.setVisibility(android.view.View.GONE);
        }
        if (errorText != null && !backendFailed) {
            errorText.setVisibility(android.view.View.GONE);
        }
    }

    private void showStartupError(String title, @Nullable String detail) {
        final String message = StartupErrorReport.format(
            title,
            detail,
            StartupErrorReport.collect(this)
        );
        runOnUiThread(() -> {
            mainHandler.removeCallbacksAndMessages(null);
            if (webView != null) {
                webView.setVisibility(android.view.View.INVISIBLE);
            }
            if (loadingLogo != null) {
                loadingLogo.setVisibility(android.view.View.GONE);
            }
            if (progressBar != null) {
                progressBar.setVisibility(android.view.View.GONE);
            }
            if (loadingText != null) {
                loadingText.setVisibility(android.view.View.GONE);
            }
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
        // Prefer friendly phase copy over technical/counter messages.
        if (fallbackMessage == null || fallbackMessage.isEmpty()) {
            return STARTUP_PHASES[phaseIndex];
        }
        String trimmed = fallbackMessage.trim();
        if (trimmed.startsWith("Starting MeshChatX")
            || trimmed.startsWith("Still starting")
            || trimmed.startsWith("Retrying")
            || trimmed.startsWith("Having trouble")) {
            return STARTUP_PHASES[phaseIndex];
        }
        return trimmed;
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (webView != null) {
            webView.post(() -> {
                if (webView != null) {
                    webView.requestLayout();
                }
            });
        }
    }

    @Override
    protected void onDestroy() {
        if (telephoneNativeSession != null) {
            telephoneNativeSession.onDestroy();
            telephoneNativeSession = null;
        }
        if (attachmentPcmRecorder != null) {
            attachmentPcmRecorder.cancel();
            attachmentPcmRecorder = null;
        }
        stopService(new Intent(this, MeshChatForegroundService.class));
        super.onDestroy();
        mainHandler.removeCallbacksAndMessages(null);
        if (pendingWebPermissionRequest != null) {
            pendingWebPermissionRequest.deny();
            pendingWebPermissionRequest = null;
        }
        if (pendingGeolocationPermissionCallback != null) {
            pendingGeolocationPermissionCallback.invoke(pendingGeolocationOrigin, false, false);
            pendingGeolocationPermissionCallback = null;
            pendingGeolocationOrigin = null;
        }
        if (filePathCallback != null) {
            filePathCallback.onReceiveValue(null);
            filePathCallback = null;
        }
        if (webView != null) {
            webView.destroy();
        }
    }

    WebView getWebViewForNativeBridge() {
        return webView;
    }

    private void onWebViewDownloadStart(
        String url,
        String userAgent,
        String contentDisposition,
        String mimeType,
        long contentLength
    ) {
        if (url == null || url.isEmpty()) {
            return;
        }
        Uri uri = Uri.parse(url);
        if (!isAllowedWebViewNavigationUri(uri)) {
            return;
        }
        String scheme = uri.getScheme();
        if (scheme == null) {
            return;
        }
        String s = scheme.toLowerCase(Locale.ROOT);
        if (!"http".equals(s) && !"https".equals(s)) {
            return;
        }
        String fileName = parseDownloadFileName(contentDisposition, uri);
        new Thread(() -> fetchAndPersistWebViewDownload(url, fileName), "meshchatx-webview-dl").start();
    }

    private static String parseDownloadFileName(String contentDisposition, Uri uri) {
        if (contentDisposition != null && !contentDisposition.isEmpty()) {
            Matcher star = Pattern.compile("filename\\*=UTF-8''([^;\\s]+)", Pattern.CASE_INSENSITIVE)
                .matcher(contentDisposition);
            if (star.find()) {
                try {
                    return java.net.URLDecoder.decode(star.group(1), "UTF-8");
                } catch (Exception ignored) {
                    // fall through
                }
            }
            Matcher plain = Pattern.compile("filename=\"?([^\";\\n]+)\"?", Pattern.CASE_INSENSITIVE)
                .matcher(contentDisposition);
            if (plain.find()) {
                return plain.group(1).trim();
            }
        }
        String segment = uri != null ? uri.getLastPathSegment() : null;
        if (segment != null && !segment.isEmpty()) {
            return segment;
        }
        return "download.bin";
    }

    private void fetchAndPersistWebViewDownload(String url, String fileName) {
        try {
            Request.Builder builder = new Request.Builder().url(url);
            String cookie = CookieManager.getInstance().getCookie(url);
            if (cookie != null && !cookie.isEmpty()) {
                builder.addHeader("Cookie", cookie);
            }
            try (Response response = LocalhostTrustOkHttpClient.get().newCall(builder.build()).execute()) {
                if (!response.isSuccessful() || response.body() == null) {
                    runOnUiThread(
                        () ->
                            Toast.makeText(
                                this,
                                "Download failed: HTTP " + response.code(),
                                Toast.LENGTH_LONG
                            ).show()
                    );
                    return;
                }
                byte[] data = response.body().bytes();
                runOnUiThread(
                    () -> {
                        try {
                            persistMeshchatDownload(fileName, data);
                        } catch (IOException e) {
                            Toast.makeText(
                                this,
                                "Save failed: " + e.getMessage(),
                                Toast.LENGTH_LONG
                            ).show();
                        }
                    }
                );
            }
        } catch (Exception e) {
            runOnUiThread(
                () -> Toast.makeText(this, "Download failed: " + e.getMessage(), Toast.LENGTH_LONG).show()
            );
        }
    }

    void persistMeshchatDownload(String fileName, byte[] data) throws IOException {
        String safe = MeshchatDownloadUtils.sanitizeFileName(fileName);
        ContentResolver resolver = getContentResolver();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContentValues values = new ContentValues();
            values.put(MediaStore.MediaColumns.DISPLAY_NAME, safe);
            String mime = URLConnection.guessContentTypeFromName(safe);
            if (mime == null) {
                mime = "application/octet-stream";
            }
            values.put(MediaStore.MediaColumns.MIME_TYPE, mime);
            values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
            values.put(MediaStore.MediaColumns.IS_PENDING, 1);
            Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) {
                throw new IOException("MediaStore insert failed");
            }
            try (OutputStream out = resolver.openOutputStream(uri)) {
                if (out == null) {
                    throw new IOException("openOutputStream failed");
                }
                out.write(data);
            }
            values.clear();
            values.put(MediaStore.MediaColumns.IS_PENDING, 0);
            resolver.update(uri, values, null, null);
            Toast.makeText(this, getString(R.string.download_saved_meshchatx, safe), Toast.LENGTH_LONG).show();
        } else {
            File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (dir == null) {
                throw new IOException("no download directory");
            }
            if (!dir.exists() && !dir.mkdirs()) {
                throw new IOException("mkdirs failed");
            }
            File target = new File(dir, safe);
            try (FileOutputStream fos = new FileOutputStream(target)) {
                fos.write(data);
            }
            Toast.makeText(this, getString(R.string.download_saved_app_files, target.getAbsolutePath()), Toast.LENGTH_LONG)
                .show();
        }
    }

    private static class MeshChatXAndroidBridge {
        private final MainActivity activity;

        MeshChatXAndroidBridge(MainActivity activity) {
            this.activity = activity;
        }

        @JavascriptInterface
        public void saveDownload(String fileName, String base64Data) {
            if (base64Data == null) {
                return;
            }
            activity.runOnUiThread(() -> {
                try {
                    byte[] raw = android.util.Base64.decode(base64Data, android.util.Base64.DEFAULT);
                    if (raw.length == 0) {
                        Toast.makeText(activity, "Empty file", Toast.LENGTH_SHORT).show();
                        return;
                    }
                    activity.persistMeshchatDownload(fileName, raw);
                } catch (IllegalArgumentException e) {
                    Toast.makeText(activity, "Invalid download data", Toast.LENGTH_LONG).show();
                } catch (IOException e) {
                    Toast.makeText(activity, "Save failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
        }

        @JavascriptInterface
        public void exitApp() {
            activity.runOnUiThread(() -> {
                activity.finishAffinity();
                android.os.Process.killProcess(android.os.Process.myPid());
            });
        }

        @JavascriptInterface
        public String getPlatform() {
            return "android";
        }

        @JavascriptInterface
        public String getBatteryStatus() {
            try {
                int level = -1;
                boolean charging = false;
                BatteryManager batteryManager =
                    (BatteryManager) activity.getSystemService(Context.BATTERY_SERVICE);
                if (batteryManager != null) {
                    level = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                    // BatteryManager may return Integer.MIN_VALUE when unsupported.
                    if (level < 0 || level > 100) {
                        level = -1;
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        charging = batteryManager.isCharging();
                    }
                }
                IntentFilter filter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
                Intent batteryStatus = activity.registerReceiver(null, filter);
                if (batteryStatus != null) {
                    if (level < 0) {
                        int rawLevel = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                        int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
                        if (rawLevel >= 0 && scale > 0) {
                            level = Math.round((rawLevel * 100f) / scale);
                        }
                    }
                    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
                        int status =
                            batteryStatus.getIntExtra(
                                BatteryManager.EXTRA_STATUS,
                                BatteryManager.BATTERY_STATUS_UNKNOWN);
                        charging =
                            status == BatteryManager.BATTERY_STATUS_CHARGING
                                || status == BatteryManager.BATTERY_STATUS_FULL;
                    }
                }
                if (level < 0) {
                    return "";
                }
                if (level > 100) {
                    level = 100;
                }
                return "{\"level\":"
                    + level
                    + ",\"charging\":"
                    + (charging ? "true" : "false")
                    + ",\"source\":\"android\"}";
            } catch (Exception e) {
                return "";
            }
        }

        @JavascriptInterface
        public String getPreferredUiTheme() {
            return activity.resolvePreferredUiTheme();
        }

        @JavascriptInterface
        public void setUiTheme(String theme) {
            activity.runOnUiThread(() -> activity.setUiThemeFromBridge(theme));
        }

        @JavascriptInterface
        public boolean getBlockScreenshots() {
            return activity.isBlockScreenshotsEnabled();
        }

        @JavascriptInterface
        public void setBlockScreenshots(boolean enabled) {
            activity.runOnUiThread(() -> activity.setBlockScreenshotsEnabled(enabled));
        }

        @JavascriptInterface
        public boolean getClearClipboardOnBackground() {
            return activity.isClearClipboardOnBackgroundEnabled();
        }

        @JavascriptInterface
        public void setClearClipboardOnBackground(boolean enabled) {
            activity.runOnUiThread(() -> activity.setClearClipboardOnBackgroundEnabled(enabled));
        }

        @JavascriptInterface
        public String getRemoteBackendUrl() {
            String stored = activity.resolveStoredRemoteBackendUrl();
            return stored != null ? stored : "";
        }

        @JavascriptInterface
        public String getEffectiveBackendUrl() {
            return activity.resolveBackendUrl();
        }

        @JavascriptInterface
        public boolean isRemoteBackend() {
            return activity.isRemoteBackendMode();
        }

        /**
         * Persist a remote backend URL and restart the app.
         * Pass empty string to clear and use the on-device local backend.
         * Returns ok, invalid, or unsupported.
         */
        @JavascriptInterface
        public String setRemoteBackendUrlAndRestart(String url) {
            final String normalized = RemoteBackendUrl.normalize(url);
            if (url != null && !url.trim().isEmpty() && normalized == null) {
                return "invalid";
            }
            String current = activity.resolveStoredRemoteBackendUrl();
            boolean same =
                (normalized == null && current == null)
                    || (normalized != null && normalized.equals(current));
            if (same) {
                return "unchanged";
            }
            activity.runOnUiThread(() -> {
                activity.persistRemoteBackendUrl(normalized);
                Toast.makeText(
                        activity,
                        normalized == null
                            ? R.string.remote_backend_switching_local
                            : R.string.remote_backend_switching_remote,
                        Toast.LENGTH_SHORT)
                    .show();
                activity.restartAppForBackendChange();
            });
            return "ok";
        }

        @JavascriptInterface
        public String getSidebandPluginsDefaultPath() {
            try {
                File dir = new File(activity.getFilesDir(), "meshchatx/sideband-plugins");
                if (!dir.isDirectory() && !dir.mkdirs()) {
                    return activity.getFilesDir().getAbsolutePath();
                }
                return dir.getAbsolutePath();
            } catch (Exception e) {
                return "";
            }
        }

        @JavascriptInterface
        public void shareApk() {
            activity.runOnUiThread(() -> {
                try {
                    String srcPath = activity.getApplicationInfo().sourceDir;
                    File src = new File(srcPath);
                    if (!src.isFile()) {
                        Toast.makeText(activity, R.string.share_apk_unavailable, Toast.LENGTH_LONG).show();
                        return;
                    }
                    File cacheDir = new File(activity.getCacheDir(), "apk_share");
                    if (!cacheDir.isDirectory() && !cacheDir.mkdirs()) {
                        Toast.makeText(activity, R.string.share_apk_failed, Toast.LENGTH_LONG).show();
                        return;
                    }
                    String ver = "unknown";
                    try {
                        android.content.pm.PackageInfo pi =
                            activity
                                .getPackageManager()
                                .getPackageInfo(activity.getPackageName(), 0);
                        if (pi.versionName != null && !pi.versionName.isEmpty()) {
                            ver = pi.versionName.replaceAll("[^A-Za-z0-9._-]+", "_");
                        }
                    } catch (PackageManager.NameNotFoundException ignored) {
                    }
                    File dest = new File(cacheDir, "meshchatx-" + ver + ".apk");
                    try (FileInputStream in = new FileInputStream(src);
                        FileOutputStream out = new FileOutputStream(dest, false)) {
                        byte[] buf = new byte[8192];
                        int n;
                        while ((n = in.read(buf)) != -1) {
                            out.write(buf, 0, n);
                        }
                        out.flush();
                    }
                    Uri uri =
                        FileProvider.getUriForFile(
                            activity, activity.getPackageName() + ".fileprovider", dest);
                    Intent share = new Intent(Intent.ACTION_SEND);
                    share.setType("application/vnd.android.package-archive");
                    share.putExtra(Intent.EXTRA_STREAM, uri);
                    share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    share.setClipData(
                        ClipData.newUri(
                            activity.getContentResolver(),
                            activity.getString(R.string.share_apk_chooser_title),
                            uri));
                    activity.startActivity(
                        Intent.createChooser(
                            share, activity.getString(R.string.share_apk_chooser_title)));
                } catch (Exception e) {
                    String msg = activity.getString(R.string.share_apk_failed);
                    if (e.getMessage() != null && !e.getMessage().isEmpty()) {
                        msg = msg + ": " + e.getMessage();
                    }
                    Toast.makeText(activity, msg, Toast.LENGTH_LONG).show();
                }
            });
        }

        @JavascriptInterface
        public boolean hasBluetoothPermissions() {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
                return true;
            }
            return ContextCompat.checkSelfPermission(activity, Manifest.permission.BLUETOOTH_CONNECT)
                    == PackageManager.PERMISSION_GRANTED
                && ContextCompat.checkSelfPermission(activity, Manifest.permission.BLUETOOTH_SCAN)
                    == PackageManager.PERMISSION_GRANTED;
        }

        @JavascriptInterface
        public String requestBluetoothPermissions() {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
                return "granted";
            }
            if (hasBluetoothPermissions()) {
                return "granted";
            }
            if (activity.isBluetoothPermanentlyDenied()) {
                activity.runOnUiThread(() -> {
                    activity.openBluetoothPermissionSettings();
                    Toast.makeText(
                        activity,
                        "Bluetooth blocked. Enable it in app settings.",
                        Toast.LENGTH_LONG
                    ).show();
                });
                return "settings";
            }
            activity.runOnUiThread(() -> {
                List<String> missing = new ArrayList<>();
                activity.addIfMissing(missing, Manifest.permission.BLUETOOTH_CONNECT);
                activity.addIfMissing(missing, Manifest.permission.BLUETOOTH_SCAN);
                if (missing.isEmpty()) {
                    return;
                }
                for (String permission : missing) {
                    activity.markBluetoothPermissionPrompted(permission);
                }
                ActivityCompat.requestPermissions(
                    activity,
                    missing.toArray(new String[0]),
                    RNODE_BLUETOOTH_PERMISSION_REQUEST_CODE
                );
            });
            return "requested";
        }

        @JavascriptInterface
        public boolean hasUsbPermissions() {
            UsbManager manager = (UsbManager) activity.getSystemService(Context.USB_SERVICE);
            if (manager == null) {
                return false;
            }
            java.util.HashMap<String, android.hardware.usb.UsbDevice> devices =
                manager.getDeviceList();
            if (devices == null || devices.isEmpty()) {
                return true;
            }
            for (android.hardware.usb.UsbDevice device : devices.values()) {
                if (!manager.hasPermission(device)) {
                    return false;
                }
            }
            return true;
        }

        @JavascriptInterface
        public String requestUsbPermissions() {
            return openRNodeFlasher();
        }

        @JavascriptInterface
        public boolean hasNativeRNodeFlasher() {
            return true;
        }

        @JavascriptInterface
        public String openRNodeFlasher() {
            try {
                final java.util.concurrent.CountDownLatch latch =
                    new java.util.concurrent.CountDownLatch(1);
                final String[] result = new String[] {"error:unknown"};
                activity.runOnUiThread(() -> {
                    try {
                        Intent intent =
                            new Intent(activity, com.meshchatx.rnode.RNodeFlasherActivity.class);
                        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        activity.startActivity(intent);
                        result[0] = "ok";
                    } catch (Exception e) {
                        String msg =
                            e.getMessage() != null && !e.getMessage().isEmpty()
                                ? e.getMessage()
                                : "Could not open native RNode flasher";
                        result[0] = "error:" + msg;
                        Toast.makeText(activity, msg, Toast.LENGTH_LONG).show();
                    } finally {
                        latch.countDown();
                    }
                });
                if (!latch.await(3, java.util.concurrent.TimeUnit.SECONDS)) {
                    return "timeout";
                }
                return result[0];
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return "interrupted";
            }
        }

        @JavascriptInterface
        public String openBluetoothSettings() {
            try {
                final java.util.concurrent.CountDownLatch latch =
                    new java.util.concurrent.CountDownLatch(1);
                final boolean[] launched = new boolean[] {false};
                activity.runOnUiThread(() -> {
                    try {
                        launched[0] = activity.openBluetoothPermissionSettings();
                    } finally {
                        latch.countDown();
                    }
                });
                if (!latch.await(2, java.util.concurrent.TimeUnit.SECONDS)) {
                    return "timeout";
                }
                return launched[0] ? "ok" : "unavailable";
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return "interrupted";
            }
        }

        @JavascriptInterface
        public String openUsbSettings() {
            try {
                final java.util.concurrent.CountDownLatch latch =
                    new java.util.concurrent.CountDownLatch(1);
                final boolean[] launched = new boolean[] {false};
                activity.runOnUiThread(() -> {
                    try {
                        launched[0] = AppSettingsLauncher.openAppDetails(activity);
                    } finally {
                        latch.countDown();
                    }
                });
                if (!latch.await(2, java.util.concurrent.TimeUnit.SECONDS)) {
                    return "timeout";
                }
                return launched[0] ? "ok" : "unavailable";
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return "interrupted";
            }
        }

        @JavascriptInterface
        public boolean isNativePcmAudioAvailable() {
            return TelephoneNativeAudioSession.canRun(activity)
                && WavPcmAttachmentRecorder.canStart(activity);
        }

        /**
         * Voice-note attachment capture (PCM WAV) only checks the attachment recorder,
         * independent of telephone native audio, so the WebView can always prefer
         * native 48 kHz mono PCM for LXST Opus encoding on the server.
         */
        @JavascriptInterface
        public boolean isNativeWavAttachmentAvailable() {
            return WavPcmAttachmentRecorder.canStart(activity);
        }

        @JavascriptInterface
        public boolean isTelephoneNativeAudioAvailable() {
            return TelephoneNativeAudioSession.canRun(activity);
        }

        @JavascriptInterface
        public String startTelephoneNativeAudio() {
            try {
                if (activity.telephoneNativeSession == null) {
                    activity.telephoneNativeSession = new TelephoneNativeAudioSession(activity);
                }
                activity.telephoneNativeSession.start();
                return "ok";
            } catch (Exception e) {
                return e.getMessage() != null ? e.getMessage() : "err";
            }
        }

        @JavascriptInterface
        public void stopTelephoneNativeAudio() {
            try {
                if (activity.telephoneNativeSession != null) {
                    activity.telephoneNativeSession.stop();
                }
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public boolean isTelephoneNativeAudioActive() {
            return activity.telephoneNativeSession != null && activity.telephoneNativeSession.isActive();
        }

        @JavascriptInterface
        public String startNativeWavAttachment() {
            try {
                if (activity.attachmentPcmRecorder == null) {
                    activity.attachmentPcmRecorder = new WavPcmAttachmentRecorder(activity);
                }
                return activity.attachmentPcmRecorder.start();
            } catch (Exception e) {
                return e.getMessage() != null ? e.getMessage() : "err";
            }
        }

        @JavascriptInterface
        public void stopNativeWavAttachment() {
            if (activity.attachmentPcmRecorder == null) {
                return;
            }
            final WavPcmAttachmentRecorder r = activity.attachmentPcmRecorder;
            new Thread(
                () -> {
                    String b64 = r.stopBase64Wav();
                    activity.runOnUiThread(
                        () -> {
                            try {
                                if (activity.webView == null) {
                                    return;
                                }
                                org.json.JSONObject o = new org.json.JSONObject();
                                if (b64 == null) {
                                    o.put("ok", false);
                                    o.put("error", "out_of_memory");
                                } else if (b64.isEmpty()) {
                                    o.put("ok", false);
                                    o.put("error", "empty");
                                } else {
                                    o.put("ok", true);
                                    o.put("data", b64);
                                }
                                String p = o.toString();
                                activity.webView.evaluateJavascript(
                                    "try{if(window.__meshchatXNative&&typeof window.__meshchatXNative.onWav==='function'){"
                                        + "var p=" + p
                                        + "; window.__meshchatXNative.onWav(p);}}catch(e){}",
                                    null
                                );
                            } catch (Exception ignored) {
                            } finally {
                                activity.attachmentPcmRecorder = null;
                            }
                        }
                    );
                },
                "meshchatx-attach-stop"
            ).start();
        }

        @JavascriptInterface
        public void cancelNativeWavAttachment() {
            if (activity.attachmentPcmRecorder != null) {
                activity.attachmentPcmRecorder.cancel();
                activity.attachmentPcmRecorder = null;
            }
        }

        @JavascriptInterface
        public void showNotification(String title, String body) {
            AndroidNotificationBridge.showInboundMessage(title, body, null, null);
        }

        @JavascriptInterface
        public void showMessageNotification(String title, String body, String destinationHash) {
            AndroidNotificationBridge.showInboundMessage(title, body, null, destinationHash);
        }

        @JavascriptInterface
        public void cancelMessageNotifications(String destinationHash) {
            AndroidNotificationBridge.cancelMessageNotifications(destinationHash);
        }

        @JavascriptInterface
        public void cancelAllMessageNotifications() {
            AndroidNotificationBridge.cancelAllMessageNotifications();
        }

        @JavascriptInterface
        public void setOpenConversationHashes(String csv) {
            AndroidNotificationBridge.setOpenConversationHashes(csv);
        }

        @JavascriptInterface
        public void setDoNotDisturbEnabled(boolean enabled) {
            AndroidNotificationBridge.setDoNotDisturbEnabled(enabled);
        }

        @JavascriptInterface
        public void showIncomingCallNotification(String callerName) {
            AndroidNotificationBridge.showIncomingCall(callerName, null);
        }

        @JavascriptInterface
        public void showMissedCallNotification(String title, String body) {
            AndroidNotificationBridge.showMissedCall(title, body, null);
        }

        @JavascriptInterface
        public void cancelIncomingCallNotification() {
            AndroidNotificationBridge.cancelIncomingCallNotification();
        }

        @JavascriptInterface
        public String getAndroidStorageStatus() {
            try {
                int versionCode = activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0).versionCode;
                return AndroidStorageManager.statusJson(activity, versionCode);
            } catch (PackageManager.NameNotFoundException e) {
                return "{}";
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void setAndroidStorageMode(String mode) {
            AndroidStorageManager.setConfiguredMode(activity, mode);
        }

        @JavascriptInterface
        public void markAndroidStorageSetupCompleted() {
            AndroidStorageManager.markSetupCompleted(activity);
        }

        @JavascriptInterface
        public void scheduleCopyToExternalAndRestart() {
            AndroidStorageManager.scheduleCopyToExternal(activity);
        }

        @JavascriptInterface
        public void keepInternalStorageAndDismiss() {
            try {
                int versionCode =
                    activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0).versionCode;
                AndroidStorageManager.keepInternalAndDismissUpgrade(activity, versionCode);
            } catch (PackageManager.NameNotFoundException ignored) {
                AndroidStorageManager.setConfiguredMode(activity, AndroidStorageManager.MODE_INTERNAL);
                AndroidStorageManager.markSetupCompleted(activity);
            }
        }

        @JavascriptInterface
        public void restartApp() {
            activity.runOnUiThread(() -> {
                activity.finishAffinity();
                android.os.Process.killProcess(android.os.Process.myPid());
            });
        }
    }
}

