// SPDX-License-Identifier: 0BSD
//
// license_scope_mapper analyzes file similarity against an upstream repository
// and emits per-file SPDX license recommendations with optional header updates.
//
// Quick start:
//
//	go run scripts/license_scope_mapper.go \
//	  --repo-root "/run/media/user1/projects/reticulum-meshchatX" \
//	  --overrides "scripts/license_scope_overrides.json" \
//	  --write-headers --replace-existing
//
// Environment variables are supported with the LICENSE_SCOPE_ prefix
// (for example LICENSE_SCOPE_SCAN_EXTS and LICENSE_SCOPE_HEADER_EXTS).
//
// Important caveats (read before relying on output):
//
//  1. Textual similarity is not a legal test for derivative-work status. A file
//     forked from upstream and heavily refactored or renamed is still a
//     derivative work and still carries upstream license obligations. The
//     pure-0BSD branch is therefore opt-in (--allow-pure-0bsd) and gated
//     behind --pure-0bsd-confirm-no-derivation to avoid accidental
//     relicensing of upstream-derived material.
//
//  2. --clean-non-target-spdx and --replace-existing rewrite or delete
//     SPDX markers in tracked files. Run with --report-json first and
//     review the diff before enabling either flag; third-party SPDX lines
//     in vendored or generated files must not be silently stripped.
//
//  3. The default base license is "0BSD AND MIT", which means BOTH licenses
//     apply simultaneously to their respective contributions. This is the
//     safe default for files where provenance cannot be cleanly separated.
package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"hash/fnv"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	envPrefix          = "LICENSE_SCOPE_"
	defaultUpstreamURL = "https://github.com/liamcottle/reticulum-meshchat"
)

var spdxPattern = regexp.MustCompile(`SPDX-License-Identifier:\s*([A-Za-z0-9.\-+ ()]+)`)

type config struct {
	repoRoot                    string
	upstreamPath                string
	upstreamURL                 string
	upstreamBranch              string
	cloneTimeout                time.Duration
	scanExtsRaw                 string
	headerExtsRaw               string
	excludeDirsRaw              string
	excludePathsRaw             string
	maxFileSizeBytes            int64
	mitThreshold                float64
	mixedThreshold              float64
	allowPure0BSD               bool
	pure0BSDConfirmNoDerivation bool
	pure0BSDThreshold           float64
	baseLicense                 string
	maxNameCandidates           int
	writeHeaders                bool
	replaceExisting             bool
	cleanNonTarget              bool
	overridesPath               string
	reportJSON                  string
	explainPathsRaw             string
	explainAll                  bool

	scanExts         map[string]struct{}
	headerExts       map[string]struct{}
	excludedDirs     map[string]struct{}
	excludedContains []string
	explainPaths     map[string]struct{}
}

type fileData struct {
	absPath     string
	relPath     string
	baseName    string
	normHash    string
	lineSet     map[string]struct{}
	bigramSet   map[uint64]struct{}
	shingle5Set map[uint64]struct{}
	shingle7Set map[uint64]struct{}
}

type matchResult struct {
	upstreamRelPath string
	directPathMatch bool
	similarityPct   float64
	lineJaccardPct  float64
	bigramDicePct   float64
	shingle5Pct     float64
	shingle7Pct     float64
	lineCommon      int
	lineUnion       int
	bigramCommon    int
	bigramTotal     int
	shingle5Common  int
	shingle5Union   int
	shingle7Common  int
	shingle7Union   int
}

type reportItem struct {
	Path            string  `json:"path"`
	License         string  `json:"license"`
	SimilarityPct   float64 `json:"similarity_pct"`
	LineJaccardPct  float64 `json:"line_jaccard_pct"`
	BigramDicePct   float64 `json:"bigram_dice_pct"`
	Shingle5Pct     float64 `json:"shingle5_jaccard_pct"`
	Shingle7Pct     float64 `json:"shingle7_jaccard_pct"`
	OriginalPct     float64 `json:"original_pct"`
	MinePct         float64 `json:"mine_pct"`
	UpstreamMatch   string  `json:"upstream_match"`
	DirectPathMatch bool    `json:"direct_path_match"`
	HeaderChanged   bool    `json:"header_changed"`
	ExistingSPDX    string  `json:"existing_spdx,omitempty"`
}

