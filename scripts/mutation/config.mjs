/**
 * Default frontend mutation targets and their Vitest files.
 */

/** @typedef {{ source: string, tests: string[] }} MutationTarget */

const LIBS_TESTS = ["tests/frontend/libs.core.test.js", "tests/frontend/libs.oracle.test.js"];

/** @type {MutationTarget[]} */
export const DEFAULT_FRONTEND_TARGETS = [
    {
        source: "meshchatx/src/frontend/js/rnode/Capabilities.js",
        tests: ["tests/frontend/RNodeCapabilities.test.js"],
    },
    {
        source: "meshchatx/src/frontend/js/mapLinkUtils.js",
        tests: ["tests/frontend/mapLinkUtils.test.js", "tests/frontend/mapLinkUtils.security.test.js"],
    },
    {
        source: "meshchatx/src/frontend/js/clipboardUtils.js",
        tests: ["tests/frontend/clipboardUtils.test.js"],
    },
    {
        source: "meshchatx/src/frontend/js/LinkUtils.js",
        tests: ["tests/frontend/LinkUtils.test.js"],
    },
    {
        source: "meshchatx/src/frontend/js/reticulumPathfinding.js",
        tests: ["tests/frontend/reticulumPathfinding.test.js"],
    },
    {
        source: "meshchatx/src/frontend/libs/emitter.js",
        tests: LIBS_TESTS,
    },
    {
        source: "meshchatx/src/frontend/libs/uuid.js",
        tests: LIBS_TESTS,
    },
    {
        source: "meshchatx/src/frontend/libs/datetime.js",
        tests: LIBS_TESTS,
    },
    {
        source: "meshchatx/src/frontend/libs/clickOutside.js",
        tests: LIBS_TESTS,
    },
];

/**
 * @param {string} sourcePath
 * @returns {MutationTarget | undefined}
 */
export function findTarget(sourcePath, targets = DEFAULT_FRONTEND_TARGETS) {
    const normalized = sourcePath.replace(/\\/g, "/");
    return targets.find((target) => target.source === normalized);
}
