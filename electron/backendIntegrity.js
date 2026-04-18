"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("node:path");

/**
 * Verify SHA-256 hashes of backend files against backend-manifest.json next to the executable.
 * @param {string} exeDir Directory containing the backend binary and manifest.
 * @returns {{ ok: boolean, issues: string[] }}
 */
function verifyBackendIntegrity(exeDir) {
    const manifestPath = path.join(exeDir, "backend-manifest.json");
    if (!fs.existsSync(manifestPath)) {
        return { ok: true, issues: ["Manifest missing"] };
    }

    try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
        const issues = [];

        const filesToVerify = manifest.files || manifest;
        const metadata = manifest._metadata || {};

        for (const [relPath, expectedHash] of Object.entries(filesToVerify)) {
            const fullPath = path.join(exeDir, relPath);
            if (!fs.existsSync(fullPath)) {
                issues.push(`Missing: ${relPath}`);
                continue;
            }

            const fileBuffer = fs.readFileSync(fullPath);
            const actualHash = crypto.createHash("sha256").update(fileBuffer).digest("hex");
            if (actualHash !== expectedHash) {
                issues.push(`Modified: ${relPath}`);
            }
        }

        if (issues.length > 0 && metadata.date && metadata.time) {
            issues.unshift(`Backend build timestamp: ${metadata.date} ${metadata.time}`);
        }

        return {
            ok: issues.length === 0,
            issues: issues,
        };
    } catch (error) {
        return { ok: false, issues: [error.message] };
    }
}

module.exports = { verifyBackendIntegrity };
