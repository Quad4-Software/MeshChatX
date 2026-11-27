package bridge

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const (
	maxConcurrentDownloads = 8
	maxDownloadBytes       = int64(4) << 30 // 4 GiB per download
	maxChunkBytes          = 4 << 20        // 4 MiB decoded per chunk
	idleTimeout            = 2 * time.Minute
	maxNameBytes           = 180
)

// DownloadManager receives base64 chunks from the renderer and writes them
// under <Downloads>/MeshChatX (Electron's exchange dir), sanitizing names and
// de-duplicating collisions.
type DownloadManager struct {
	mu     sync.Mutex
	getDir func() string
	dir    string
	active map[string]*downloadState

	// janitor state (lazy; injectable for tests)
	janitorStarted bool
	janitorEvery   time.Duration
	now            func() time.Time
}

type downloadState struct {
	path      string
	file      *os.File
	size      int64
	written   int64
	lastSeen  time.Time
	windowID  uint
	completed bool
}

func NewDownloadManager(getDownloadsDir func() string) *DownloadManager {
	return &DownloadManager{
		getDir:       getDownloadsDir,
		active:       map[string]*downloadState{},
		janitorEvery: 30 * time.Second,
		now:          time.Now,
	}
}

// Dir returns <Downloads>/MeshChatX, creating it lazily. Refuses to use a
// symlinked exchange dir.
func (d *DownloadManager) Dir() string {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.dir != "" {
		return d.dir
	}
	base := ""
	if d.getDir != nil {
		base = d.getDir()
	}
	if base == "" {
		home, _ := os.UserHomeDir()
		base = filepath.Join(home, "Downloads")
	}
	dir := filepath.Join(base, "MeshChatX")
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return ""
	}
	if fi, err := os.Lstat(dir); err == nil && fi.Mode()&os.ModeSymlink != 0 {
		return ""
	}
	d.dir = dir
	return dir
}

var reservedNames = map[string]bool{
	"con": true, "prn": true, "aux": true, "nul": true,
	"com1": true, "com2": true, "com3": true, "com4": true, "com5": true,
	"com6": true, "com7": true, "com8": true, "com9": true,
	"lpt1": true, "lpt2": true, "lpt3": true, "lpt4": true, "lpt5": true,
	"lpt6": true, "lpt7": true, "lpt8": true, "lpt9": true,
}

// sanitizeName produces a safe single path component.
func sanitizeName(name string) string {
	base := name
	base = strings.ReplaceAll(base, "\\", "/")
	if i := strings.LastIndex(base, "/"); i >= 0 {
		base = base[i+1:]
	}
	var b strings.Builder
	for _, r := range base {
		switch {
		case r < 0x20, r == '<', r == '>', r == ':', r == '"', r == '|', r == '?', r == '*':
			b.WriteRune('_')
		case r == 0x7f || (r >= 0x200e && r <= 0x200f) || (r >= 0x202a && r <= 0x202e) || (r >= 0x2066 && r <= 0x2069):
			// control + bidi override/mark chars: drop entirely
		default:
			b.WriteRune(r)
		}
	}
	out := strings.Trim(b.String(), " .")
	// strip remaining leading dots then trailing dots/spaces
	out = strings.TrimLeft(out, ".")
	out = strings.TrimRight(out, ". ")
	if out == "" {
		out = "download"
	}
	// Windows reserved device names (also con.txt etc.)
	stem := strings.ToLower(strings.SplitN(out, ".", 2)[0])
	if reservedNames[stem] {
		out = "_" + out
	}
	// rune-safe byte cap keeping the extension when it is short enough to
	// be worth keeping; a longer "extension" is just tail bytes, so drop it.
	if len(out) > maxNameBytes {
		ext := filepath.Ext(out)
		if len(ext) > 32 || len(ext) > maxNameBytes-16 {
			ext = ""
		}
		keep := maxNameBytes - len(ext)
		runes := []rune(out)
		for len(string(runes)) > keep {
			runes = runes[:len(runes)-1]
		}
		out = strings.TrimRight(string(runes), ". ") + ext
		if out == "" {
			out = "download"
		}
	}
	return out
}

func (d *DownloadManager) uniquePath(dir, name string) string {
	candidate := filepath.Join(dir, name)
	if _, err := os.Stat(candidate); os.IsNotExist(err) {
		return candidate
	}
	ext := filepath.Ext(name)
	stem := strings.TrimSuffix(name, ext)
	for i := 1; i < 1000; i++ {
		candidate = filepath.Join(dir, fmt.Sprintf("%s (%d)%s", stem, i, ext))
		if _, err := os.Stat(candidate); os.IsNotExist(err) {
			return candidate
		}
	}
	return filepath.Join(dir, fmt.Sprintf("%s-%d%s", stem, time.Now().UnixNano(), ext))
}

