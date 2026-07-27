package com.meshchatx.rnode;

import android.Manifest;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.webkit.CookieManager;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.meshchatx.AppSettingsLauncher;
import com.meshchatx.LocalhostTrustOkHttpClient;
import com.meshchatx.R;
import com.meshchatx.RemoteBackendUrl;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Fully native RNode flasher (USB serial + ESP32 ROM protocol).
 * Launched from the WebView Tools page via MeshChatXAndroid.openRNodeFlasher().
 */
public final class RNodeFlasherActivity extends AppCompatActivity implements UsbSerialHub.Listener {
    private static final int REQ_BT = 4401;
    private static final String PREFS = "rnode_flasher";
    private static final String PREF_BT_PROMPTED = "bt_perm_prompted";
    private static final String SHELL_PREFS = "meshchatx_shell";
    private static final String PREF_REMOTE_BACKEND_URL = "remote_backend_url";

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private UsbSerialHub usbHub;
    private ProductCatalog catalog;
    @Nullable
    private byte[] firmwareBytes;
    @Nullable
    private String firmwareName;

    private Spinner usbSpinner;
    private Spinner productSpinner;
    private Spinner modelSpinner;
    private ProgressBar progressBar;
    private TextView statusView;
    private TextView logView;
    private Button flashButton;
    private Button downloadButton;

    private final List<UsbSerialHub.PortInfo> ports = new ArrayList<>();
    private ArrayAdapter<UsbSerialHub.PortInfo> usbAdapter;
    private ArrayAdapter<ProductCatalog.Product> productAdapter;
    private ArrayAdapter<ProductCatalog.Model> modelAdapter;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            setContentView(R.layout.activity_rnode_flasher);
            if (getSupportActionBar() != null) {
                getSupportActionBar().setTitle(R.string.rnode_flasher_title);
                getSupportActionBar().setDisplayHomeAsUpEnabled(true);
            }

            usbSpinner = findViewById(R.id.rnodeUsbSpinner);
            productSpinner = findViewById(R.id.rnodeProductSpinner);
            modelSpinner = findViewById(R.id.rnodeModelSpinner);
            progressBar = findViewById(R.id.rnodeProgress);
            statusView = findViewById(R.id.rnodeStatus);
            logView = findViewById(R.id.rnodeLog);
            flashButton = findViewById(R.id.rnodeFlash);
            downloadButton = findViewById(R.id.rnodeDownloadFirmware);

            usbAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, ports);
            usbSpinner.setAdapter(usbAdapter);

            try {
                catalog = ProductCatalog.load(this);
            } catch (Exception e) {
                appendLog("Failed to load product catalog: " + e.getMessage());
                catalog = ProductCatalog.empty();
            }
            productAdapter =
                new ArrayAdapter<>(
                    this, android.R.layout.simple_spinner_dropdown_item, catalog.products());
            productSpinner.setAdapter(productAdapter);
            modelAdapter =
                new ArrayAdapter<>(
                    this, android.R.layout.simple_spinner_dropdown_item, new ArrayList<>());
            modelSpinner.setAdapter(modelAdapter);

            productSpinner.setOnItemSelectedListener(
                new AdapterView.OnItemSelectedListener() {
                    @Override
                    public void onItemSelected(
                        AdapterView<?> parent, View view, int position, long id) {
                        refreshModels();
                    }

                    @Override
                    public void onNothingSelected(AdapterView<?> parent) {
                    }
                }
            );

            findViewById(R.id.rnodeRefreshUsb).setOnClickListener(v -> refreshPorts());
            findViewById(R.id.rnodeRequestUsb).setOnClickListener(v -> requestUsbPermission());
            findViewById(R.id.rnodeRequestBluetooth).setOnClickListener(v -> requestBluetooth());
            findViewById(R.id.rnodeOpenAppSettings).setOnClickListener(v -> openAppSettings());
            downloadButton.setOnClickListener(v -> downloadFirmware());
            flashButton.setOnClickListener(v -> flashSelected());

            usbHub = new UsbSerialHub(this);
            usbHub.addListener(this);
            usbHub.start();
            refreshPorts();
            refreshModels();
            appendLog("Native RNode flasher ready.");
        } catch (Exception e) {
            String msg =
                e.getMessage() != null && !e.getMessage().isEmpty()
                    ? e.getMessage()
                    : "Native RNode flasher failed to start";
            Toast.makeText(this, msg, Toast.LENGTH_LONG).show();
            finish();
        }
    }

    @Override
    public boolean onSupportNavigateUp() {
        finish();
        return true;
    }

    @Override
    protected void onDestroy() {
        if (usbHub != null) {
            usbHub.stop();
            usbHub = null;
        }
        io.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onUsbPermissionResult(String deviceId, boolean granted) {
        appendLog("USB permission " + (granted ? "granted" : "denied") + " for " + deviceId);
        refreshPorts();
    }

    @Override
    public void onPortsChanged() {
        refreshPorts();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_BT) {
            return;
        }
        boolean ok = true;
        if (grantResults == null || grantResults.length == 0) {
            ok = false;
        } else {
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    ok = false;
                    break;
                }
            }
        }
        appendLog(ok ? "Bluetooth permission granted." : "Bluetooth permission denied.");
        if (ok) {
            Toast.makeText(this, "Bluetooth allowed", Toast.LENGTH_SHORT).show();
            return;
        }
        if (isBluetoothPermanentlyDenied()) {
            appendLog("Bluetooth permanently denied. Opening app settings.");
            Toast.makeText(
                this,
                "Bluetooth blocked. Enable it in app settings.",
                Toast.LENGTH_LONG
            ).show();
            openBluetoothSettings();
            return;
        }
        Toast.makeText(this, "Bluetooth denied", Toast.LENGTH_SHORT).show();
    }

    private boolean isBluetoothPermanentlyDenied() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            return false;
        }
        String[] needed = new String[] {
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
        };
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        boolean prompted = prefs.getBoolean(PREF_BT_PROMPTED, false);
        for (String permission : needed) {
            if (ContextCompat.checkSelfPermission(this, permission)
                == PackageManager.PERMISSION_GRANTED) {
                continue;
            }
            if (prompted && !ActivityCompat.shouldShowRequestPermissionRationale(this, permission)) {
                return true;
            }
        }
        return false;
    }

    private void requestBluetooth() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            appendLog("Bluetooth runtime permission not required on this Android version.");
            Toast.makeText(this, "Bluetooth already allowed on this Android version", Toast.LENGTH_SHORT)
                .show();
            return;
        }
        List<String> missing = new ArrayList<>();
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
            != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.BLUETOOTH_CONNECT);
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
            != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.BLUETOOTH_SCAN);
        }
        if (missing.isEmpty()) {
            appendLog("Bluetooth permission already granted.");
            Toast.makeText(this, "Bluetooth already allowed", Toast.LENGTH_SHORT).show();
            return;
        }
        if (isBluetoothPermanentlyDenied()) {
            appendLog("Bluetooth permanently denied. Opening app settings.");
            Toast.makeText(
                this,
                "Bluetooth blocked. Enable it in app settings.",
                Toast.LENGTH_LONG
            ).show();
            openBluetoothSettings();
            return;
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(PREF_BT_PROMPTED, true).apply();
        ActivityCompat.requestPermissions(this, missing.toArray(new String[0]), REQ_BT);
        appendLog("Requesting Bluetooth permissions…");
    }

    private void openAppSettings() {
        AppSettingsLauncher.openAppDetails(this);
    }

    private void openBluetoothSettings() {
        AppSettingsLauncher.openBluetoothSettings(this);
    }

    private void refreshPorts() {
        ports.clear();
        if (usbHub != null) {
            ports.addAll(usbHub.listPorts());
        }
        usbAdapter.notifyDataSetChanged();
        if (ports.isEmpty()) {
            setStatus(getString(R.string.rnode_flasher_no_usb));
        } else {
            setStatus(ports.size() + " USB serial device(s)");
        }
    }

    private void refreshModels() {
        modelAdapter.clear();
        ProductCatalog.Product product = selectedProduct();
        if (product != null) {
            modelAdapter.addAll(product.models);
        }
        modelAdapter.notifyDataSetChanged();
    }

    private void requestUsbPermission() {
        UsbSerialHub.PortInfo port = selectedPort();
        if (port == null) {
            boolean any = usbHub != null && usbHub.requestPermissionsForAll();
            appendLog(any ? "Requested USB permissions." : "No USB devices need permission.");
            return;
        }
        if (port.hasPermission) {
            appendLog("USB already allowed for " + port);
            return;
        }
        if (usbHub != null) {
            usbHub.requestPermission(port.deviceId);
            appendLog("Requested USB permission for " + port);
        }
    }

    private void downloadFirmware() {
        ProductCatalog.Product product = selectedProduct();
        ProductCatalog.Model model = selectedModel();
        if (product == null) {
            Toast.makeText(this, "Select a product", Toast.LENGTH_SHORT).show();
            return;
        }
        String filename = product.resolveFirmwareFilename(model);
        if (filename == null || filename.isEmpty()) {
            Toast.makeText(this, "No firmware filename for product", Toast.LENGTH_SHORT).show();
            return;
        }
        setBusy(true);
        setStatus("Downloading " + filename + "…");
        appendLog("Downloading " + filename);
        io.execute(() -> {
            try {
                byte[] bytes = fetchFirmwareZip(filename);
                File cache = new File(getCacheDir(), filename);
                try (FileOutputStream fos = new FileOutputStream(cache)) {
                    fos.write(bytes);
                }
                firmwareBytes = bytes;
                firmwareName = filename;
                mainHandler.post(() -> {
                    setBusy(false);
                    setStatus("Downloaded " + filename + " (" + bytes.length + " bytes)");
                    appendLog("Firmware ready: " + cache.getAbsolutePath());
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    setBusy(false);
                    setStatus("Download failed");
                    appendLog("Download error: " + e.getMessage());
                    Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        });
    }

    private void flashSelected() {
        UsbSerialHub.PortInfo port = selectedPort();
        ProductCatalog.Product product = selectedProduct();
        ProductCatalog.Model model = selectedModel();
        if (port == null) {
            Toast.makeText(this, getString(R.string.rnode_flasher_no_usb), Toast.LENGTH_SHORT).show();
            return;
        }
        if (product == null) {
            Toast.makeText(this, "Select a product", Toast.LENGTH_SHORT).show();
            return;
        }
        Map<String, String> flashFiles = product.resolveFlashFiles(model);
        if (flashFiles == null || flashFiles.isEmpty()) {
            Toast.makeText(this, "No ESP flash map for this product (nRF52 not in MVP)", Toast.LENGTH_LONG)
                .show();
            return;
        }
        if (firmwareBytes == null) {
            Toast.makeText(this, "Download firmware first", Toast.LENGTH_SHORT).show();
            return;
        }
        setBusy(true);
        setStatus(getString(R.string.rnode_flasher_busy));
        final byte[] zip = firmwareBytes;
        final String deviceId = port.deviceId;
        io.execute(() -> {
            try {
                List<Esp32SerialFlasher.Image> images =
                    Esp32SerialFlasher.imagesFromZip(zip, flashFiles);
                usbHub.open(deviceId, 115200);
                Esp32SerialFlasher flasher =
                    new Esp32SerialFlasher(
                        usbHub,
                        new Esp32SerialFlasher.Progress() {
                            @Override
                            public void onStatus(String message) {
                                mainHandler.post(() -> {
                                    setStatus(message);
                                    appendLog(message);
                                });
                            }

                            @Override
                            public void onProgress(int percent) {
                                mainHandler.post(() -> progressBar.setProgress(percent));
                            }
                        }
                    );
                flasher.flash(images, 460800);
                mainHandler.post(() -> {
                    setBusy(false);
                    setStatus("Flash complete");
                    Toast.makeText(this, "Flash complete", Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    setBusy(false);
                    setStatus("Flash failed");
                    appendLog("Flash error: " + e.getMessage());
                    Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show();
                });
            } finally {
                if (usbHub != null) {
                    usbHub.close();
                }
            }
        });
    }

    /**
     * Resolve the effective backend origin, matching MainActivity so the flasher
     * still works when the shell is configured against a remote backend instead
     * of the on-device local API.
     */
    private String resolveApiBaseUrl() {
        SharedPreferences prefs = getSharedPreferences(SHELL_PREFS, MODE_PRIVATE);
        return RemoteBackendUrl.resolveEffectiveUrl(prefs.getString(PREF_REMOTE_BACKEND_URL, null));
    }

    /**
     * The localhost-only client skips certificate validation for the embedded
     * self-signed 127.0.0.1 server. A configured remote backend must keep normal
     * system certificate validation, so it gets a plain OkHttpClient instead.
     */
    private OkHttpClient httpClientFor(String apiBaseUrl) {
        if (RemoteBackendUrl.isLocalBackendUrl(apiBaseUrl)) {
            return LocalhostTrustOkHttpClient.get();
        }
        return new OkHttpClient.Builder().connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS).build();
    }

    private byte[] fetchFirmwareZip(String filename) throws Exception {
        String apiBaseUrl = resolveApiBaseUrl();
        OkHttpClient client = httpClientFor(apiBaseUrl);
        // Resolve latest release asset URL via the backend API, then download through proxy.
        String releaseUrl = apiBaseUrl + "/api/v1/tools/rnode/latest_release";
        Request releaseReq = authorizedGet(apiBaseUrl, releaseUrl);
        String assetUrl;
        try (Response response = client.newCall(releaseReq).execute()) {
            if (!response.isSuccessful() || response.body() == null) {
                throw new IllegalStateException("latest_release HTTP " + response.code());
            }
            JSONObject release = new JSONObject(response.body().string());
            JSONArray assets = release.optJSONArray("assets");
            assetUrl = null;
            if (assets != null) {
                for (int i = 0; i < assets.length(); i++) {
                    JSONObject asset = assets.getJSONObject(i);
                    if (filename.equals(asset.optString("name"))) {
                        assetUrl = asset.optString("browser_download_url");
                        break;
                    }
                }
            }
            if (assetUrl == null || assetUrl.isEmpty()) {
                assetUrl =
                    "https://github.com/markqvist/RNode_Firmware/releases/latest/download/"
                        + filename;
            }
        }
        String downloadUrl =
            apiBaseUrl
                + "/api/v1/tools/rnode/download_firmware?url="
                + Uri.encode(assetUrl);
        Request dlReq = authorizedGet(apiBaseUrl, downloadUrl);
        try (Response response = client.newCall(dlReq).execute()) {
            if (!response.isSuccessful() || response.body() == null) {
                throw new IllegalStateException("download_firmware HTTP " + response.code());
            }
            ResponseBody body = response.body();
            return body.bytes();
        }
    }

    private Request authorizedGet(String apiBaseUrl, String url) {
        Request.Builder builder = new Request.Builder().url(url).get();
        String cookie = CookieManager.getInstance().getCookie(apiBaseUrl);
        if (cookie != null && !cookie.isEmpty()) {
            builder.header("Cookie", cookie);
        }
        return builder.build();
    }

    @Nullable
    private UsbSerialHub.PortInfo selectedPort() {
        int idx = usbSpinner.getSelectedItemPosition();
        if (idx < 0 || idx >= ports.size()) {
            return null;
        }
        return ports.get(idx);
    }

    @Nullable
    private ProductCatalog.Product selectedProduct() {
        Object item = productSpinner.getSelectedItem();
        return item instanceof ProductCatalog.Product ? (ProductCatalog.Product) item : null;
    }

    @Nullable
    private ProductCatalog.Model selectedModel() {
        Object item = modelSpinner.getSelectedItem();
        return item instanceof ProductCatalog.Model ? (ProductCatalog.Model) item : null;
    }

    private void setBusy(boolean busy) {
        flashButton.setEnabled(!busy);
        downloadButton.setEnabled(!busy);
        progressBar.setIndeterminate(busy && progressBar.getProgress() == 0);
    }

    private void setStatus(String text) {
        statusView.setText(text);
    }

    private void appendLog(String line) {
        CharSequence existing = logView.getText();
        if (existing == null || existing.length() == 0) {
            logView.setText(line);
        } else {
            logView.setText(existing + "\n" + line);
        }
    }
}