type reportConfig struct {
	RepoRoot                    string  `json:"repo_root"`
	UpstreamURL                 string  `json:"upstream_url"`
	UpstreamBranch              string  `json:"upstream_branch"`
	ScanExtensions              string  `json:"scan_extensions"`
	HeaderExtensions            string  `json:"header_extensions"`
	MitThreshold                float64 `json:"mit_threshold"`
	MixedThreshold              float64 `json:"mixed_threshold"`
	AllowPure0BSD               bool    `json:"allow_pure_0bsd"`
	Pure0BSDConfirmNoDerivation bool    `json:"pure_0bsd_confirm_no_derivation"`
	Pure0BSDThreshold           float64 `json:"pure_0bsd_threshold_pct"`
	BaseLicense                 string  `json:"base_license"`
	MaxNameCandidates           int     `json:"max_name_candidates"`
	WriteHeaders                bool    `json:"write_headers"`
	ReplaceExisting             bool    `json:"replace_existing"`
	CleanNonTarget              bool    `json:"clean_non_target_spdx"`
	OverridesPath               string  `json:"overrides_path,omitempty"`
}

type reportSummary struct {
	FilesAnalyzed        int            `json:"files_analyzed"`
	HeadersUpdated       int            `json:"headers_updated"`
	RemovedNonTargetSPDX int            `json:"removed_non_target_spdx"`
	LicenseCounts        map[string]int `json:"license_counts"`
}

type reportDocument struct {
	GeneratedAt string        `json:"generated_at"`
	Config      reportConfig  `json:"config"`
	Summary     reportSummary `json:"summary"`
	Results     []reportItem  `json:"results"`
}

var commentStyleByExt = map[string]string{
	".py":    "hash",
	".sh":    "hash",
	".bash":  "hash",
	".zsh":   "hash",
	".yml":   "hash",
	".yaml":  "hash",
	".toml":  "hash",
	".ini":   "hash",
	".cfg":   "hash",
	".conf":  "hash",
	".mk":    "hash",
	".js":    "line",
	".ts":    "line",
	".jsx":   "line",
	".tsx":   "line",
	".c":     "line",
	".h":     "line",
	".cpp":   "line",
	".hpp":   "line",
	".java":  "line",
	".go":    "line",
	".rs":    "line",
	".swift": "line",
	".kt":    "line",
	".css":   "block",
	".scss":  "block",
	".less":  "block",
	".html":  "html",
	".xml":   "html",
	".vue":   "html",
	".md":    "html",
}

