import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "../../..");

export const appPackageVersion = JSON.parse(readFileSync(join(repoRoot, "package.json"), "utf8")).version;
