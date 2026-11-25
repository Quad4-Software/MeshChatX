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

func TestRotationReopensFileAfterCountedBytesExceedLimit(t *testing.T) {
	dir := t.TempDir()
	logPath := filepath.Join(dir, "meshchatx.log")
	l := New(func() string { return dir })
	defer l.Close()

	l.Write("before rotation")
	l.mu.Lock()
	firstFile := l.file
	l.mu.Unlock()
	if firstFile == nil {
		t.Fatal("log file was not kept open after first write")
	}

	// Approach the rotation threshold through bytes written by this logger,
	// then write one chunk that crosses it. Rotation must use the in-memory
	// count before that write, close the old handle, and reopen meshchatx.log.
	for {
		l.mu.Lock()
		size := l.fileSize
		l.mu.Unlock()
		if size > LogMaxBytes-4096 {
			break
		}
		l.Write(strings.Repeat("x", 1024))
	}
	l.Write(strings.Repeat("x", 4096))
	l.Write("after rotation")

	l.mu.Lock()
	rotatedFile := l.file
	trackedSize := l.fileSize
	l.mu.Unlock()
	if rotatedFile == nil || rotatedFile == firstFile {
		t.Fatal("rotation did not close and reopen the kept-open file handle")
	}
	if trackedSize <= 0 || trackedSize > LogMaxBytes {
		t.Fatalf("tracked size after rotation: %d", trackedSize)
	}
	if _, err := os.Stat(logPath + ".1"); err != nil {
		t.Fatal("rotated file missing")
	}
	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "after rotation") || strings.Contains(string(data), "before rotation") {
		t.Fatalf("new log has wrong entries: %q", data)
	}
}

func TestNoStatPerLineWrite(t *testing.T) {
	dir := t.TempDir()
	origStat := openFileStat
	statCalls := 0
	openFileStat = func(f *os.File) (os.FileInfo, error) {
		statCalls++
		return f.Stat()
	}
	defer func() { openFileStat = origStat }()

	l := New(func() string { return dir })
	defer l.Close()
	l.Write("one")
	if statCalls != 1 {
		t.Fatalf("stat calls after open: %d, want 1", statCalls)
	}
	l.Write("two")
	l.Write("three")
	if statCalls != 1 {
		t.Fatalf("per-line writes statted the file: %d calls", statCalls)
	}
}

func TestCloseReleasesHandleAndWriteReopens(t *testing.T) {
	dir := t.TempDir()
	logPath := filepath.Join(dir, "meshchatx.log")
	l := New(func() string { return dir })
	l.Write("one")
	l.Close()
	l.mu.Lock()
	closed := l.file == nil
	l.mu.Unlock()
	if !closed {
		t.Fatal("Close did not release the log handle")
	}
	l.Write("two")
	defer l.Close()
	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "one") || !strings.Contains(string(data), "two") {
		t.Fatalf("writes across Close missing: %q", data)
	}
}
