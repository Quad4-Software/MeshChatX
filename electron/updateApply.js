// SPDX-License-Identifier: 0BSD
// Apply a backend-staged update payload (updates/pending) to an AppImage
// install. The backend has already verified the payload against the signed
// update manifest and written updates/pending.json under the storage dir.
// This module reads that marker itself, confines the payload to the
// pending directory, and re-hashes before swapping, so a compromised or
// confused renderer cannot steer an arbitrary file onto the AppImage path.

const crypto = require("crypto");
const fs = require("fs");
const path = require("node:path");

const PENDING_DIR = path.join("updates", "pending");
const PENDING_MARKER = path.join("updates", "pending.json");

function sha256File(filePath) {
    const h = crypto.createHash("sha256");
    h.update(fs.readFileSync(filePath));
    return h.digest("hex");
}

function readPendingMarker(storageDir) {
    try {
        const raw = fs.readFileSync(path.join(storageDir, PENDING_MARKER), "utf8");
        const marker = JSON.parse(raw);
        return marker && typeof marker === "object" ? marker : null;
    } catch {
        return null;
    }
}

function clearPending(storageDir) {
    try {
        fs.unlinkSync(path.join(storageDir, PENDING_MARKER));
    } catch {
        // marker already gone
    }
}

// Returns {applied: true} on success or {applied: false, error}.
function applyPendingUpdate(storageDir) {
    const marker = readPendingMarker(storageDir);
    if (!marker) {
        return { applied: false, error: "no_pending_update" };
    }
    const file = typeof marker.file === "string" ? marker.file : "";
    const sha256 = typeof marker.sha256 === "string" ? marker.sha256 : "";
    const kind = typeof marker.kind === "string" ? marker.kind : "";
    if (!file || path.basename(file) !== file || !/^[0-9a-f]{64}$/i.test(sha256)) {
        return { applied: false, error: "bad_pending_marker" };
    }
    if (kind !== "appimage") {
        return { applied: false, error: "unsupported_kind", kind };
    }
    const target = process.env.APPIMAGE;
    if (!target) {
        return { applied: false, error: "not_appimage" };
    }
    const pendingDir = path.resolve(storageDir, PENDING_DIR);
    const stagedPath = path.resolve(pendingDir, file);
    if (!stagedPath.startsWith(pendingDir + path.sep)) {
        return { applied: false, error: "path_escape" };
    }
    if (!fs.existsSync(stagedPath) || !fs.statSync(stagedPath).isFile()) {
        return { applied: false, error: "staged_missing" };
    }
    if (sha256File(stagedPath) !== sha256.toLowerCase()) {
        return { applied: false, error: "sha256_mismatch" };
    }

    const targetPath = path.resolve(target);
    if (stagedPath === targetPath) {
        return { applied: false, error: "same_path" };
    }

    // Keep a rollback copy of the current image, then atomic-rename the
    // verified payload into place. Renaming over a running AppImage is safe
    // on Linux: the FUSE mount keeps the old inode until exit.
    const backup = targetPath + ".bak";
    try {
        fs.copyFileSync(targetPath, backup);
    } catch {
        // Non-fatal: proceed without a rollback copy if the source cannot
        // be duplicated (e.g. read-only mount).
    }
    try {
        fs.chmodSync(stagedPath, 0o755);
        fs.renameSync(stagedPath, targetPath);
    } catch (e) {
        return { applied: false, error: `swap_failed: ${e && e.message}` };
    }
    clearPending(storageDir);
    return { applied: true };
}

module.exports = { applyPendingUpdate, sha256File, readPendingMarker };
