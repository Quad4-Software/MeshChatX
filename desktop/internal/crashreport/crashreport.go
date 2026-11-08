// Package crashreport ports electron/backendCrashReport.js and
// electron/offlineRecovery.js: persisted crash reports, crash diagnosis and
// database-backup recovery listings.
package crashreport

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const ReportFilename = "last-backend-crash.json"

func GetLogsDir(storageDir string) string {
	return filepath.Join(storageDir, "logs")
}

func GetCrashReportPath(storageDir string) string {
	return filepath.Join(GetLogsDir(storageDir), ReportFilename)
}

func GetBackendLogPath(storageDir string) string {
	return filepath.Join(GetLogsDir(storageDir), "meshchatx.log")
}

func tailText(text string, maxChars int) string {
	if text == "" {
		return ""
	}
	if maxChars <= 0 {
		maxChars = 12000
	}
	if len(text) <= maxChars {
		return text
	}
	return text[len(text)-maxChars:]
}

type Crash struct {
	Code           *int   `json:"code"`
	Signal         string `json:"signal,omitempty"`
	Stdout         string `json:"stdout,omitempty"`
	Stderr         string `json:"stderr,omitempty"`
	At             int64  `json:"at"`
	Platform       string `json:"platform,omitempty"`
	Pid            *int   `json:"pid,omitempty"`
	SavedAt        int64  `json:"savedAt,omitempty"`
	ReportPath     string `json:"reportPath,omitempty"`
	BackendLogPath string `json:"backendLogPath,omitempty"`
}

func NormalizeCrash(crash map[string]any) *Crash {
	if crash == nil {
		return nil
	}
	out := &Crash{}
	if v, ok := crash["code"]; ok && v != nil {
		if f, ok := v.(float64); ok {
			i := int(f)
			out.Code = &i
		}
	}
	if v, ok := crash["signal"].(string); ok {
		out.Signal = v
	}
	if v, ok := crash["stdout"].(string); ok {
		out.Stdout = tailText(v, 12000)
	}
	if v, ok := crash["stderr"].(string); ok {
		out.Stderr = tailText(v, 12000)
	}
	out.At = time.Now().UnixMilli()
	if v, ok := crash["at"].(float64); ok {
		out.At = int64(v)
	}
	if v, ok := crash["platform"].(string); ok {
		out.Platform = v
	}
	if v, ok := crash["pid"].(float64); ok {
		i := int(v)
		out.Pid = &i
	}
	return out
}

// PersistCrashReport writes last-backend-crash.json under <storage>/logs.
func PersistCrashReport(storageDir string, crash *Crash) map[string]any {
	if storageDir == "" || crash == nil {
		return nil
	}
	logsDir := GetLogsDir(storageDir)
	if err := os.MkdirAll(logsDir, 0o755); err != nil {
		return nil
	}
	reportPath := GetCrashReportPath(storageDir)
	payload := map[string]any{
		"code":           crash.Code,
		"signal":         crash.Signal,
		"stdout":         crash.Stdout,
		"stderr":         crash.Stderr,
		"at":             crash.At,
		"platform":       crash.Platform,
		"pid":            crash.Pid,
		"savedAt":        time.Now().UnixMilli(),
		"reportPath":     reportPath,
		"backendLogPath": GetBackendLogPath(storageDir),
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return nil
	}
	if err := os.WriteFile(reportPath, append(data, '\n'), 0o644); err != nil {
		return nil
	}
	return payload
}

// LoadCrashReport reads last-backend-crash.json; nil when absent/corrupt.
func LoadCrashReport(storageDir string) *Crash {
	if storageDir == "" {
		return nil
	}
	data, err := os.ReadFile(GetCrashReportPath(storageDir))
	if err != nil {
		return nil
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil
	}
	return NormalizeCrash(raw)
}

func ClearCrashReport(storageDir string) {
	if storageDir == "" {
		return
	}
	_ = os.Remove(GetCrashReportPath(storageDir))
}

var memoryLineRe = regexp.MustCompile(`(?m)^MESHCHAT_MEMORY:\s*(.+)$`)

