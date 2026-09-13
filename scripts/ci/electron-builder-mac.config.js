const fs = require("fs");
const path = require("path");

module.exports = function (request) {
    const projectDir = request?.projectDir || process.cwd();
    const packageJsonPath = path.join(projectDir, "package.json");
    const pkg = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
    const config = { ...pkg.build };

    const isX64 = (process.argv || []).some((arg) => arg === "--x64" || arg === "-x64");
    const arch = isX64 ? "x64" : "arm64";

    // Per-arch DMG builds must not inherit the universal target from
    // package.json, and they must keep the files filter so that .venv and
    // other project artifacts are not bundled into the asar.
    config.mac = {
        ...config.mac,
        target: [
            {
                target: "dmg",
                arch: [arch],
            },
        ],
    };

    return config;
};
