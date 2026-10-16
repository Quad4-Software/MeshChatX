import { describe, it, expect } from "vitest";
import { brand } from "../../meshchatx/src/frontend/js/brand.js";
import fs from "fs";
import path from "path";

const brandJson = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "brand.json"), "utf8"));

describe("frontend brand consumer", () => {
    it("exposes the brand.json values", () => {
        expect(brand.name).toBe(brandJson.name);
        expect(brand.repository).toBe(brandJson.repository);
        expect(brand.homepage).toBe(brandJson.homepage);
        expect(brand.app_id).toBe(brandJson.app_id);
    });

    it("derives issue and flatpak URLs from the repository", () => {
        expect(brand.issues_url).toBe(`https://github.com/${brandJson.repository}/issues`);
        const [owner, repo] = brandJson.repository.split("/");
        expect(brand.flatpak_repo_base_url).toBe(`https://${owner.toLowerCase()}.github.io/${repo}/flatpak`);
        expect(brand.repo_url).toBe(`https://github.com/${brandJson.repository}`);
    });

    it("has no empty required values", () => {
        for (const key of ["name", "product_name", "slug", "app_id", "repository", "homepage"]) {
            expect(brand[key], key).toBeTruthy();
        }
    });
});
