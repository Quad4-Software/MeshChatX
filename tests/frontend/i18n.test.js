import { describe, it, expect } from "vitest";
import en from "../../meshchatx/src/frontend/locales/en.json";
import de from "../../meshchatx/src/frontend/locales/de.json";
import ru from "../../meshchatx/src/frontend/locales/ru.json";
import itLocale from "../../meshchatx/src/frontend/locales/it.json";
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

describe("i18n Localization Tests", () => {
    const enKeys = getKeys(en);
    const locales = [
        { name: "German", data: de, keys: getKeys(de) },
        { name: "Russian", data: ru, keys: getKeys(ru) },
        { name: "Italian", data: itLocale, keys: getKeys(itLocale) },
    ];

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

    it("should find all $t usage in components and ensure they exist in en.json", () => {
        const frontendDir = path.resolve(__dirname, "../../meshchatx/src/frontend");
        const files = [];

        function walkDir(dir) {
            fs.readdirSync(dir).forEach((file) => {
                const fullPath = path.join(dir, file);
                if (fs.statSync(fullPath).isDirectory()) {
                    if (file !== "node_modules" && file !== "dist" && file !== "assets") {
                        walkDir(fullPath);
                    }
                } else if (file.endsWith(".vue") || file.endsWith(".js")) {
                    files.push(fullPath);
                }
            });
        }

        walkDir(frontendDir);

        const foundKeys = new Set();
        // Regex to find $t('key') or $t("key") or $t(`key`) or $t('key', ...)
        // Also supports {{ $t('key') }}
        const tRegex = /\$t\s*\(\s*['"`]([^'"`]+)['"`]/g;

        files.forEach((file) => {
            const content = fs.readFileSync(file, "utf8");
            let match;
            while ((match = tRegex.exec(content)) !== null) {
                foundKeys.add(match[1]);
            }
        });

        const missingInEn = Array.from(foundKeys).filter((key) => {
            // Check if key exists in nested object 'en'
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
        // Some keys might be dynamic, so we might want to be careful with this test
        // But for now, let's see what it finds.
        // We expect some false positives if keys are constructed dynamically.
        expect(nonDynamicMissing.length).toBe(0);
    });
});
