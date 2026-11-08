package crashreport

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestPersistLoadClearCrashReport(t *testing.T) {
	dir := t.TempDir()
	code := 3
	crash := &Crash{
		Code: &code, Signal: "", Stdout: "out", Stderr: "err",
		At: 1234, Platform: "linux", Pid: &code,
	}
	payload := PersistCrashReport(dir, crash)
	if payload == nil {
		t.Fatal("persist returned nil")
	}
	if _, err := os.Stat(GetCrashReportPath(dir)); err != nil {
		t.Fatalf("report file missing: %v", err)
	}
	loaded := LoadCrashReport(dir)
	if loaded == nil {
		t.Fatal("load returned nil")
	}
	if loaded.Code == nil || *loaded.Code != 3 || loaded.Stdout != "out" || loaded.Stderr != "err" {
		t.Fatalf("loaded: %+v", loaded)
	}
	ClearCrashReport(dir)
	if LoadCrashReport(dir) != nil {
		t.Fatal("report not cleared")
	}
	// nil/empty storage is a no-op
	PersistCrashReport("", crash)
	LoadCrashReport("")
	ClearCrashReport("")
}

func TestLoadCrashReportCorrupt(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(GetLogsDir(dir), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(GetCrashReportPath(dir), []byte("{bad json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if LoadCrashReport(dir) != nil {
		t.Fatal("corrupt report should load as nil")
	}
}

func TestNormalizeCrash(t *testing.T) {
	if NormalizeCrash(nil) != nil {
		t.Fatal("nil crash")
	}
	c := NormalizeCrash(map[string]any{
		"code": float64(1), "signal": "SIGTERM", "stdout": strings.Repeat("x", 20000),
		"at": float64(99), "platform": "linux", "pid": float64(42),
	})
	if c == nil || c.Code == nil || *c.Code != 1 || c.Signal != "SIGTERM" || c.At != 99 {
		t.Fatalf("normalize: %+v", c)
	}
	if len(c.Stdout) > 12000 {
		t.Fatalf("stdout not tailed: %d", len(c.Stdout))
	}
}

func TestParseMemoryLogLine(t *testing.T) {
	if ParseMemoryLogLine("") != nil {
		t.Fatal("empty")
	}
	if ParseMemoryLogLine("no marker here") != nil {
		t.Fatal("no marker")
	}
	got := ParseMemoryLogLine("noise\nMESHCHAT_MEMORY: total_mb=4096 available_mb=512 percent_used=87 action=warn\nmore")
	if got == nil {
		t.Fatal("no parse")
	}
	if got["total_mb"] != 4096.0 || got["available_mb"] != 512.0 || got["action"] != "warn" {
		t.Fatalf("parse: %v", got)
	}
}

func TestDiagnoseBackendCrash(t *testing.T) {
	code := func(i int) *int { return &i }
	cases := []struct {
		name    string
		stderr  string
		stdout  string
		code    *int
		signal  string
		wantCat string
	}{
		{"memory abort", "", "MESHCHAT_MEMORY: available_mb=100 action=abort", nil, "", "memory"},
		{"memory warn", "", "MESHCHAT_MEMORY: available_mb=900 action=warn", nil, "", "memory"},
		{"oom text", "out of memory", "", nil, "", "memory"},
		{"permission", "EACCES permission denied", "", nil, "", "permission"},
		{"port conflict", "address already in use port 9337", "", nil, "", "port-conflict"},
		{"vcruntime", "VCRUNTIME140.dll missing", "", nil, "", "runtime"},
		{"db corrupt", "database is malformed and corrupt", "", nil, "", "database"},
		{"python crash", "!!! application crash detected !!!", "", nil, "", "python-crash"},
		{"access violation", "", "", code(3221226505), "", "native-crash"},
		{"exit signal", "", "", nil, "SIGTERM", "exit-signal"},
		{"exit code", "", "", code(1), "", "exit-code"},
		{"unknown", "", "", nil, "", "unknown"},
	}
	for _, tc := range cases {
		got := DiagnoseBackendCrash(tc.stderr, tc.stdout, tc.code, tc.signal)
		if got.Category != tc.wantCat {
			t.Errorf("%s: got %q want %q", tc.name, got.Category, tc.wantCat)
		}
		if len(got.Hints) == 0 {
			t.Errorf("%s: no hints", tc.name)
		}
	}
}

func TestListRecoveryBackups(t *testing.T) {
	dir := t.TempDir()
	auto := filepath.Join(dir, "database-backups")
	snap := filepath.Join(dir, "snapshots")
	for _, d := range []string{auto, snap} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	write := func(d, name string) {
		if err := os.WriteFile(filepath.Join(d, name), []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	write(auto, "backup-2024-01-01.zip")
	write(auto, "backup-SUSPICIOUS-2024-01-02.zip")
	write(snap, "snapshot-2024-01-03.zip")
	write(auto, "not-a-zip.txt")

	// deterministic mtimes: snapshot newest, suspicious middle, plain oldest
	old := time.Now().Add(-3 * time.Hour)
	mid := time.Now().Add(-2 * time.Hour)
	newest := time.Now().Add(-1 * time.Hour)
	_ = os.Chtimes(filepath.Join(auto, "backup-2024-01-01.zip"), old, old)
	_ = os.Chtimes(filepath.Join(auto, "backup-SUSPICIOUS-2024-01-02.zip"), mid, mid)
	_ = os.Chtimes(filepath.Join(snap, "snapshot-2024-01-03.zip"), newest, newest)

	backups := ListRecoveryBackups(dir)
	if len(backups) != 3 {
		t.Fatalf("backups: %d %v", len(backups), backups)
	}
	kinds := map[string]string{}
	suspicious := false
	for _, b := range backups {
		kinds[b.Kind] = b.Kind
		if b.Suspicious {
			suspicious = true
		}
		if b.Name == "not-a-zip.txt" {
			t.Fatal("non-zip listed")
		}
	}
	if kinds["auto"] != "auto" || kinds["snapshot"] != "snapshot" {
		t.Fatalf("kinds: %v", kinds)
	}
	if !suspicious {
		t.Fatal("suspicious flag not set")
	}
	// sorted newest first by CreatedAt — snapshot is newest
	if backups[0].Kind != "snapshot" {
		t.Fatalf("order: %+v", backups)
	}
	if ListRecoveryBackups("") != nil {
		t.Fatal("empty storage")
	}
}

func TestPickPreferredRestoreBackup(t *testing.T) {
	if PickPreferredRestoreBackup(nil) != nil {
		t.Fatal("nil backups")
	}
	backups := []RecoveryBackup{
		{Name: "a", Suspicious: true},
		{Name: "b", Suspicious: false},
	}
	got := PickPreferredRestoreBackup(backups)
	if got == nil || got.Name != "b" {
		t.Fatalf("preferred: %+v", got)
	}
	allSuspicious := []RecoveryBackup{{Name: "a", Suspicious: true}}
	if got := PickPreferredRestoreBackup(allSuspicious); got == nil || got.Name != "a" {
		t.Fatalf("all suspicious should return first: %+v", got)
	}
}

func TestCrashRecoveryInfo(t *testing.T) {
	dir := t.TempDir()
	code := 1
	info := CrashRecoveryInfo(dir, "/rns", "linux", "", "stderr-text", "stdout-text", &code, "")
	if info["supportsOfflineRestore"] != true {
		t.Fatalf("offline restore: %v", info["supportsOfflineRestore"])
	}
	diag, ok := info["diagnosis"].(Diagnosis)
	if !ok || diag.Category != "exit-code" {
		t.Fatalf("diagnosis: %v", info["diagnosis"])
	}
	if info["preferredBackup"] != nil {
		t.Fatalf("unexpected backup: %v", info["preferredBackup"])
	}
	guide, _ := info["cleanupGuide"].(string)
	if !strings.Contains(guide, dir) {
		t.Fatal("cleanup guide missing storage dir")
	}
}
