// SPDX-License-Identifier: 0BSD

import { registerBlockedFeature } from "./blocked/index.js";

let featuresRegistered = false;

/**
 * Reset for tests.
 */
export function resetAllFeaturesForTests() {
    featuresRegistered = false;
}

/**
 * Register feature modules that opt into routeRegistry.
 * Call once at boot after registerCoreContributions.
 * Lives under features/ so kernel js/ stays free of feature imports.
 */
export function registerAllFeatures() {
    if (featuresRegistered) {
        return;
    }
    featuresRegistered = true;
    registerBlockedFeature();
}
