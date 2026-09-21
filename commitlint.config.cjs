// SPDX-License-Identifier: 0BSD
module.exports = {
    extends: ["@commitlint/config-conventional"],
    rules: {
        // Warn, not error: long-lived branches carry pre-enforcement commits
        // whose headers cannot be shortened without rewriting history.
        "header-max-length": [1, "always", 120],
        "subject-case": [0],
        "subject-full-stop": [1, "never", "."],
        "body-max-line-length": [0],
        "type-enum": [
            2,
            "always",
            // merge, migrate, and localization are established types in this
            // repo's history alongside the conventional set.
            [
                "feat",
                "fix",
                "refactor",
                "chore",
                "docs",
                "test",
                "ci",
                "build",
                "perf",
                "style",
                "revert",
                "merge",
                "migrate",
                "localization",
            ],
        ],
    },
};
