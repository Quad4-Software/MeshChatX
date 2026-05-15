const { FusesPlugin } = require("@electron-forge/plugin-fuses");
const { FuseV1Options, FuseVersion } = require("@electron/fuses");
const which = require("which");
const path = require("path");

function hasExecutable(name) {
    return which.sync(name, { nothrow: true }) !== null;
}

const forgeSnapExplicit = process.env.FORGE_MAKE_SNAP === "1" || process.env.FORGE_MAKE_SNAP === "true";
const forgeFlatpakExplicit = process.env.FORGE_MAKE_FLATPAK === "1" || process.env.FORGE_MAKE_FLATPAK === "true";

const forgeSnapEnabled = hasExecutable("snapcraft") || forgeSnapExplicit;
const forgeFlatpakEnabled = (hasExecutable("flatpak-builder") && hasExecutable("eu-strip")) || forgeFlatpakExplicit;

const platform = process.env.PLATFORM || process.platform;
const arch = process.env.ARCH || process.arch;
let extraResourceDir = `build/exe/linux-${arch}`;
if (platform === "win32" || platform === "win") {
    extraResourceDir = `build/exe/win32-${arch}`;
} else if (platform === "darwin") {
    extraResourceDir = `build/exe/darwin-${arch}`;
}

module.exports = {
    packagerConfig: {
        asar: {
            unpack: "electron/{loading.html,crash.html,preload.js}",
        },
        ignore: [
            /^\/\.flatpak-builder(\/|$)/,
            /^\/\.snapcraft(\/|$)/,
            /^\/parts(\/|$)/,
            /^\/prime(\/|$)/,
            /^\/stage(\/|$)/,
        ],
        extraResource: [extraResourceDir],
        executableName: "reticulum-meshchatx",
        name: "Reticulum MeshChatX",
        appBundleId: "com.meshchatx",
        icon: "electron/build/icon",
        // osxSign: {}, macOS signing
        // osxNotarize: { ... }, macOS notarization
    },
    rebuildConfig: {},
    makers: [
        {
            name: "@electron-forge/maker-squirrel",
            config: {
                name: "reticulum_meshchatx",
            },
        },
        {
            name: "@electron-forge/maker-zip",
        },
        {
            name: "@electron-forge/maker-deb",
            config: {
                options: {
                    maintainer: "Quad4",
                    homepage: "https://git.quad4.io/RNS-Things/MeshChatX",
                    categories: ["Network"],
                },
            },
        },
        {
            name: "@electron-forge/maker-rpm",
            config: {},
        },
        {
            name: "@electron-forge/maker-snap",
            enabled: forgeSnapEnabled,
            config: {
                summary: "Mesh networking chat client",
                description: "A simple mesh network communications app powered by the Reticulum Network Stack",
                confinement: "strict",
                grade: "devel",
                base: "core22",
                appConfig: {
                    extensions: ["gnome"],
                },
                features: {
                    audio: true,
                    webgl: true,
                },
            },
        },
        {
            name: "@electron-forge/maker-flatpak",
            enabled: forgeFlatpakEnabled,
            config: {
                options: {
                    categories: ["Network"],
                    // electron-installer-flatpak still defaults to zypak v2021.02, which hardcodes
                    // clang++; org.freedesktop.Sdk 25.08 does not ship clang++ on PATH. Match
                    // org.electronjs.Electron2.BaseApp 25.08 (g++ / C++20).
                    modules: [
                        {
                            name: "zypak",
                            sources: [
                                {
                                    type: "git",
                                    url: "https://github.com/refi64/zypak",
                                    tag: "v2025.09",
                                    commit: "693a71c5ffa80ec9c9ce2ae03b1ccc493c698e53",
                                },
                            ],
                        },
                    ],
                    runtime: "org.freedesktop.Platform",
                    runtimeVersion: "25.08",
                    sdk: "org.freedesktop.Sdk",
                    base: "org.electronjs.Electron2.BaseApp",
                    baseVersion: "25.08",
                    // Custom desktop template for proper StartupWMClass
                    desktopTemplate: path.join(__dirname, "electron", "flatpak-desktop.ejs"),
                    finishArgs: [
                        "--share=ipc",
                        "--share=network",
                        "--socket=x11",
                        "--socket=wayland",
                        "--device=dri",
                        "--allow=bluetooth",
                        "--filesystem=home",
                        "--talk-name=org.freedesktop.Notifications",
                        "--talk-name=org.freedesktop.DBus",
                        "--talk-name=org.freedesktop.portal.Desktop",
                        "--own-name=com.meshchatx",
                        "--env=TMPDIR=/var/tmp",
                        "--socket=pulseaudio",
                        "--filesystem=xdg-run/pipewire-0",
                    ],
                    extraFlatpakBuilderArgs: ["--verbose"],
                },
            },
        },
    ],
    plugins: [
        {
            name: "@electron-forge/plugin-auto-unpack-natives",
            config: {},
        },
        // Fuses are used to enable/disable various Electron functionality
        // at package time, before code signing the application
        new FusesPlugin({
            version: FuseVersion.V1,
            resetAdHocDarwinSignature: process.platform === "darwin" || platform === "darwin",
            [FuseV1Options.RunAsNode]: false,
            [FuseV1Options.EnableCookieEncryption]: true,
            [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
            [FuseV1Options.EnableNodeCliInspectArguments]: false,
            [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
            [FuseV1Options.OnlyLoadAppFromAsar]: true,
        }),
    ],
};
