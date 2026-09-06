// SPDX-License-Identifier: 0BSD
"use strict";

/**
 * Minimal Electron shell for Playwright _electron.launch smoke.
 * Does not start the Python backend.
 */

const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");
const { normalizeExternalUrlForOpen } = require("../../../electron/safeExternalUrl");

ipcMain.handle("e2e-normalize-external-url", (_event, raw) => normalizeExternalUrlForOpen(raw));

let mainWindow = null;

app.whenReady().then(async () => {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 700,
        show: true,
        webPreferences: {
            preload: path.join(__dirname, "preload.cjs"),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
        },
    });
    await mainWindow.loadFile(path.join(__dirname, "index.html"));
});

app.on("window-all-closed", () => {
    app.quit();
});
