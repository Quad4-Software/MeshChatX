/**
 * Single source of truth: set "version" in package.json, then run:
 *   pnpm run version:sync
 *
 * Writes: meshchatx/__init__.py (__version__), meshchatx/src/version.py, pyproject.toml [project].version,
 * meshchatx/src/backend/data/THIRD_PARTY_NOTICES.txt (reticulum-meshchatx line only),
 * README + lang README "current version" lines, docs/meshchatx_on_raspberry_pi.md
 * (and meshchatx/src/frontend/public/meshchatx-docs copy), android/app/build.gradle,
 * pipx example, packaging/arch/PKGBUILD pkgver / printf fallback.
 *
 * __version__ lives in meshchatx/__init__.py so Chaquopy/Android (which may not ship loose .py
 * data files next to bytecode) always has a resolvable version. src/version.py stays for packaging and tools.
 * The build script runs version:sync automatically.
 */

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pkgPath = path.join(root, "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
const version = pkg.version;
if (!version || typeof version !== "string") {
    console.error("package.json has no valid 'version' field");
    process.exit(1);
}

function writeIfChanged(absPath, content) {
    const prev = fs.existsSync(absPath) ? fs.readFileSync(absPath, "utf8") : null;
    if (prev !== content) {
        fs.writeFileSync(absPath, content, "utf8");
        console.log(`Updated ${path.relative(root, absPath)}`);
    }
}

const versionPy = `"""Version string synced from package.json.

Do not edit by hand. Run: pnpm run version:sync
"""

__version__ = "${version}"
`;
writeIfChanged(path.join(root, "meshchatx", "src", "version.py"), versionPy);

patchFile("meshchatx/__init__.py", (c) => c.replace(/^__version__\s*=\s*"[^"]*"\s*$/m, `__version__ = "${version}"`));

const pyprojectPath = path.join(root, "pyproject.toml");
let pyproject = fs.readFileSync(pyprojectPath, "utf8");
const pyprojectNext = pyproject.replace(/^version = "[^"]+"/m, `version = "${version}"`);
if (pyprojectNext !== pyproject) {
    fs.writeFileSync(pyprojectPath, pyprojectNext, "utf8");
    console.log(`Updated ${path.relative(root, pyprojectPath)}`);
}

const noticesPath = path.join(root, "meshchatx", "src", "backend", "data", "THIRD_PARTY_NOTICES.txt");
if (fs.existsSync(noticesPath)) {
    let notices = fs.readFileSync(noticesPath, "utf8");
    const noticesNext = notices.replace(/^reticulum-meshchatx .+$/m, `reticulum-meshchatx ${version}`);
    if (noticesNext !== notices) {
        fs.writeFileSync(noticesPath, noticesNext, "utf8");
        console.log(`Updated ${path.relative(root, noticesPath)}`);
    }
}

function patchFile(rel, fn) {
    const abs = path.join(root, rel);
    if (!fs.existsSync(abs)) {
        return;
    }
    const before = fs.readFileSync(abs, "utf8");
    const after = fn(before);
    if (after !== before) {
        fs.writeFileSync(abs, after, "utf8");
        console.log(`Updated ${rel}`);
    }
}

patchFile("README.md", (c) => c.replace(/(Current version in this repo is `)[^`]+(`)/, `$1${version}$2`));

patchFile("lang/README.de.md", (c) =>
    c.replace(/(Aktuelle Version in diesem Repository: `)[^`]+(`)/, `$1${version}$2`)
);
patchFile("lang/README.it.md", (c) => c.replace(/(Versione attuale nel repository: `)[^`]+(`)/, `$1${version}$2`));
patchFile("lang/README.ja.md", (c) =>
    c.replace(/(このリポジトリの現在のバージョンは `)[^`]+(` です。)/, `$1${version}$2`)
);
patchFile("lang/README.ru.md", (c) => c.replace(/(Текущая версия в репозитории: `)[^`]+(`)/, `$1${version}$2`));
patchFile("lang/README.zh.md", (c) => c.replace(/(本仓库当前版本: `)[^`]+(`)/, `$1${version}$2`));

function patchRaspberryPiDoc(c) {
    let x = c;
    x = x.replace(/\(\d+\.\d+\.\d+ or newer\)/, `(${version} or newer)`);
    x = x.replace(/Direct example \(v\d+\.\d+\.\d+\):/, `Direct example (v${version}):`);
    x = x.replace(
        /releases\/download\/v\d+\.\d+\.\d+\/reticulum_meshchatx-\d+\.\d+\.\d+-py3-none-any\.whl/g,
        `releases/download/v${version}/reticulum_meshchatx-${version}-py3-none-any.whl`
    );
    return x;
}

patchFile("docs/meshchatx_on_raspberry_pi.md", patchRaspberryPiDoc);
patchFile("meshchatx/src/frontend/public/meshchatx-docs/meshchatx_on_raspberry_pi.md", patchRaspberryPiDoc);

const versionParts = version.split(".").map((n) => Number.parseInt(n, 10));
if (versionParts.length === 3 && versionParts.every((n) => Number.isFinite(n))) {
    const versionCode = versionParts[0] * 10000 + versionParts[1] * 1000 + versionParts[2];
    patchFile("android/app/build.gradle", (c) => {
        let x = c.replace(/versionCode \d+/, `versionCode ${versionCode}`);
        x = x.replace(/versionName "[^"]+"/, `versionName "${version}"`);
        return x;
    });
}

patchFile("packaging/arch/PKGBUILD", (c) => {
    let x = c.replace(/^pkgver=\d+\.\d+\.\d+(.*)$/m, `pkgver=${version}$1`);
    x = x.replace(/printf "\d+\.\d+\.\d+\.r%s\.%s"/, `printf "${version}.r%s.%s"`);
    return x;
});

console.log(`Synced version ${version} from package.json`);
