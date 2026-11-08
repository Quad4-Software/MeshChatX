package logger

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWriteCreatesLogFile(t *testing.T) {
	dir := t.TempDir()
	l := New(func() string { return dir })
	l.Write("hello world")
	data, err := os.ReadFile(filepath.Join(dir, "meshchatx.log"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "[wails] hello world") {
		t.Fatalf("log content: %q", data)
	}
	// second write appends
	l.Write("second line")
	data, _ = os.ReadFile(filepath.Join(dir, "meshchatx.log"))
	if strings.Count(string(data), "[wails]") != 2 {
		t.Fatalf("append failed: %q", data)
	}
}

func TestPendingUntilDirAvailable(t *testing.T) {
	dir := t.TempDir()
	available := false
	l := New(func() string {
		if !available {
			return ""
		}
		return dir
	})
	l.Write("early message")
	// nothing written yet (dir unavailable -> pending)
	if _, err := os.Stat(filepath.Join(dir, "meshchatx.log")); !os.IsNotExist(err) {
		t.Fatal("log written before dir available")
	}
	available = true
	l.Write("later message")
	data, err := os.ReadFile(filepath.Join(dir, "meshchatx.log"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "early message") || !strings.Contains(string(data), "later message") {
		t.Fatalf("pending not flushed: %q", data)
	}
}

func TestRotation(t *testing.T) {
	dir := t.TempDir()
	logPath := filepath.Join(dir, "meshchatx.log")
	// pre-fill beyond 5MiB
	big := strings.Repeat("x", LogMaxBytes+100)
	if err := os.WriteFile(logPath, []byte(big), 0o644); err != nil {
		t.Fatal(err)
	}
	l := New(func() string { return dir })
	l.Write("after rotation")
	if _, err := os.Stat(logPath + ".1"); err != nil {
		t.Fatal("rotated file missing")
	}
	data, _ := os.ReadFile(logPath)
	if !strings.Contains(string(data), "after rotation") {
		t.Fatal("new log missing entry")
	}
	if len(data) > LogMaxBytes {
		t.Fatalf("log still too big: %d", len(data))
	}
}

func TestWriteToUnwritableDirDisables(t *testing.T) {
	// getDir returns a path under a file (not a dir) -> MkdirAll fails -> disabled
	blocker := filepath.Join(t.TempDir(), "blocker")
	if err := os.WriteFile(blocker, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	l := New(func() string { return filepath.Join(blocker, "sub") })
	l.Write("one")
	l.Write("two") // must not panic; disabled after first failure
}
