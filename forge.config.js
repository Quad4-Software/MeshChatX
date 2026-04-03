const { FusesPlugin } = require("@electron-forge/plugin-fuses");
const { FuseV1Options, FuseVersion } = require("@electron/fuses");

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
        asar: true,
        extraResource: [extraResourceDir],
        executableName: "reticulum-meshchatx",
        name: "Reticulum MeshChatX",
        appBundleId: "com.sudoivan.reticulummeshchatx",
        icon: "electron/build/icon",
        // osxSign: {}, // Uncomment and configure for macOS signing
        // osxNotarize: { ... }, // Uncomment and configure for macOS notarization
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
                    maintainer: "Sudo-Ivan",
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
            name: "@electron-forge/maker-flatpak",
            config: {
                options: {
                    categories: ["Network"],
                    runtime: "org.freedesktop.Platform",
                    runtimeVersion: "24.08",
                    sdk: "org.freedesktop.Sdk",
                    base: "org.electronjs.Electron2.BaseApp",
                    baseVersion: "24.08",
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
            [FuseV1Options.RunAsNode]: false,
            [FuseV1Options.EnableCookieEncryption]: true,
            [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
            [FuseV1Options.EnableNodeCliInspectArguments]: false,
            [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
            [FuseV1Options.OnlyLoadAppFromAsar]: true,
        }),
    ],
};
