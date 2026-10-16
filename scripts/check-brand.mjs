#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
// Drift check: every static surface that cannot be templated cheaply must
// match brand.json. Exits 1 and names the file/expected value on mismatch.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { loadBrand } from "./brand.mjs";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

export function checkBrand(brand, brandPath = path.join(root, "brand.json")) {
    const failures = [];
    const expectFile = (rel, needle, field) => {
        const file = path.join(root, rel);
        let text;
        try {
            text = fs.readFileSync(file, "utf8");
        } catch {
            failures.push(`${rel}: file missing (expected ${field} "${needle}")`);
            return;
        }
        if (!text.includes(needle)) {
            failures.push(`${rel}: expected ${field} "${needle}" from ${brandPath}`);
        }
    };

    const checks = [
        ["package.json", brand.app_id, "app_id"],
        ["package.json", brand.name, "name"],
        ["packaging/flatpak/com.meshchatx.app.metainfo.xml", brand.app_id, "app_id"],
        ["packaging/flatpak/com.meshchatx.app.desktop", brand.slug, "slug"],
        ["packaging/arch/PKGBUILD", "reticulum-meshchatx", "slug"],
        ["pyproject.toml", `https://github.com/${brand.repository}`, "repository"],
        ["meshchatx/src/frontend/public/manifest.json", brand.name, "name"],
        ["meshchatx/src/frontend/index.html", brand.name, "name"],
        ["helm/meshchatx/Chart.yaml", brand.slug, "slug"],
        ["android/app/build.gradle", "com.meshchatx", "slug"],
        ["SECURITY.md", brand.security_contact, "security_contact"],
        ["docker/docker-compose.yml", brand.docker_hub_image, "docker_hub_image"],
        ["docker/docker-compose.coolify.yml", brand.docker_hub_image, "docker_hub_image"],
        ["docker/docker-compose.demo.yml", brand.docker_hub_image, "docker_hub_image"],
        ["helm/meshchatx/values.yaml", brand.docker_hub_image, "docker_hub_image"],
        ["ansible/meshchatx/defaults/main.yml", brand.docker_hub_image, "docker_hub_image"],
        ["proxmox/build-vm-template.sh", brand.docker_hub_image, "docker_hub_image"],
        ["proxmox/build-lxc.sh", brand.docker_hub_image, "docker_hub_image"],
        ["helm/meshchatx/Chart.yaml", `https://github.com/${brand.repository}`, "repository"],
    ];
    for (const [rel, needle, field] of checks) {
        if (fs.existsSync(path.join(root, rel))) {
            expectFile(rel, needle, field);
        }
    }
    return failures;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const brand = loadBrand();
    const failures = checkBrand(brand);
    if (failures.length) {
        for (const f of failures) {
            console.error(`brand drift: ${f}`);
        }
        process.exit(1);
    }
    console.log("brand:check OK");
}
