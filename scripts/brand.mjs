// SPDX-License-Identifier: 0BSD
// brand.json loader shared by Node scripts and the brand drift check.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

export const BRAND_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "brand.json");

export function loadBrand(file = BRAND_PATH) {
    const brand = JSON.parse(fs.readFileSync(file, "utf8"));
    if (!brand.flatpak_repo_base_url && brand.repository?.includes("/")) {
        const [owner, name] = brand.repository.split("/");
        brand.flatpak_repo_base_url = `https://${owner.toLowerCase()}.github.io/${name}/flatpak`;
    }
    if (!brand.issues_url && brand.repository) {
        brand.issues_url = `https://github.com/${brand.repository}/issues`;
    }
    return brand;
}