func main() {
	cfg, err := parseConfig()
	if err != nil {
		exitErr(err)
	}

	emitSafetyNotices(cfg)

	if cfg.cleanNonTarget {
		removed, err := removeSPDXFromNonTargetFiles(cfg)
		if err != nil {
			exitErr(err)
		}
		fmt.Printf("Removed SPDX headers from non-target files: %d\n", removed)
	}

	upstreamRoot := cfg.upstreamPath
	cleanup := func() {}
	if strings.TrimSpace(upstreamRoot) == "" {
		tmpDir, err := os.MkdirTemp("", "license-scope-upstream-*")
		if err != nil {
			exitErr(err)
		}
		cleanup = func() { _ = os.RemoveAll(tmpDir) }
		upstreamRoot = filepath.Join(tmpDir, "upstream")
		if err := cloneUpstream(cfg, upstreamRoot); err != nil {
			cleanup()
			exitErr(err)
		}
	}
	defer cleanup()

	repoRootAbs, _ := filepath.Abs(cfg.repoRoot)
	upstreamAbs, _ := filepath.Abs(upstreamRoot)

	localFiles, err := discoverFiles(cfg, repoRootAbs)
	if err != nil {
		exitErr(err)
	}
	overrides, err := loadOverrides(cfg.overridesPath)
	if err != nil {
		exitErr(err)
	}
	upstreamFiles, err := discoverFiles(cfg, upstreamAbs)
	if err != nil {
		exitErr(err)
	}

	upstreamByRel := make(map[string]fileData, len(upstreamFiles))
	upstreamByBase := make(map[string][]fileData, len(upstreamFiles))
	for _, f := range upstreamFiles {
		upstreamByRel[f.relPath] = f
		upstreamByBase[f.baseName] = append(upstreamByBase[f.baseName], f)
	}

	results := make([]reportItem, 0, len(localFiles))
	classCounts := map[string]int{}
	headersUpdated := 0
	removedNonTarget := 0
	if cfg.cleanNonTarget {
		// We report cleanup count from function call side-effect by rescanning isn't needed.
		// Keep zero here and rely on printed output.
	}

	for _, local := range localFiles {
		match := findBestMatch(local, upstreamByRel, upstreamByBase, cfg.maxNameCandidates)
		license, decisionReason := classify(match, cfg)
		if forced, ok := overrides[local.relPath]; ok {
			license = forced
			decisionReason = "override file matched path"
		}
		classCounts[license]++

		item := reportItem{
			Path:            local.relPath,
			License:         license,
			SimilarityPct:   round2(match.similarityPct),
			LineJaccardPct:  round2(match.lineJaccardPct),
			BigramDicePct:   round2(match.bigramDicePct),
			Shingle5Pct:     round2(match.shingle5Pct),
			Shingle7Pct:     round2(match.shingle7Pct),
			OriginalPct:     round2(match.similarityPct),
			MinePct:         round2(100.0 - match.similarityPct),
			UpstreamMatch:   match.upstreamRelPath,
			DirectPathMatch: match.directPathMatch,
		}

		if cfg.writeHeaders && isHeaderExt(local.relPath, cfg.headerExts) {
			changed, existing, err := upsertSPDX(local.absPath, license, cfg.replaceExisting)
			if err != nil {
				fmt.Fprintf(os.Stderr, "SPDX update failed for %s: %v\n", local.relPath, err)
			} else {
				item.HeaderChanged = changed
				item.ExistingSPDX = existing
				if changed {
					headersUpdated++
				}
			}
		}

		if shouldExplainPath(local.relPath, cfg.explainAll, cfg.explainPaths) {
			printExplanation(local.relPath, match, license, decisionReason, cfg)
		}

		results = append(results, item)
	}

	sort.Slice(results, func(i, j int) bool { return results[i].Path < results[j].Path })

	doc := reportDocument{
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		Config: reportConfig{
			RepoRoot:                    repoRootAbs,
			UpstreamURL:                 cfg.upstreamURL,
			UpstreamBranch:              cfg.upstreamBranch,
			ScanExtensions:              cfg.scanExtsRaw,
			HeaderExtensions:            cfg.headerExtsRaw,
			MitThreshold:                cfg.mitThreshold,
			MixedThreshold:              cfg.mixedThreshold,
			AllowPure0BSD:               cfg.allowPure0BSD,
			Pure0BSDConfirmNoDerivation: cfg.pure0BSDConfirmNoDerivation,
			Pure0BSDThreshold:           cfg.pure0BSDThreshold,
			BaseLicense:                 cfg.baseLicense,
			MaxNameCandidates:           cfg.maxNameCandidates,
			WriteHeaders:                cfg.writeHeaders,
			ReplaceExisting:             cfg.replaceExisting,
			CleanNonTarget:              cfg.cleanNonTarget,
			OverridesPath:               cfg.overridesPath,
		},
		Summary: reportSummary{
			FilesAnalyzed:        len(results),
			HeadersUpdated:       headersUpdated,
			RemovedNonTargetSPDX: removedNonTarget,
			LicenseCounts:        classCounts,
		},
		Results: results,
	}

	reportPath := filepath.Join(repoRootAbs, cfg.reportJSON)
	reportBytes, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		exitErr(err)
	}
	if err := os.WriteFile(reportPath, append(reportBytes, '\n'), 0o644); err != nil {
		exitErr(err)
	}

	fmt.Printf("Analyzed files: %d\n", len(results))
	fmt.Printf("License counts -> %s\n", formatCountSummary(classCounts, float64(len(results))))
	fmt.Printf("JSON report: %s\n", reportPath)
	if cfg.writeHeaders {
		fmt.Printf("Headers updated (%s): %d\n", cfg.headerExtsRaw, headersUpdated)
	}
}

