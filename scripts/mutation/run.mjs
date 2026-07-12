#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { DEFAULT_FRONTEND_TARGETS } from "./config.mjs";
import { generateMutants } from "./mutators.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

/**
 * @typedef {"killed" | "survived" | "error" | "skipped"} MutantStatus
 */

/**
 * @typedef {{ id: string, source: string, operator: string, line: number, column: number, status: MutantStatus, detail?: string }} MutantResult
 */

function parseArgs(argv) {
    const options = {
        targets: [...DEFAULT_FRONTEND_TARGETS],
        minScore: null,
        maxMutantsPerFile: null,
        reportPath: "reports/mutation/meshmut-report.json",
        dryRun: false,
        explicitSources: false,
    };

    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === "--min-score") {
            options.minScore = Number(argv[++i]);
        } else if (arg === "--max-per-file") {
            options.maxMutantsPerFile = Number(argv[++i]);
        } else if (arg === "--report") {
            options.reportPath = argv[++i];
        } else if (arg === "--source") {
            const source = argv[++i];
            const existing = DEFAULT_FRONTEND_TARGETS.find((target) => target.source === source);
            if (!existing) {
                throw new Error(`Unknown mutation source: ${source}`);
            }
            if (!options.explicitSources) {
                options.targets = [];
                options.explicitSources = true;
            }
            options.targets.push(existing);
        } else if (arg === "--dry-run") {
            options.dryRun = true;
        } else if (arg === "--help" || arg === "-h") {
            printHelp();
            process.exit(0);
        } else {
            throw new Error(`Unknown argument: ${arg}`);
        }
    }

    return options;
}

function printHelp() {
    process.stdout.write(`MeshMut - in-repo JavaScript mutation testing

Usage:
  node scripts/mutation/run.mjs [options]

Options:
  --source <path>       Mutate a single configured source file
  --min-score <pct>     Fail when mutation score is below threshold
  --max-per-file <n>    Cap mutants generated per source file
  --report <path>       JSON report output path (default: reports/mutation/meshmut-report.json)
  --dry-run             List mutants without executing tests
  --help                Show this help
`);
}

/**
 * @param {string[]} testFiles
 */
function runVitest(testFiles) {
    const args = ["exec", "vitest", "run", ...testFiles];
    const result = spawnSync("pnpm", args, {
        cwd: ROOT,
        encoding: "utf-8",
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
    });
    return {
        exitCode: result.status ?? 1,
        stdout: result.stdout ?? "",
        stderr: result.stderr ?? "",
    };
}

/**
 * @param {import("./config.mjs").MutationTarget} target
 * @param {ReturnType<typeof parseArgs>} options
 * @returns {MutantResult[]}
 */
function mutateTarget(target, options) {
    const sourcePath = path.join(ROOT, target.source);
    const original = fs.readFileSync(sourcePath, "utf-8");
    let mutants = generateMutants(original, target.source);

    if (options.maxMutantsPerFile != null) {
        mutants = mutants.slice(0, options.maxMutantsPerFile);
    }

    if (options.dryRun) {
        return mutants.map((mutant) => ({
            id: mutant.id,
            source: target.source,
            operator: mutant.operator,
            line: mutant.line,
            column: mutant.column,
            status: "skipped",
            detail: `dry-run: ${mutant.original} -> ${mutant.mutated}`,
        }));
    }

    /** @type {MutantResult[]} */
    const results = [];

    for (const mutant of mutants) {
        fs.writeFileSync(sourcePath, mutant.content, "utf-8");
        const run = runVitest(target.tests);
        fs.writeFileSync(sourcePath, original, "utf-8");

        if (run.exitCode !== 0) {
            results.push({
                id: mutant.id,
                source: target.source,
                operator: mutant.operator,
                line: mutant.line,
                column: mutant.column,
                status: "killed",
            });
            continue;
        }

        results.push({
            id: mutant.id,
            source: target.source,
            operator: mutant.operator,
            line: mutant.line,
            column: mutant.column,
            status: "survived",
            detail: `${mutant.original} -> ${mutant.mutated}`,
        });
    }

    return results;
}

/**
 * @param {MutantResult[]} results
 */
function summarize(results) {
    const killed = results.filter((result) => result.status === "killed").length;
    const survived = results.filter((result) => result.status === "survived").length;
    const errors = results.filter((result) => result.status === "error").length;
    const skipped = results.filter((result) => result.status === "skipped").length;
    const scored = killed + survived;
    const score = scored > 0 ? (killed / scored) * 100 : 0;

    return { killed, survived, errors, skipped, scored, score };
}

function writeReport(reportPath, results, summary) {
    const absolute = path.isAbsolute(reportPath) ? reportPath : path.join(ROOT, reportPath);
    fs.mkdirSync(path.dirname(absolute), { recursive: true });
    fs.writeFileSync(
        absolute,
        JSON.stringify(
            {
                tool: "meshmut",
                generatedAt: new Date().toISOString(),
                summary,
                results,
            },
            null,
            2
        ),
        "utf-8"
    );
    return absolute;
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    /** @type {MutantResult[]} */
    const allResults = [];

    for (const target of options.targets) {
        process.stdout.write(`\nMutating ${target.source} (${target.tests.length} test file(s))\n`);
        const results = mutateTarget(target, options);
        allResults.push(...results);

        const fileSummary = summarize(results);
        process.stdout.write(
            `  killed=${fileSummary.killed} survived=${fileSummary.survived} score=${fileSummary.score.toFixed(1)}%\n`
        );
    }

    const summary = summarize(allResults);
    const reportFile = writeReport(options.reportPath, allResults, summary);

    process.stdout.write("\nMutation summary\n");
    process.stdout.write(`  killed:   ${summary.killed}\n`);
    process.stdout.write(`  survived: ${summary.survived}\n`);
    process.stdout.write(`  score:    ${summary.score.toFixed(1)}%\n`);
    process.stdout.write(`  report:   ${reportFile}\n`);

    if (summary.survived > 0) {
        process.stdout.write("\nSurviving mutants:\n");
        for (const result of allResults.filter((entry) => entry.status === "survived").slice(0, 20)) {
            process.stdout.write(
                `  ${result.source}:${result.line}:${result.column} [${result.operator}] ${result.detail ?? ""}\n`
            );
        }
        if (summary.survived > 20) {
            process.stdout.write(`  ... and ${summary.survived - 20} more (see report)\n`);
        }
    }

    if (options.minScore != null && summary.score < options.minScore) {
        process.stderr.write(`\nMutation score ${summary.score.toFixed(1)}% is below minimum ${options.minScore}%.\n`);
        process.exit(1);
    }

    if (summary.scored === 0) {
        process.stderr.write("\nNo mutants were scored.\n");
        process.exit(1);
    }
}

main();