// Begin creates <dir>/<name> (de-duplicated) and returns {ok,id,path}.
// windowID ties the download to the owning window for AbortForWindow cleanup.
func (d *DownloadManager) Begin(name string, size int64, windowID uint) map[string]any {
	d.mu.Lock()
	if len(d.active) >= maxConcurrentDownloads {
		d.mu.Unlock()
		return map[string]any{"ok": false, "error": "too many concurrent downloads"}
	}
	d.mu.Unlock()
	dir := d.Dir()
	if dir == "" {
		return map[string]any{"ok": false, "error": "download dir unavailable"}
	}
	if size > maxDownloadBytes {
		return map[string]any{"ok": false, "error": "download exceeds 4 GiB limit"}
	}
	clean := sanitizeName(name)
	var f *os.File
	var path string
	var err error
	for attempt := 0; attempt < 4; attempt++ {
		path = d.uniquePath(dir, clean)
		f, err = os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
		if err == nil {
			break
		}
		if !os.IsExist(err) {
			return map[string]any{"ok": false, "error": err.Error()}
		}
	}
	if err != nil {
		return map[string]any{"ok": false, "error": err.Error()}
	}
	var idBytes [8]byte
	_, _ = rand.Read(idBytes[:])
	id := fmt.Sprintf("dl-%x", idBytes)
	d.mu.Lock()
	// Re-check under the lock: the early check races with other Begin calls
	// that may have filled the cap while this file was being created.
	if len(d.active) >= maxConcurrentDownloads {
		d.mu.Unlock()
		_ = f.Close()
		_ = os.Remove(path)
		return map[string]any{"ok": false, "error": "too many concurrent downloads"}
	}
	d.active[id] = &downloadState{path: path, file: f, size: size, lastSeen: d.now(), windowID: windowID}
	if !d.janitorStarted {
		d.janitorStarted = true
		go d.janitor()
	}
	d.mu.Unlock()
	return map[string]any{"ok": true, "id": id, "path": path}
}

// Chunk appends one base64 chunk.
func (d *DownloadManager) Chunk(id, dataBase64 string) map[string]any {
	d.mu.Lock()
	st := d.active[id]
	if st != nil {
		st.lastSeen = d.now()
	}
	d.mu.Unlock()
	if st == nil {
		return map[string]any{"ok": false, "error": "unknown download"}
	}
	if len(dataBase64) > ((maxChunkBytes+2)/3)*4 {
		return map[string]any{"ok": false, "error": "chunk too large"}
	}
	raw, err := base64.StdEncoding.DecodeString(dataBase64)
	if err != nil {
		return map[string]any{"ok": false, "error": "bad chunk encoding"}
	}
	if len(raw) > maxChunkBytes {
		return map[string]any{"ok": false, "error": "chunk too large"}
	}
	// The write and the byte counter must stay inside d.mu: End/Abort/janitor
	// close st.file right after removing the entry, so an unlocked write could
	// interleave with another chunk or race the close and bypass the size cap.
	// d.active[id] == st also rejects chunks for downloads aborted while the
	// base64 payload was being decoded.
	d.mu.Lock()
	if st.completed || d.active[id] != st {
		d.mu.Unlock()
		return map[string]any{"ok": false, "error": "unknown download"}
	}
	if st.written+int64(len(raw)) > maxDownloadBytes {
		delete(d.active, id)
		d.mu.Unlock()
		_ = st.file.Close()
		_ = os.Remove(st.path)
		return map[string]any{"ok": false, "error": "download exceeds 4 GiB limit"}
	}
	if _, err := st.file.Write(raw); err != nil {
		d.mu.Unlock()
		return map[string]any{"ok": false, "error": err.Error()}
	}
	st.written += int64(len(raw))
	d.mu.Unlock()
	return map[string]any{"ok": true}
}

// End closes the file and reports the saved path.
func (d *DownloadManager) End(id string) map[string]any {
	d.mu.Lock()
	st := d.active[id]
	if st != nil {
		delete(d.active, id)
		st.completed = true
	}
	d.mu.Unlock()
	if st == nil {
		return map[string]any{"ok": false, "error": "unknown download"}
	}
	_ = st.file.Close()
	if st.size > 0 && st.written != st.size {
		_ = os.Remove(st.path)
		return map[string]any{
			"ok":    false,
			"error": fmt.Sprintf("incomplete download: %d of %d bytes", st.written, st.size),
		}
	}
	return map[string]any{"ok": true, "path": st.path}
}

// Abort removes a partial download.
func (d *DownloadManager) Abort(id string) map[string]any {
	d.mu.Lock()
	st := d.active[id]
	if st != nil {
		delete(d.active, id)
	}
	d.mu.Unlock()
	if st == nil {
		return map[string]any{"ok": false}
	}
	_ = st.file.Close()
	_ = os.Remove(st.path)
	return map[string]any{"ok": true}
}

// AbortForWindow removes every partial owned by windowID — called when that
// window's bridge token is rotated (page navigated) or invalidated (closed).
// Other windows' downloads are untouched.
func (d *DownloadManager) AbortForWindow(windowID uint) {
	d.mu.Lock()
	var states []*downloadState
	for id, st := range d.active {
		if st.windowID == windowID {
			delete(d.active, id)
			states = append(states, st)
		}
	}
	d.mu.Unlock()
	for _, st := range states {
		_ = st.file.Close()
		_ = os.Remove(st.path)
	}
}

// AbortAll removes every active partial — reserved for real shutdown.
func (d *DownloadManager) AbortAll() {
	d.mu.Lock()
	states := make([]*downloadState, 0, len(d.active))
	for id, st := range d.active {
		delete(d.active, id)
		states = append(states, st)
	}
	d.mu.Unlock()
	for _, st := range states {
		_ = st.file.Close()
		_ = os.Remove(st.path)
	}
}

// janitor removes downloads idle longer than idleTimeout.
func (d *DownloadManager) janitor() {
	for {
		d.mu.Lock()
		interval := d.janitorEvery
		cutoff := d.now().Add(-idleTimeout)
		var stale []*downloadState
		for id, st := range d.active {
			if st.lastSeen.Before(cutoff) {
				delete(d.active, id)
				stale = append(stale, st)
			}
		}
		d.mu.Unlock()
		for _, st := range stale {
			_ = st.file.Close()
			_ = os.Remove(st.path)
		}
		time.Sleep(interval)
	}
}