func parseConfig() (config, error) {
	cfg := config{}
	flag.StringVar(&cfg.repoRoot, "repo-root", envString("REPO_ROOT", "."), "Path to repository root")
	flag.StringVar(&cfg.upstreamPath, "upstream-path", envString("UPSTREAM_PATH", ""), "Path to local upstream checkout")
	flag.StringVar(&cfg.upstreamURL, "upstream-url", envString("UPSTREAM_URL", defaultUpstreamURL), "Upstream git URL")
	flag.StringVar(&cfg.upstreamBranch, "upstream-branch", envString("UPSTREAM_BRANCH", "master"), "Upstream branch")
	flag.DurationVar(&cfg.cloneTimeout, "clone-timeout", envDuration("CLONE_TIMEOUT", 2*time.Minute), "Timeout for upstream clone")
	flag.StringVar(&cfg.scanExtsRaw, "scan-exts", envString("SCAN_EXTS", ".py,.vue"), "Comma-separated extensions for similarity analysis")
	flag.StringVar(&cfg.headerExtsRaw, "header-exts", envString("HEADER_EXTS", ".py,.vue"), "Comma-separated extensions eligible for SPDX headers")
	flag.StringVar(&cfg.excludeDirsRaw, "exclude-dirs", envString("EXCLUDE_DIRS", ".git,.idea,.vscode,.local,.pnpm-store,.flatpak-builder,node_modules,dist,build,.venv,venv,__pycache__,.pytest_cache,.mypy_cache,.ruff_cache"), "Comma-separated directories to skip")
	flag.StringVar(&cfg.excludePathsRaw, "exclude-path-contains", envString("EXCLUDE_PATH_CONTAINS", ""), "Comma-separated path substrings to skip")
	flag.Int64Var(&cfg.maxFileSizeBytes, "max-file-size-bytes", envInt64("MAX_FILE_SIZE_BYTES", 2_000_000), "Max file size for analysis")
	flag.Float64Var(&cfg.mitThreshold, "mit-threshold", envFloat("MIT_THRESHOLD", 0.85), "Composite similarity threshold for MIT")
	flag.Float64Var(&cfg.mixedThreshold, "mixed-threshold", envFloat("MIXED_THRESHOLD", 0.25), "Composite similarity threshold for mixed license")
	flag.BoolVar(&cfg.allowPure0BSD, "allow-pure-0bsd", envBool("ALLOW_PURE_0BSD", false), "Allow pure 0BSD classification for files with very low similarity and no direct path match. Disabled by default because textual similarity is not a legal test for derivative-work status.")
	flag.BoolVar(&cfg.pure0BSDConfirmNoDerivation, "pure-0bsd-confirm-no-derivation", envBool("PURE_0BSD_CONFIRM_NO_DERIVATION", false), "Required acknowledgement that files classified as pure 0BSD are not derivative works of upstream sources. Without this flag --allow-pure-0bsd is ignored.")
	flag.Float64Var(&cfg.pure0BSDThreshold, "pure-0bsd-threshold", envFloat("PURE_0BSD_THRESHOLD", 1.0), "Max similarity percent for pure 0BSD")
	flag.StringVar(&cfg.baseLicense, "base-license", envString("BASE_LICENSE", "0BSD AND MIT"), "Default SPDX license below mixed threshold")
	flag.IntVar(&cfg.maxNameCandidates, "max-name-candidates", envInt("MAX_NAME_CANDIDATES", 200), "Max basename candidates when direct path match missing")
	flag.BoolVar(&cfg.writeHeaders, "write-headers", envBool("WRITE_HEADERS", false), "Write SPDX headers")
	flag.BoolVar(&cfg.replaceExisting, "replace-existing", envBool("REPLACE_EXISTING", false), "Replace existing SPDX header")
	flag.BoolVar(&cfg.cleanNonTarget, "clean-non-target-spdx", envBool("CLEAN_NON_TARGET_SPDX", false), "Remove SPDX headers from files outside header-exts")
	flag.StringVar(&cfg.overridesPath, "overrides", envString("OVERRIDES", ""), "Path to JSON map of relpath->SPDX")
	flag.StringVar(&cfg.reportJSON, "report-json", envString("REPORT_JSON", "license-scope-report.json"), "JSON report output path")
	flag.StringVar(&cfg.explainPathsRaw, "explain-paths", envString("EXPLAIN_PATHS", ""), "Comma-separated repo-relative paths to explain scoring decisions")
	flag.BoolVar(&cfg.explainAll, "explain-all", envBool("EXPLAIN_ALL", false), "Print scoring explanation for every analyzed file")
	flag.Parse()

	cfg.scanExts = parseExtSet(cfg.scanExtsRaw)
	cfg.headerExts = parseExtSet(cfg.headerExtsRaw)
	cfg.excludedDirs = parseStringSet(cfg.excludeDirsRaw)
	cfg.excludedContains = parseStringList(cfg.excludePathsRaw)
	cfg.explainPaths = parsePathSet(cfg.explainPathsRaw)

	if len(cfg.scanExts) == 0 {
		return cfg, errors.New("scan-exts must include at least one extension")
	}
	if len(cfg.headerExts) == 0 {
		return cfg, errors.New("header-exts must include at least one extension")
	}
	if cfg.mixedThreshold < 0 || cfg.mitThreshold < 0 || cfg.mitThreshold > 1 || cfg.mixedThreshold > cfg.mitThreshold {
		return cfg, errors.New("thresholds must satisfy 0 <= mixed-threshold <= mit-threshold <= 1")
	}
	if cfg.pure0BSDThreshold < 0 || cfg.pure0BSDThreshold > 100 {
		return cfg, errors.New("pure-0bsd-threshold must be in [0,100] percent")
	}
	return cfg, nil
}

func envKey(name string) string { return envPrefix + name }

func envString(name, fallback string) string {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		return v
	}
	return fallback
}

func envBool(name string, fallback bool) bool {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		b, err := strconv.ParseBool(strings.TrimSpace(v))
		if err == nil {
			return b
		}
	}
	return fallback
}

func envInt(name string, fallback int) int {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		i, err := strconv.Atoi(strings.TrimSpace(v))
		if err == nil {
			return i
		}
	}
	return fallback
}

func envInt64(name string, fallback int64) int64 {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		i, err := strconv.ParseInt(strings.TrimSpace(v), 10, 64)
		if err == nil {
			return i
		}
	}
	return fallback
}

func envFloat(name string, fallback float64) float64 {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		f, err := strconv.ParseFloat(strings.TrimSpace(v), 64)
		if err == nil {
			return f
		}
	}
	return fallback
}

