// SPDX-License-Identifier: 0BSD
module.exports = {
    extends: ["@commitlint/config-conventional"],
    rules: {
        "header-max-length": [2, "always", 120],
        "subject-case": [0],
        "body-max-line-length": [0],
        "type-enum": [
            2,
            "always",
            ["feat", "fix", "refactor", "chore", "docs", "test", "ci", "build", "perf", "style", "revert"],
        ],
    },
};
