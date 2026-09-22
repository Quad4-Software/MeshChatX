import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

function getKeys(obj, prefix = "") {
    return Object.keys(obj).reduce((res, el) => {
        if (Array.isArray(obj[el])) {
            return res;
        } else if (typeof obj[el] === "object" && obj[el] !== null) {
            return [...res, ...getKeys(obj[el], prefix + el + ".")];
        }
        return [...res, prefix + el];
    }, []);
}

const localesDir = path.resolve(__dirname, "../../meshchatx/src/frontend/locales");
const localeFiles = fs.readdirSync(localesDir).filter((f) => f.endsWith(".json"));
const allLocales = {};
for (const file of localeFiles) {
    const code = file.replace(".json", "");
    allLocales[code] = JSON.parse(fs.readFileSync(path.join(localesDir, file), "utf-8"));
}

const en = allLocales["en"];

describe("i18n Localization Tests", () => {
    const enKeys = getKeys(en);
    const locales = Object.entries(allLocales)
        .filter(([code]) => code !== "en")
        .map(([code, data]) => ({
            name: data._languageName || code,
            data,
            keys: getKeys(data),
        }));

    it("should have _languageName in every locale", () => {
        const missing = Object.entries(allLocales)
            .filter(([, data]) => !data._languageName || typeof data._languageName !== "string")
            .map(([code]) => code);
        expect(missing).toEqual([]);
    });

    locales.forEach((locale) => {
        it(`should have all keys from en.json in ${locale.name}`, () => {
            const missingKeys = enKeys.filter((key) => !locale.keys.includes(key));
            if (missingKeys.length > 0) {
                console.warn(`Missing keys in ${locale.name}:`, missingKeys);
            }
            expect(missingKeys).toEqual([]);
        });

        it(`should not have extra keys in ${locale.name} that are not in en.json`, () => {
            const extraKeys = locale.keys.filter((key) => !enKeys.includes(key));
            if (extraKeys.length > 0) {
                console.warn(`Extra keys in ${locale.name}:`, extraKeys);
            }
            expect(extraKeys).toEqual([]);
        });
    });

    it("should find all $t and t() usage in components and ensure they exist in en.json", () => {
        const frontendDir = path.resolve(__dirname, "../../meshchatx/src/frontend");
        const files = [];
        const skipDirs = new Set(["node_modules", "dist", "assets", "public", "locales"]);

        function walkDir(dir) {
            fs.readdirSync(dir).forEach((file) => {
                const fullPath = path.join(dir, file);
                if (fs.statSync(fullPath).isDirectory()) {
                    if (!skipDirs.has(file)) {
                        walkDir(fullPath);
                    }
                } else if (file.endsWith(".js") || file.endsWith(".ts") || file.endsWith(".svelte")) {
                    files.push(fullPath);
                }
            });
        }

        walkDir(frontendDir);

        const foundKeys = new Set();
        // Framework-free t('key') from js/i18n (Svelte / feature libs)
        const tRegex = /(?:\$t|\bt)\s*\(\s*['"`]([^'"`]+)['"`]/g;

        files.forEach((file) => {
            const content = fs.readFileSync(file, "utf8");
            let match;
            while ((match = tRegex.exec(content)) !== null) {
                foundKeys.add(match[1]);
            }
        });

        const missingInEn = Array.from(foundKeys).filter((key) => {
            const parts = key.split(".");
            let current = en;
            for (const part of parts) {
                if (current[part] === undefined) {
                    return true;
                }
                current = current[part];
            }
            return false;
        });

        const nonDynamicMissing = missingInEn.filter((k) => !k.includes("${"));
        if (nonDynamicMissing.length > 0) {
            console.warn("Keys used in code but missing in en.json:", nonDynamicMissing);
        }
        expect(nonDynamicMissing.length).toBe(0);
    });

    it("frontend tree has no remaining .vue sources", () => {
        const frontendDir = path.resolve(__dirname, "../../meshchatx/src/frontend");
        const vueFiles = [];
        function walk(dir) {
            for (const name of fs.readdirSync(dir)) {
                const full = path.join(dir, name);
                if (fs.statSync(full).isDirectory()) walk(full);
                else if (name.endsWith(".vue")) vueFiles.push(full);
            }
        }
        walk(frontendDir);
        expect(vueFiles).toEqual([]);
    });

    it("keeps archives page keys present in every locale", () => {
        const required = [
            "archives.title",
            "archives.description",
            "archives.search_placeholder",
            "archives.recrawl",
            "archives.recrawl_pending",
            "archives.recrawl_done",
            "archives.recrawl_failed",
            "archives.never_crawl",
            "archives.back_to_list",
            "archives.rendering",
            "archives.view",
            "archives.clear_search",
            "archives.matches_count",
        ];
        for (const key of required) {
            const parts = key.split(".");
            for (const [code, data] of Object.entries(allLocales)) {
                let current = data;
                for (const part of parts) {
                    expect(current?.[part], `${code} missing ${key}`).toBeDefined();
                    current = current[part];
                }
                expect(typeof current, `${code} ${key} type`).toBe("string");
                expect(String(current).trim().length, `${code} ${key} empty`).toBeGreaterThan(0);
            }
        }
    });

    it("keeps docs upload/share keys present in every locale", () => {
        const required = [
            "docs.btn_share",
            "docs.error",
            "docs.failed_upload_docs",
            "docs.upload_success",
            "common.prompt_title",
        ];
        for (const key of required) {
            const parts = key.split(".");
            for (const [code, data] of Object.entries(allLocales)) {
                let current = data;
                for (const part of parts) {
                    expect(current?.[part], `${code} missing ${key}`).toBeDefined();
                    current = current[part];
                }
                expect(typeof current).toBe("string");
                expect(current.length).toBeGreaterThan(0);
            }
        }
    });

    it("keeps FS sandbox status keys present in every locale", () => {
        const required = [
            "app.landlock_status",
            "app.landlock_active",
            "app.landlock_inactive",
            "app.landlock_auto_enabled",
            "app.landlock_kernel_unsupported",
            "app.landlock_disabled_by_env",
            "app.appcontainer_status",
            "app.appcontainer_active",
            "app.appcontainer_inactive",
            "app.appcontainer_auto_enabled",
            "app.appcontainer_unsupported",
            "app.appcontainer_disabled_by_env",
            "app.seccomp_status",
            "app.seccomp_active",
            "app.seccomp_inactive",
            "app.seccomp_auto_enabled",
            "app.seccomp_kernel_unsupported",
            "app.seccomp_disabled_by_env",
        ];
        for (const key of required) {
            const parts = key.split(".");
            for (const [code, data] of Object.entries(allLocales)) {
                let current = data;
                for (const part of parts) {
                    expect(current?.[part], `${code} missing ${key}`).toBeDefined();
                    current = current[part];
                }
                expect(typeof current, `${code} ${key} type`).toBe("string");
                expect(String(current).trim().length, `${code} ${key} empty`).toBeGreaterThan(0);
            }
        }
    });
});