func envDuration(name string, fallback time.Duration) time.Duration {
	if v, ok := os.LookupEnv(envKey(name)); ok {
		d, err := time.ParseDuration(strings.TrimSpace(v))
		if err == nil {
			return d
		}
	}
	return fallback
}

func parseStringList(raw string) []string {
	out := []string{}
	for _, token := range strings.Split(raw, ",") {
		t := strings.TrimSpace(token)
		if t != "" {
			out = append(out, t)
		}
	}
	return out
}

func parseStringSet(raw string) map[string]struct{} {
	out := map[string]struct{}{}
	for _, t := range parseStringList(raw) {
		out[t] = struct{}{}
	}
	return out
}

func parsePathSet(raw string) map[string]struct{} {
	out := map[string]struct{}{}
	for _, p := range parseStringList(raw) {
		out[filepath.ToSlash(strings.TrimSpace(p))] = struct{}{}
	}
	return out
}

func parseExtSet(raw string) map[string]struct{} {
	out := map[string]struct{}{}
	for _, token := range parseStringList(raw) {
		ext := strings.ToLower(token)
		if !strings.HasPrefix(ext, ".") {
			ext = "." + ext
		}
		out[ext] = struct{}{}
	}
	return out
}

func cloneUpstream(cfg config, target string) error {
	ctx, cancel := context.WithTimeout(context.Background(), cfg.cloneTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "clone", "--depth", "1", "--branch", cfg.upstreamBranch, cfg.upstreamURL, target)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return fmt.Errorf("git clone timed out after %s", cfg.cloneTimeout)
		}
		return err
	}
	return nil
}

func discoverFiles(cfg config, root string) ([]fileData, error) {
	out := []fileData{}
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		name := d.Name()
		if d.IsDir() {
			if _, skip := cfg.excludedDirs[name]; skip {
				return filepath.SkipDir
			}
			return nil
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if shouldSkipFile(cfg, rel, path) {
			return nil
		}
		normHash, lineSet, bigrams, s5, s7, err := loadAndNormalize(path)
		if err != nil {
			return nil
		}
		out = append(out, fileData{
			absPath:     path,
			relPath:     rel,
			baseName:    filepath.Base(path),
			normHash:    normHash,
			lineSet:     lineSet,
			bigramSet:   bigrams,
			shingle5Set: s5,
			shingle7Set: s7,
		})
		return nil
	})
	return out, err
}

func shouldSkipFile(cfg config, rel, abs string) bool {
	for _, part := range cfg.excludedContains {
		if strings.Contains(rel, part) {
			return true
		}
	}
	ext := strings.ToLower(filepath.Ext(abs))
	if _, ok := cfg.scanExts[ext]; !ok {
		return true
	}
	if _, ok := commentStyleByExt[ext]; !ok {
		return true
	}
	info, err := os.Stat(abs)
	if err != nil {
		return true
	}
	if info.Size() > cfg.maxFileSizeBytes {
		return true
	}
	return false
}

func loadAndNormalize(path string) (string, map[string]struct{}, map[uint64]struct{}, map[uint64]struct{}, map[uint64]struct{}, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", nil, nil, nil, nil, err
	}
	if bytes.IndexByte(raw, 0) >= 0 {
		return "", nil, nil, nil, nil, errors.New("binary file")
	}
	sc := bufio.NewScanner(bytes.NewReader(raw))
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)

	lines := []string{}
	lineSet := map[string]struct{}{}
	for sc.Scan() {
		line := sc.Text()
		if strings.Contains(line, "SPDX-License-Identifier:") {
			continue
		}
		norm := strings.ToLower(strings.TrimSpace(line))
		if norm == "" {
			continue
		}
		lines = append(lines, norm)
		lineSet[norm] = struct{}{}
	}
	if err := sc.Err(); err != nil {
		return "", nil, nil, nil, nil, err
	}
	sum := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return hex.EncodeToString(sum[:]), lineSet, makeNGramSet(lines, 2), makeNGramSet(lines, 5), makeNGramSet(lines, 7), nil
}

func findBestMatch(local fileData, byRel map[string]fileData, byBase map[string][]fileData, maxCandidates int) matchResult {
	best := matchResult{}
	if direct, ok := byRel[local.relPath]; ok {
		best = similarityDetail(local, direct)
		best.upstreamRelPath = direct.relPath
		best.directPathMatch = true
	}

	candidates := byBase[local.baseName]
	if len(candidates) > maxCandidates {
		candidates = candidates[:maxCandidates]
	}
	for _, cand := range candidates {
		if cand.relPath == best.upstreamRelPath {
			continue
		}
		d := similarityDetail(local, cand)
		if d.similarityPct > best.similarityPct {
			d.upstreamRelPath = cand.relPath
			d.directPathMatch = cand.relPath == local.relPath
			best = d
		}
	}
	if best.upstreamRelPath == local.relPath && best.upstreamRelPath != "" {
		best.directPathMatch = true
	}
	return best
}

