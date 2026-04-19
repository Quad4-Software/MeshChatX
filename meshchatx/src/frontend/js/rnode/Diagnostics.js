import RNodeUtils from "./RNodeUtils.js";

/**
 * Smart diagnostics for connected RNode devices.
 *
 * Given an open RNode handle, inspect()/inspectQuiet() will try to read the
 * essential identification & state from the device and return a structured
 * report including i18n suggestion keys for any issues detected.
 *
 * The suggestion keys map directly to entries under
 * tools.rnode_flasher.diagnostics.* in the locale files, so the UI does not
 * need any logic to translate raw issue identifiers.
 */

export const ISSUE_NOT_PROVISIONED = "not_provisioned";
export const ISSUE_FIRMWARE_HASH_MISSING = "firmware_hash_missing";
export const ISSUE_FIRMWARE_HASH_MISMATCH = "firmware_hash_mismatch";
export const ISSUE_PRODUCT_MISMATCH = "product_mismatch";
export const ISSUE_NO_FIRMWARE_VERSION = "no_firmware_version";
export const ISSUE_DETECT_FAILED = "detect_failed";
export const ISSUE_READ_TIMEOUT = "read_timeout";

const ALL_ISSUE_KEYS = new Set([
    ISSUE_NOT_PROVISIONED,
    ISSUE_FIRMWARE_HASH_MISSING,
    ISSUE_FIRMWARE_HASH_MISMATCH,
    ISSUE_PRODUCT_MISMATCH,
    ISSUE_NO_FIRMWARE_VERSION,
    ISSUE_DETECT_FAILED,
    ISSUE_READ_TIMEOUT,
]);

function suggestionKeysFor(issue) {
    return [`tools.rnode_flasher.diagnostics.suggestions.${issue}`];
}

function withTimeout(promise, ms, code) {
    let timer = null;
    const timeoutPromise = new Promise((_, reject) => {
        timer = setTimeout(() => {
            const err = new Error(code || "timeout");
            err.code = code || "TIMEOUT";
            reject(err);
        }, ms);
    });
    return Promise.race([promise, timeoutPromise]).finally(() => {
        if (timer) {
            clearTimeout(timer);
        }
    });
}

function safeArrayEqual(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b)) {
        return false;
    }
    if (a.length !== b.length) {
        return false;
    }
    for (let i = 0; i < a.length; i++) {
        if ((a[i] & 0xff) !== (b[i] & 0xff)) {
            return false;
        }
    }
    return true;
}

/**
 * Run a diagnostics sweep against a connected RNode.
 *
 * @param {object} rnode RNode instance (already detected/open)
 * @param {{ expectedProductId?: number, expectedModelId?: number, timeoutMs?: number }} [options]
 * @returns {Promise<{
 *   firmwareVersion: string|null,
 *   platform: number|null,
 *   board: number|null,
 *   mcu: number|null,
 *   eepromBytes: number[]|null,
 *   romDetails: object|null,
 *   firmwareHash: number[]|null,
 *   targetFirmwareHash: number[]|null,
 *   isProvisioned: boolean,
 *   issues: string[],
 *   suggestionKeys: string[],
 *   summary: object,
 * }>}
 */
