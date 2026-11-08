package bridge

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

func tmpDM(t *testing.T) *DownloadManager {
	t.Helper()
	return NewDownloadManager(func() string { return t.TempDir() })
}

func b64(s string) string { return base64.StdEncoding.EncodeToString([]byte(s)) }

func TestSanitizeName(t *testing.T) {
	cases := map[string]string{
		"con":               "_con",
		"CON.txt":           "_CON.txt",
		"lpt9":              "_lpt9",
		"file.txt":          "file.txt",
		"..hidden":          "hidden",
		"trailing... ":      "trailing",
		"a/b/c.txt":         "c.txt",
		"":                  "download",
		"\u202Eevil.txt":    "evil.txt",
		"normal \u200F.txt": "normal .txt",
	}
	for in, want := range cases {
		if got := sanitizeName(in); got != want {
			t.Fatalf("sanitizeName(%q)=%q want %q", in, got, want)
		}
	}
	// rune-safe cap keeps extension and valid UTF-8
	long := strings.Repeat("a", 200) + ".txt"
	got := sanitizeName(long)
	if len(got) > maxNameBytes+len(".txt") || !strings.HasSuffix(got, ".txt") {
		t.Fatalf("long name cap failed: len=%d", len(got))
	}
	if !utf8Valid(got) {
		t.Fatal("rune boundary split")
	}
}

func utf8Valid(s string) bool {
	for _, r := range s {
		if r == 0xFFFD {
			return false
		}
	}
	return true
}

func TestBeginChunkEnd(t *testing.T) {
	d := tmpDM(t)
	r := d.Begin("a.txt", 5, 1)
	if r["ok"] != true {
		t.Fatalf("begin: %v", r)
	}
	id := r["id"].(string)
	if res := d.Chunk(id, b64("hello")); res["ok"] != true {
		t.Fatalf("chunk: %v", res)
	}
	if res := d.Chunk(id, "!!!bad"); res["ok"] != false {
		t.Fatal("bad b64 accepted")
	}
	if res := d.End(id); res["ok"] != true {
		t.Fatalf("end: %v", res)
	}
	data, _ := os.ReadFile(r["path"].(string))
	if string(data) != "hello" {
		t.Fatalf("content %q", data)
	}
}

func TestConcurrencyCap(t *testing.T) {
	d := tmpDM(t)
	ids := []string{}
	for i := 0; i < maxConcurrentDownloads; i++ {
		r := d.Begin("f"+string(rune('a'+i))+".txt", 0, 1)
		if r["ok"] != true {
			t.Fatalf("begin %d: %v", i, r)
		}
		ids = append(ids, r["id"].(string))
	}
	if r := d.Begin("extra.txt", 0, 1); r["ok"] != false {
		t.Fatal("9th download allowed")
	}
	for _, id := range ids {
		d.Abort(id)
	}
}

func TestSizeCap(t *testing.T) {
	d := tmpDM(t)
	r := d.Begin("big.bin", 0, 1)
	id := r["id"].(string)
	// exceed 4GiB by writing chunks near the cap: write 4GiB is too much for a
	// test, so shrink via direct state manipulation is not possible; instead
	// verify the chunk-size cap and trust the arithmetic for the byte cap.
	big := make([]byte, maxChunkBytes+1)
	if res := d.Chunk(id, base64.StdEncoding.EncodeToString(big)); res["ok"] != false {
		t.Fatal("oversize chunk accepted")
	}
	d.Abort(id)
}

func TestAbortAll(t *testing.T) {
	d := tmpDM(t)
	r := d.Begin("x.txt", 0, 1)
	p := r["path"].(string)
	d.AbortAll()
	if _, err := os.Stat(p); !os.IsNotExist(err) {
		t.Fatal("partial not removed by AbortAll")
	}
}

func TestAbortForWindow(t *testing.T) {
	d := tmpDM(t)
	r1 := d.Begin("w1.txt", 0, 1)
	r2 := d.Begin("w2.txt", 0, 2)
	p1, p2 := r1["path"].(string), r2["path"].(string)
	d.AbortForWindow(1)
	if _, err := os.Stat(p1); !os.IsNotExist(err) {
		t.Fatal("window-1 partial not removed")
	}
	if _, err := os.Stat(p2); err != nil {
		t.Fatal("window-2 partial wrongly removed")
	}
	// the surviving download still accepts chunks
	if res := d.Chunk(r2["id"].(string), b64("data")); res["ok"] != true {
		t.Fatalf("surviving chunk failed: %v", res)
	}
	d.AbortAll()
}

func TestJanitor(t *testing.T) {
	d := tmpDM(t)
	var mu sync.Mutex
	fakeNow := time.Now()
	d.now = func() time.Time {
		mu.Lock()
		defer mu.Unlock()
		return fakeNow
	}
	d.janitorEvery = time.Millisecond
	r := d.Begin("idle.txt", 0, 1)
	p := r["path"].(string)
	mu.Lock()
	fakeNow = fakeNow.Add(idleTimeout + time.Second)
	mu.Unlock()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(p); os.IsNotExist(err) {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("idle download not reaped")
}

func TestSymlinkDirRefused(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink perms")
	}
	base := t.TempDir()
	real := filepath.Join(base, "real")
	_ = os.MkdirAll(real, 0o755)
	link := filepath.Join(base, "MeshChatX")
	_ = os.Symlink(real, link)
	d := NewDownloadManager(func() string { return base })
	if got := d.Dir(); got != "" {
		t.Fatalf("symlinked dir accepted: %q", got)
	}
}