func similarityDetail(a, b fileData) matchResult {
	if a.normHash != "" && a.normHash == b.normHash {
		return matchResult{
			similarityPct:  100,
			lineJaccardPct: 100,
			bigramDicePct:  100,
			shingle5Pct:    100,
			shingle7Pct:    100,
			lineCommon:     len(a.lineSet),
			lineUnion:      len(a.lineSet),
			bigramCommon:   len(a.bigramSet),
			bigramTotal:    len(a.bigramSet) + len(b.bigramSet),
			shingle5Common: len(a.shingle5Set),
			shingle5Union:  len(a.shingle5Set),
			shingle7Common: len(a.shingle7Set),
			shingle7Union:  len(a.shingle7Set),
		}
	}
	lineJ, lineCommon, lineUnion := setJaccardPctWithCounts(a.lineSet, b.lineSet)
	biD, biCommon, biTotal := setDicePctWithCounts(a.bigramSet, b.bigramSet)
	sh5, sh5Common, sh5Union := setJaccardPctWithCounts(a.shingle5Set, b.shingle5Set)
	sh7, sh7Common, sh7Union := setJaccardPctWithCounts(a.shingle7Set, b.shingle7Set)
	composite := combineComposite(lineJ, biD, sh5, sh7, len(a.bigramSet) > 0 && len(b.bigramSet) > 0, len(a.shingle5Set) > 0 && len(b.shingle5Set) > 0, len(a.shingle7Set) > 0 && len(b.shingle7Set) > 0)
	return matchResult{
		similarityPct:  composite,
		lineJaccardPct: lineJ,
		bigramDicePct:  biD,
		shingle5Pct:    sh5,
		shingle7Pct:    sh7,
		lineCommon:     lineCommon,
		lineUnion:      lineUnion,
		bigramCommon:   biCommon,
		bigramTotal:    biTotal,
		shingle5Common: sh5Common,
		shingle5Union:  sh5Union,
		shingle7Common: sh7Common,
		shingle7Union:  sh7Union,
	}
}

// classify maps a similarity result to an SPDX expression. The pure-0BSD
// branch requires both --allow-pure-0bsd and --pure-0bsd-confirm-no-derivation
// because textual similarity alone cannot prove non-derivation; renamed or
// heavily refactored forks of upstream files retain MIT obligations.
func classify(match matchResult, cfg config) (string, string) {
	sim := match.similarityPct / 100.0
	if sim >= cfg.mitThreshold {
		return "MIT", fmt.Sprintf("composite similarity %.2f%% >= MIT threshold %.2f%%", match.similarityPct, cfg.mitThreshold*100.0)
	}
	if cfg.allowPure0BSD && cfg.pure0BSDConfirmNoDerivation && !match.directPathMatch && match.similarityPct <= cfg.pure0BSDThreshold {
		return "0BSD", fmt.Sprintf("low similarity %.2f%% <= pure-0bsd threshold %.2f%% and no direct path match (operator confirmed non-derivation)", match.similarityPct, cfg.pure0BSDThreshold)
	}
	if sim >= cfg.mixedThreshold {
		return "0BSD AND MIT", fmt.Sprintf("composite similarity %.2f%% >= mixed threshold %.2f%%", match.similarityPct, cfg.mixedThreshold*100.0)
	}
	return cfg.baseLicense, fmt.Sprintf("below mixed threshold; fallback to base license %s", cfg.baseLicense)
}

func makeNGramSet(lines []string, n int) map[uint64]struct{} {
	out := map[uint64]struct{}{}
	if n <= 0 || len(lines) < n {
		return out
	}
	for i := 0; i <= len(lines)-n; i++ {
		out[hashNGram(lines[i:i+n])] = struct{}{}
	}
	return out
}

func hashNGram(parts []string) uint64 {
	h := fnv.New64a()
	for i, p := range parts {
		_, _ = h.Write([]byte(p))
		if i+1 < len(parts) {
			_, _ = h.Write([]byte{0})
		}
	}
	return h.Sum64()
}

func combineComposite(lineJ, biD, sh5, sh7 float64, hasBi, hasS5, hasS7 bool) float64 {
	type part struct {
		score  float64
		weight float64
		ok     bool
	}
	parts := []part{
		{lineJ, 0.20, true},
		{biD, 0.30, hasBi},
		{sh5, 0.30, hasS5},
		{sh7, 0.20, hasS7},
	}
	weighted := 0.0
	total := 0.0
	for _, p := range parts {
		if !p.ok {
			continue
		}
		weighted += p.score * p.weight
		total += p.weight
	}
	if total <= 0 {
		return 0
	}
	return weighted / total
}