// ParseMemoryLogLine extracts the first MESHCHAT_MEMORY: line's key=value pairs.
func ParseMemoryLogLine(text string) map[string]any {
	if text == "" {
		return nil
	}
	m := memoryLineRe.FindStringSubmatch(text)
	if m == nil {
		return nil
	}
	parsed := map[string]any{}
	for _, token := range strings.Fields(m[1]) {
		idx := strings.Index(token, "=")
		if idx <= 0 {
			continue
		}
		key := token[:idx]
		value := token[idx+1:]
		switch key {
		case "total_mb", "available_mb", "percent_used":
			if f, err := strconv.ParseFloat(value, 64); err == nil {
				parsed[key] = f
			}
		default:
			parsed[key] = value
		}
	}
	if len(parsed) == 0 {
		return nil
	}
	return parsed
}

type Diagnosis struct {
	Category string   `json:"category"`
	Summary  string   `json:"summary"`
	Hints    []string `json:"hints"`
}

func containsAny(s string, needles ...string) bool {
	for _, n := range needles {
		if strings.Contains(s, n) {
			return true
		}
	}
	return false
}

// DiagnoseBackendCrash classifies a backend exit from its captured output.
func DiagnoseBackendCrash(stderr, stdout string, exitCode *int, exitSignal string) Diagnosis {
	combined := strings.ToLower(stdout + "\n" + stderr)
	rawCombined := stdout + "\n" + stderr
	var hints []string

	if ml := ParseMemoryLogLine(rawCombined); ml != nil {
		available, hasAvailable := ml["available_mb"].(float64)
		action, _ := ml["action"].(string)
		if action == "abort" || (hasAvailable && available < 200) {
			hints = append(hints,
				"Close other applications to free RAM, then relaunch.",
				"On low-memory devices, try Emergency Mode from the crash screen.")
			if hasAvailable {
				return Diagnosis{"memory", fmt.Sprintf("The backend reported critically low memory (%.0f MB available).", available), hints}
			}
			return Diagnosis{"memory", "The backend aborted startup due to critically low memory.", hints}
		}
		if action == "warn" {
			hints = append(hints, "Emergency Mode reduces startup memory use on 4 GB devices.")
			if hasAvailable {
				return Diagnosis{"memory", fmt.Sprintf("The backend detected limited memory (%.0f MB available).", available), hints}
			}
			return Diagnosis{"memory", "The backend detected limited system memory during startup.", hints}
		}
	}

	if containsAny(combined, "memoryerror", "out of memory", "cannot allocate memory", "oom") {
		hints = append(hints,
			"Close other applications to free RAM, then relaunch.",
			"On low-memory devices, try Emergency Mode from the crash screen.")
		return Diagnosis{"memory", "The backend likely ran out of memory during startup.", hints}
	}

	if containsAny(combined, "eacces", "eperm", "permission denied", "access is denied") {
		hints = append(hints,
			"Check that MeshChatX can write to its data folder.",
			"Avoid running from protected locations; portable installs should stay on a writable drive.")
		return Diagnosis{"permission", "The backend could not read or write a required file or folder.", hints}
	}

	if containsAny(combined, "address already in use", "eaddrinuse", "only one usage of each socket", "port 9337") {
		hints = append(hints, "Another backend copy may still be running. End ReticulumMeshChatX.exe in Task Manager, then relaunch.")
		return Diagnosis{"port-conflict", "Port 9337 is already in use by another process.", hints}
	}

	if containsAny(combined, "dll load failed", "vcruntime", "api-ms-win", "the specified module could not be found") {
		hints = append(hints, "Install the latest Microsoft Visual C++ Redistributable (x64), then relaunch.")
		return Diagnosis{"runtime", "A required Windows runtime library may be missing.", hints}
	}

	if containsAny(combined, "database") && containsAny(combined, "corrupt", "malformed") {
		hints = append(hints,
			"Use Restore latest backup on the crash screen if automatic backups are listed.",
			"Try auto-repair on the crash screen to run SQLite recovery on the next launch.",
			"Copy reset instructions from the crash screen to remove MeshChatX and Reticulum data folders and start fresh.",
			"Emergency Mode can still open the app without the database so you can download backups from About.")
		return Diagnosis{"database", "The local database may be corrupted.", hints}
	}

	if containsAny(combined, "!!! application crash detected !!!") {
		hints = append(hints, "Open the saved crash report and meshchatx.log for the full diagnostic trace.")
		return Diagnosis{"python-crash", "The Python backend crash recovery system captured a fatal error.", hints}
	}

	if exitCode != nil && *exitCode == 3221226505 || containsAny(combined, "access violation", "segfault") {
		hints = append(hints, "This can happen on older GPUs or low-memory systems. Try creating a disable-gpu file in the data folder.")
		return Diagnosis{"native-crash", "The backend process crashed natively (access violation).", hints}
	}

	if exitSignal != "" {
		hints = append(hints, "Open the logs folder below and send meshchatx.log plus the crash report when asking for support.")
		if strings.ToUpper(exitSignal) == "SIGPIPE" {
			hints = append(hints, "SIGPIPE usually means a peer socket closed mid-write (for example I2P/SAM). MeshChatX ignores SIGPIPE at startup so this should not kill modern builds.")
		}
		return Diagnosis{"exit-signal", fmt.Sprintf("The backend was terminated by %s.", exitSignal), hints}
	}

	if exitCode != nil && *exitCode != 0 {
		hints = append(hints, "Open the logs folder below and send meshchatx.log plus the crash report when asking for support.")
		return Diagnosis{"exit-code", fmt.Sprintf("The backend exited with code %d.", *exitCode), hints}
	}

	return Diagnosis{"unknown", "The backend stopped before the UI could connect.",
		[]string{"Review the saved crash report and meshchatx.log for details."}}
}

