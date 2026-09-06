const fs = require("fs");
const path = require("path");

module.exports = function (request) {
    const projectDir = (request && request.projectDir) || process.cwd();
    const packageJsonPath = path.join(projectDir, "package.json");
    const pkg = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
    const config = pkg.build || {};

    const args = process.argv || [];
    let arch = "arm64";
    if (args.includes("--x64") || args.includes("-x64")) {
        arch = "x64";
    } else if (args.includes("--arm64") || args.includes("-arm64")) {
        arch = "arm64";
    }

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