func setJaccardPctWithCounts[T comparable](a, b map[T]struct{}) (float64, int, int) {
	if len(a) == 0 || len(b) == 0 {
		return 0, 0, len(a) + len(b)
	}
	inter := 0
	for k := range a {
		if _, ok := b[k]; ok {
			inter++
		}
	}
	union := len(a) + len(b) - inter
	if union <= 0 {
		return 0, inter, union
	}
	return float64(inter) / float64(union) * 100.0, inter, union
}

func setDicePctWithCounts[T comparable](a, b map[T]struct{}) (float64, int, int) {
	if len(a) == 0 || len(b) == 0 {
		return 0, 0, len(a) + len(b)
	}
	inter := 0
	for k := range a {
		if _, ok := b[k]; ok {
			inter++
		}
	}
	den := len(a) + len(b)
	if den <= 0 {
		return 0, inter, den
	}
	return 2.0 * float64(inter) / float64(den) * 100.0, inter, den
}

func loadOverrides(path string) (map[string]string, error) {
	if strings.TrimSpace(path) == "" {
		return map[string]string{}, nil
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	loaded := map[string]string{}
	if err := json.Unmarshal(raw, &loaded); err != nil {
		return nil, err
	}
	out := map[string]string{}
	for k, v := range loaded {
		rel := filepath.ToSlash(strings.TrimSpace(k))
		lic := strings.TrimSpace(v)
		if rel != "" && lic != "" {
			out[rel] = lic
		}
	}
	return out, nil
}

func isHeaderExt(path string, exts map[string]struct{}) bool {
	ext := strings.ToLower(filepath.Ext(path))
	_, ok := exts[ext]
	return ok
}

func removeSPDXFromNonTargetFiles(cfg config) (int, error) {
	rootAbs, _ := filepath.Abs(cfg.repoRoot)
	removed := 0
	err := filepath.WalkDir(rootAbs, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			if _, skip := cfg.excludedDirs[d.Name()]; skip {
				return filepath.SkipDir
			}
			return nil
		}
		rel, err := filepath.Rel(rootAbs, path)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if shouldSkipFile(cfg, rel, path) {
			return nil
		}
		if isHeaderExt(path, cfg.headerExts) {
			return nil
		}
		changed, err := removeSPDXLine(path)
		if err != nil {
			return err
		}
		if changed {
			removed++
		}
		return nil
	})
	return removed, err
}

func removeSPDXLine(path string) (bool, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return false, err
	}
	text := string(raw)
	lines := strings.Split(text, "\n")
	maxScan := 25
	if len(lines) < maxScan {
		maxScan = len(lines)
	}
	idx := -1
	for i := 0; i < maxScan; i++ {
		if strings.Contains(lines[i], "SPDX-License-Identifier:") {
			idx = i
			break
		}
	}
	if idx < 0 {
		return false, nil
	}
	out := append([]string{}, lines[:idx]...)
	if idx+1 < len(lines) && strings.TrimSpace(lines[idx+1]) == "" {
		out = append(out, lines[idx+2:]...)
	} else {
		out = append(out, lines[idx+1:]...)
	}
	newText := strings.Join(out, "\n")
	if newText == text {
		return false, nil
	}
	return true, os.WriteFile(path, []byte(newText), 0o644)
}

func upsertSPDX(path, spdx string, replaceExisting bool) (bool, string, error) {
	ext := strings.ToLower(filepath.Ext(path))
	style, ok := commentStyleByExt[ext]
	if !ok {
		return false, "", nil
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return false, "", err
	}
	text := string(raw)
	lines := strings.Split(text, "\n")
	existingIdx := -1
	existingValue := ""
	maxScan := 25
	if len(lines) < maxScan {
		maxScan = len(lines)
	}
	for i := 0; i < maxScan; i++ {
		if strings.Contains(lines[i], "SPDX-License-Identifier:") {
			existingIdx = i
			m := spdxPattern.FindStringSubmatch(lines[i])
			if len(m) > 1 {
				existingValue = strings.TrimSpace(m[1])
			}
			break
		}
	}
	spdxLine := formatSPDX(style, spdx)
	if existingIdx >= 0 {
		if !replaceExisting {
			return false, existingValue, nil
		}
		lines[existingIdx] = spdxLine
	} else {
		insertAt := 0
		if len(lines) > 0 && strings.HasPrefix(lines[0], "#!") {
			insertAt = 1
		}
		if ext == ".py" && len(lines) > insertAt && strings.HasPrefix(lines[insertAt], "#") && strings.Contains(lines[insertAt], "coding") {
			insertAt++
		}
		prefix := append([]string{}, lines[:insertAt]...)
		suffix := append([]string{}, lines[insertAt:]...)
		lines = append(prefix, spdxLine, "")
		lines = append(lines, suffix...)
	}
	newText := strings.Join(lines, "\n")
	if newText == text {
		return false, existingValue, nil
	}
	return true, existingValue, os.WriteFile(path, []byte(newText), 0o644)
}