// DiagnosticPaths mirrors getDiagnosticPaths().
func DiagnosticPaths(storageDir, reticulumConfigDir string) map[string]any {
	var logsDir, backendLogPath, crashReportPath any
	if storageDir != "" {
		logsDir = GetLogsDir(storageDir)
		backendLogPath = GetBackendLogPath(storageDir)
		crashReportPath = GetCrashReportPath(storageDir)
	}
	return map[string]any{
		"storageDir":         nilIfEmpty(storageDir),
		"reticulumConfigDir": nilIfEmpty(reticulumConfigDir),
		"logsDir":            logsDir,
		"backendLogPath":     backendLogPath,
		"crashReportPath":    crashReportPath,
	}
}

func nilIfEmpty(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// ---- offlineRecovery.js port ----------------------------------------------

type RecoveryBackup struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	Size       int64  `json:"size"`
	CreatedAt  string `json:"createdAt"`
	Kind       string `json:"kind"`
	Suspicious bool   `json:"suspicious"`
}

var suspiciousRe = regexp.MustCompile(`(?i)SUSPICIOUS`)

func listZipBackupsInDir(dir, kind string) []RecoveryBackup {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	var out []RecoveryBackup
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".zip") {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		out = append(out, RecoveryBackup{
			Name:       e.Name(),
			Path:       filepath.Join(dir, e.Name()),
			Size:       info.Size(),
			CreatedAt:  info.ModTime().UTC().Format(time.RFC3339Nano),
			Kind:       kind,
			Suspicious: suspiciousRe.MatchString(e.Name()),
		})
	}
	return out
}

// ListRecoveryBackups merges database-backups/ ("auto") and snapshots/
// ("snapshot"), newest first.
func ListRecoveryBackups(storageDir string) []RecoveryBackup {
	if storageDir == "" {
		return nil
	}
	backups := append(
		listZipBackupsInDir(filepath.Join(storageDir, "database-backups"), "auto"),
		listZipBackupsInDir(filepath.Join(storageDir, "snapshots"), "snapshot")...,
	)
	sort.SliceStable(backups, func(i, j int) bool {
		return backups[i].CreatedAt > backups[j].CreatedAt
	})
	return backups
}

// PickPreferredRestoreBackup prefers non-suspicious backups.
func PickPreferredRestoreBackup(backups []RecoveryBackup) *RecoveryBackup {
	if len(backups) == 0 {
		return nil
	}
	for i := range backups {
		if !backups[i].Suspicious {
			return &backups[i]
		}
	}
	return &backups[0]
}