export async function diagnose(rnode, options = {}) {
    const timeoutMs = options.timeoutMs || 4000;
    const result = {
        firmwareVersion: null,
        platform: null,
        board: null,
        mcu: null,
        eepromBytes: null,
        romDetails: null,
        firmwareHash: null,
        targetFirmwareHash: null,
        isProvisioned: false,
        issues: [],
        suggestionKeys: [],
        summary: {},
    };

    const addIssue = (issue) => {
        if (!ALL_ISSUE_KEYS.has(issue)) {
            return;
        }
        if (!result.issues.includes(issue)) {
            result.issues.push(issue);
            for (const key of suggestionKeysFor(issue)) {
                if (!result.suggestionKeys.includes(key)) {
                    result.suggestionKeys.push(key);
                }
            }
        }
    };

    if (!rnode || typeof rnode.getFirmwareVersion !== "function") {
        addIssue(ISSUE_DETECT_FAILED);
        return result;
    }

    try {
        result.firmwareVersion = await withTimeout(rnode.getFirmwareVersion(), timeoutMs, "READ_TIMEOUT");
    } catch (err) {
        if (err?.code === "READ_TIMEOUT") {
            addIssue(ISSUE_READ_TIMEOUT);
        } else {
            addIssue(ISSUE_NO_FIRMWARE_VERSION);
        }
    }

    if (typeof rnode.getPlatform === "function") {
        try {
            result.platform = await withTimeout(rnode.getPlatform(), timeoutMs, "READ_TIMEOUT");
        } catch {
            // platform isn't critical for diagnostics
        }
    }
    if (typeof rnode.getBoard === "function") {
        try {
            result.board = await withTimeout(rnode.getBoard(), timeoutMs, "READ_TIMEOUT");
        } catch {
            // ignore
        }
    }
    if (typeof rnode.getMcu === "function") {
        try {
            result.mcu = await withTimeout(rnode.getMcu(), timeoutMs, "READ_TIMEOUT");
        } catch {
            // ignore
        }
    }

    let romDetails = null;
    if (typeof rnode.getRomAsObject === "function") {
        try {
            const rom = await withTimeout(rnode.getRomAsObject(), timeoutMs, "READ_TIMEOUT");
            result.eepromBytes = Array.isArray(rom?.eeprom) ? Array.from(rom.eeprom) : null;
            try {
                romDetails = typeof rom?.parse === "function" ? rom.parse() : null;
            } catch {
                romDetails = null;
            }
            result.romDetails = romDetails;
            result.isProvisioned = Boolean(romDetails?.is_provisioned);
        } catch {
            // ignore: handled by isProvisioned=false / not_provisioned issue below
        }
    }

    if (!result.isProvisioned) {
        addIssue(ISSUE_NOT_PROVISIONED);
    }

    if (
        result.isProvisioned &&
        options.expectedProductId !== undefined &&
        romDetails &&
        romDetails.product !== options.expectedProductId
    ) {
        addIssue(ISSUE_PRODUCT_MISMATCH);
    }

    if (typeof rnode.getFirmwareHash === "function") {
        try {
            result.firmwareHash = await withTimeout(rnode.getFirmwareHash(), timeoutMs, "READ_TIMEOUT");
        } catch {
            // ignore: hash retrieval can fail on un-provisioned units
        }
    }
    if (typeof rnode.getTargetFirmwareHash === "function") {
        try {
            result.targetFirmwareHash = await withTimeout(rnode.getTargetFirmwareHash(), timeoutMs, "READ_TIMEOUT");
        } catch {
            // ignore
        }
    }

    if (result.isProvisioned) {
        if (
            !Array.isArray(result.targetFirmwareHash) ||
            result.targetFirmwareHash.length === 0 ||
            result.targetFirmwareHash.every((b) => (b & 0xff) === 0)
        ) {
            addIssue(ISSUE_FIRMWARE_HASH_MISSING);
        } else if (
            Array.isArray(result.firmwareHash) &&
            result.firmwareHash.length > 0 &&
            !safeArrayEqual(result.firmwareHash, result.targetFirmwareHash)
        ) {
            addIssue(ISSUE_FIRMWARE_HASH_MISMATCH);
        }
    }

    result.summary = {
        firmware_version: result.firmwareVersion,
        platform: result.platform,
        board: result.board,
        mcu: result.mcu,
        is_provisioned: result.isProvisioned,
        product: romDetails?.product ?? null,
        model: romDetails?.model ?? null,
        hardware_revision: romDetails?.hardware_revision ?? null,
        serial_number: romDetails?.serial_number ?? null,
        firmware_hash: result.firmwareHash ? RNodeUtils.bytesToHex(result.firmwareHash) : null,
        target_firmware_hash: result.targetFirmwareHash ? RNodeUtils.bytesToHex(result.targetFirmwareHash) : null,
    };

    return result;
}

/**
 * Compare a model id from products.js against the EEPROM to see whether the
 * selected product/model in the UI matches the device the user just plugged
 * in. Useful as a guardrail before flashing.
 */
export function evaluateProductMatch(romDetails, expected) {
    if (!romDetails || !expected) {
        return { matches: false, reason: "missing_data" };
    }
    if (!romDetails.is_provisioned) {
        return { matches: false, reason: "not_provisioned" };
    }
    if (expected.productId !== undefined && romDetails.product !== expected.productId) {
        return { matches: false, reason: "product_mismatch" };
    }
    if (expected.modelId !== undefined && romDetails.model !== expected.modelId) {
        return { matches: false, reason: "model_mismatch" };
    }
    return { matches: true, reason: null };
}

export default { diagnose, evaluateProductMatch };
