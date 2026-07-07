/**
 * Regex-based mutation operators for JavaScript source files.
 * Each operator replaces a single match occurrence per mutant.
 */

/** @typedef {{ name: string, pattern: RegExp, replace: string | ((match: string) => string) }} MutationOperator */

/** @type {MutationOperator[]} */
export const MUTATION_OPERATORS = [
    { name: "strict_eq_flip", pattern: /===/g, replace: "!==" },
    { name: "strict_ne_flip", pattern: /!==/g, replace: "===" },
    { name: "loose_eq_flip", pattern: /(?<![=!])==(?!=)/g, replace: "!=" },
    { name: "loose_ne_flip", pattern: /(?<![=!])!=(?!=)/g, replace: "==" },
    { name: "logical_and_or", pattern: /&&/g, replace: "||" },
    { name: "logical_or_and", pattern: /\|\|/g, replace: "&&" },
    { name: "gt_gte", pattern: /(?<![=<>!])>(?!=)/g, replace: ">=" },
    { name: "lt_lte", pattern: /(?<![=<>!])<(?!=)/g, replace: "<=" },
    { name: "gte_gt", pattern: />=/g, replace: ">" },
    { name: "lte_lt", pattern: /<=/g, replace: "<" },
    { name: "true_false", pattern: /\btrue\b/g, replace: "false" },
    { name: "false_true", pattern: /\bfalse\b/g, replace: "true" },
    { name: "null_undefined", pattern: /\bnull\b/g, replace: "undefined" },
    { name: "return_empty_array", pattern: /\breturn\s+\[\]/g, replace: "return [1]" },
    { name: "return_empty_object", pattern: /\breturn\s+\{\}/g, replace: "return { mutated: true }" },
    { name: "plus_minus", pattern: /(?<=[\d)\]])\+(?=\d)/g, replace: "-" },
    { name: "minus_plus", pattern: /(?<=[\d)\]])-(?=\d)/g, replace: "+" },
];

/**
 * @param {string} source
 * @param {string} filePath
 * @returns {Array<{ id: string, operator: string, line: number, column: number, original: string, mutated: string, content: string }>}
 */
export function generateMutants(source, filePath) {
    /** @type {ReturnType<typeof generateMutants>} */
    const mutants = [];

    for (const operator of MUTATION_OPERATORS) {
        const pattern = operator.pattern;
        pattern.lastIndex = 0;
        let match;
        while ((match = pattern.exec(source)) !== null) {
            if (isInsideCommentOrString(source, match.index)) {
                continue;
            }

            const replacement = typeof operator.replace === "function" ? operator.replace(match[0]) : operator.replace;
            const content = source.slice(0, match.index) + replacement + source.slice(match.index + match[0].length);
            if (content === source) {
                continue;
            }

            const { line, column } = offsetToLineColumn(source, match.index);
            mutants.push({
                id: `${filePath}::${operator.name}::${match.index}`,
                operator: operator.name,
                line,
                column,
                original: match[0],
                mutated: replacement,
                content,
            });
        }
        pattern.lastIndex = 0;
    }

    return mutants;
}

/**
 * @param {string} source
 * @param {number} offset
 */
function isInsideCommentOrString(source, offset) {
    let inSingle = false;
    let inDouble = false;
    let inTemplate = false;
    let inLineComment = false;
    let inBlockComment = false;

    for (let i = 0; i < offset; i += 1) {
        const ch = source[i];
        const next = source[i + 1];

        if (inLineComment) {
            if (ch === "\n") {
                inLineComment = false;
            }
            continue;
        }
        if (inBlockComment) {
            if (ch === "*" && next === "/") {
                inBlockComment = false;
                i += 1;
            }
            continue;
        }
        if (inSingle) {
            if (ch === "\\") {
                i += 1;
                continue;
            }
            if (ch === "'") {
                inSingle = false;
            }
            continue;
        }
        if (inDouble) {
            if (ch === "\\") {
                i += 1;
                continue;
            }
            if (ch === '"') {
                inDouble = false;
            }
            continue;
        }
        if (inTemplate) {
            if (ch === "\\") {
                i += 1;
                continue;
            }
            if (ch === "`") {
                inTemplate = false;
            }
            continue;
        }

        if (ch === "/" && next === "/") {
            inLineComment = true;
            i += 1;
            continue;
        }
        if (ch === "/" && next === "*") {
            inBlockComment = true;
            i += 1;
            continue;
        }
        if (ch === "'") {
            inSingle = true;
            continue;
        }
        if (ch === '"') {
            inDouble = true;
            continue;
        }
        if (ch === "`") {
            inTemplate = true;
        }
    }

    return inSingle || inDouble || inTemplate || inLineComment || inBlockComment;
}

/**
 * @param {string} source
 * @param {number} offset
 */
function offsetToLineColumn(source, offset) {
    let line = 1;
    let column = 1;
    for (let i = 0; i < offset; i += 1) {
        if (source[i] === "\n") {
            line += 1;
            column = 1;
        } else {
            column += 1;
        }
    }
    return { line, column };
}