// BuildDataCleanupGuide renders the manual data-removal instructions.
func BuildDataCleanupGuide(storageDir, reticulumConfigDir, platform, portableExecutableDir string) string {
	if storageDir == "" {
		storageDir = "~/.reticulum-meshchatx"
	}
	if reticulumConfigDir == "" {
		reticulumConfigDir = "~/.reticulum"
	}
	legacyDir := regexp.MustCompile(`(?i)meshchatx$`).ReplaceAllString(storageDir, "meshchat")
	legacyDir = regexp.MustCompile(`(?i)MeshChatX$`).ReplaceAllString(storageDir, "meshchat")

	var lines []string
	lines = append(lines,
		"Complete MeshChatX / Reticulum data reset",
		"",
		"Quit MeshChatX completely before deleting anything. On Windows, also end ReticulumMeshChatX.exe in Task Manager if it is still running.",
		"",
		"MeshChatX storage (database, identities, automatic backups, logs):",
		"  "+storageDir,
		"",
		"Reticulum network stack (config, ratchets, path table, interface state):",
		"  "+reticulumConfigDir,
		"",
	)
	if legacyDir != "" && legacyDir != storageDir {
		lines = append(lines,
			"Legacy Reticulum MeshChat storage (only if you migrated from the old app):",
			"  "+legacyDir,
			"",
		)
	}
	if platform == "windows" && portableExecutableDir != "" {
		lines = append(lines,
			"Portable Windows install: the folders above are next to MeshChatX.exe, not in your user profile.",
			"  Portable app folder: "+portableExecutableDir,
			"",
		)
	}
	lines = append(lines,
		"Linux / macOS default locations:",
		"  ~/.reticulum-meshchatx/",
		"  ~/.reticulum/",
		"  ~/.reticulum-meshchat/ (legacy, if present)",
		"",
		"Windows default locations:",
		"  %USERPROFILE%\\.reticulum-meshchatx\\",
		"  %USERPROFILE%\\.reticulum\\",
		"  %USERPROFILE%\\.reticulum-meshchat\\ (legacy, if present)",
		"",
		"Removing these folders deletes your local identity, messages, contacts, and network path cache. You will get a new identity on the next launch unless you restore from a backup zip first.",
		"",
		"Automatic database backups are kept under database-backups/ inside the MeshChatX storage folder when the app has run successfully before.",
	)
	return strings.Join(lines, "\n")
}

// CrashRecoveryInfo is the payload for the crash-recovery-info bridge call.
func CrashRecoveryInfo(storageDir, reticulumConfigDir, platform, portableExecutableDir string, stderr, stdout string, exitCode *int, exitSignal string) map[string]any {
	backups := ListRecoveryBackups(storageDir)
	if backups == nil {
		backups = []RecoveryBackup{}
	}
	preferred := PickPreferredRestoreBackup(backups)
	diagnosis := DiagnoseBackendCrash(stderr, stdout, exitCode, exitSignal)

	var backupsDir, snapshotsDir, logsDir any
	if storageDir != "" {
		backupsDir = filepath.Join(storageDir, "database-backups")
		snapshotsDir = filepath.Join(storageDir, "snapshots")
		logsDir = GetLogsDir(storageDir)
	}
	paths := map[string]any{
		"storageDir":         nilIfEmpty(storageDir),
		"reticulumConfigDir": nilIfEmpty(reticulumConfigDir),
		"backupsDir":         backupsDir,
		"snapshotsDir":       snapshotsDir,
		"logsDir":            logsDir,
	}

	var preferredAny any
	if preferred != nil {
		preferredAny = preferred
	}

	return map[string]any{
		"diagnosis":              diagnosis,
		"paths":                  paths,
		"backups":                backups,
		"preferredBackup":        preferredAny,
		"cleanupGuide":           BuildDataCleanupGuide(storageDir, reticulumConfigDir, platform, portableExecutableDir),
		"supportsOfflineRestore": storageDir != "",
	}
}