func formatSPDX(style, spdx string) string {
	switch style {
	case "hash":
		return "# SPDX-License-Identifier: " + spdx
	case "line":
		return "// SPDX-License-Identifier: " + spdx
	case "block":
		return "/* SPDX-License-Identifier: " + spdx + " */"
	case "html":
		return "<!-- SPDX-License-Identifier: " + spdx + " -->"
	default:
		return "// SPDX-License-Identifier: " + spdx
	}
}

func formatCountSummary(counts map[string]int, total float64) string {
	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := make([]string, 0, len(keys))
	for _, k := range keys {
		parts = append(parts, fmt.Sprintf("%s: %d (%.2f%%)", k, counts[k], pct(counts[k], total)))
	}
	return strings.Join(parts, ", ")
}

func shouldExplainPath(relPath string, explainAll bool, explainPaths map[string]struct{}) bool {
	if explainAll {
		return true
	}
	_, ok := explainPaths[filepath.ToSlash(relPath)]
	return ok
}

func printExplanation(relPath string, match matchResult, license, decisionReason string, cfg config) {
	fmt.Printf("\n--- score explanation: %s ---\n", relPath)
	if match.upstreamRelPath == "" {
		fmt.Printf("upstream match: <none>\n")
	} else {
		fmt.Printf("upstream match: %s\n", match.upstreamRelPath)
	}
	fmt.Printf("direct path match: %v\n", match.directPathMatch)
	fmt.Printf("composite similarity: %.2f%%\n", match.similarityPct)
	fmt.Printf("line_jaccard: %.2f%% (%d common / %d union)\n", match.lineJaccardPct, match.lineCommon, match.lineUnion)
	fmt.Printf("bigram_dice: %.2f%% (%d common / %d total)\n", match.bigramDicePct, match.bigramCommon, match.bigramTotal)
	fmt.Printf("shingle5_jaccard: %.2f%% (%d common / %d union)\n", match.shingle5Pct, match.shingle5Common, match.shingle5Union)
	fmt.Printf("shingle7_jaccard: %.2f%% (%d common / %d union)\n", match.shingle7Pct, match.shingle7Common, match.shingle7Union)
	fmt.Printf(
		"thresholds: mit=%.2f%% mixed=%.2f%% pure_0bsd=%.2f%% allow_pure_0bsd=%v\n",
		cfg.mitThreshold*100.0,
		cfg.mixedThreshold*100.0,
		cfg.pure0BSDThreshold,
		cfg.allowPure0BSD,
	)
	fmt.Printf("decision: %s (%s)\n", license, decisionReason)
	fmt.Printf("--- end explanation ---\n")
}

func round2(v float64) float64 {
	return float64(int(v*100+0.5)) / 100
}

func pct(count int, total float64) float64 {
	if total <= 0 {
		return 0
	}
	return float64(count) / total * 100.0
}

// emitSafetyNotices prints stderr warnings for flag combinations that can
// silently relicense or strip third-party license markers. The pure-0BSD
// branch in classify also requires the explicit confirm flag, so this
// function reminds the operator when --allow-pure-0bsd is set without it.
func emitSafetyNotices(cfg config) {
	if cfg.allowPure0BSD && !cfg.pure0BSDConfirmNoDerivation {
		fmt.Fprintln(os.Stderr,
			"warning: --allow-pure-0bsd is set but --pure-0bsd-confirm-no-derivation is not; "+
				"pure 0BSD classification will not be applied. Textual similarity is not a legal "+
				"test for derivative-work status.")
	}
	if cfg.allowPure0BSD && cfg.pure0BSDConfirmNoDerivation {
		fmt.Fprintln(os.Stderr,
			"warning: pure-0BSD classification is enabled. Files with low similarity and no "+
				"direct path match will be labeled 0BSD. Confirm those files are not derivative "+
				"works of upstream sources before publishing.")
	}
	if cfg.cleanNonTarget {
		fmt.Fprintln(os.Stderr,
			"warning: --clean-non-target-spdx is set; SPDX headers in files outside header-exts "+
				"will be removed. Audit the diff before committing to avoid stripping third-party "+
				"license markers in vendored or generated files.")
	}
	if cfg.replaceExisting {
		fmt.Fprintln(os.Stderr,
			"warning: --replace-existing is set; existing SPDX headers will be overwritten by "+
				"the classifier output. Review the report-json before committing.")
	}
}

func exitErr(err error) {
	_, _ = fmt.Fprintf(os.Stderr, "Error: %v\n", err)
	os.Exit(1)
}

func init() {
	_ = runtime.GOMAXPROCS(runtime.NumCPU())
}
