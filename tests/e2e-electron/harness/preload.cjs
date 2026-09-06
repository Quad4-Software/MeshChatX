// SPDX-License-Identifier: 0BSD
"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronE2e", {
    ready: true,
    normalizeExternalUrl: (raw) => ipcRenderer.invoke("e2e-normalize-external-url", raw),
});
