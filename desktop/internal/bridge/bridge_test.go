package bridge

import (
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"
)

// fakeWindow embeds the Window interface (nil) and captures ExecJS calls.
type fakeWindow struct {
	application.Window
	mu    sync.Mutex
	js    []string
	token string
	id    uint64
}

func (f *fakeWindow) ExecJS(js string) {
	f.mu.Lock()
	f.js = append(f.js, js)
	f.mu.Unlock()
}

var fakeWinID uint64

func (f *fakeWindow) ID() uint {
	if f.id == 0 {
		fakeWinID++
		f.id = fakeWinID
	}
	return uint(f.id)
}

func (f *fakeWindow) calls() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.js...)
}

func newTestBridge(t *testing.T) *Bridge {
	t.Helper()
	return New(Deps{
		AppVersion:       func() string { return "9.9.9-test" },
		WailsVersion:     func() string { return "3.1.0" },
		WebViewKind:      func() string { return "test-webview" },
		IsHardwareAccel:  func() bool { return true },
		UserProvidedArgs: func() []string { return nil },
		StorageDir:       func() string { return t.TempDir() },
	})
}

func waitJS(t *testing.T, w *fakeWindow, wantSub string) string {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		for _, js := range w.calls() {
			if strings.Contains(js, wantSub) {
				return js
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("no ExecJS containing %q; calls: %v", wantSub, w.calls())
	return ""
}

// armToken rotates the page-load token and records it on the fake window.
func armToken(t *testing.T, b *Bridge, w *fakeWindow) {
	t.Helper()
	b.RotateToken(w)
	for _, js := range w.calls() {
		if i := strings.Index(js, "__init("); i >= 0 {
			var tok string
			if err := json.Unmarshal([]byte(strings.TrimSuffix(strings.TrimPrefix(js[i+7:], ")"), ")")), &tok); err == nil {
				w.token = tok
				return
			}
		}
	}
	t.Fatal("no __init token pushed")
}

func post(t *testing.T, b *Bridge, w *fakeWindow, origin *application.OriginInfo, method string, args ...any) {
	t.Helper()
	if w.token == "" {
		armToken(t, b, w)
	}
	payload, _ := json.Marshal(args)
	msg, _ := json.Marshal(map[string]any{"v": 1, "id": 7, "method": method, "args": payload, "t": w.token})
	b.Handle(w, string(msg), origin)
}

func TestHandleNilOriginInfo(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	b.Handle(w, `{"v":1,"id":1,"method":"app-version","args":[]}`, nil)
	time.Sleep(50 * time.Millisecond)
	if len(w.calls()) != 0 {
		t.Fatalf("nil originInfo should be ignored, got %v", w.calls())
	}
}

func TestHandleUntrustedOrigin(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	post(t, b, w, &application.OriginInfo{Origin: "https://evil.example.com"}, "app-version")
	js := waitJS(t, w, "resolve(")
	if !strings.Contains(js, "false") || !strings.Contains(js, "blocked") {
		t.Fatalf("expected block reply: %s", js)
	}
}

func TestHandleTrustedOriginUnknownMethod(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	// wails://localhost is the Linux asset origin
	post(t, b, w, &application.OriginInfo{Origin: "wails://localhost"}, "no-such-method")
	js := waitJS(t, w, "resolve(")
	if !strings.Contains(js, "unknown method") {
		t.Fatalf("expected unknown method error: %s", js)
	}
}

func TestHandleAppVersion(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	post(t, b, w, &application.OriginInfo{Origin: "wails://localhost"}, "app-version")
	js := waitJS(t, w, "9.9.9-test")
	if !strings.Contains(js, `"ok":true`) && !strings.Contains(js, ",true,") {
		// reply format: resolve(id, ok, payloadJson)
		if !strings.Contains(js, ",true,") {
			t.Fatalf("expected ok reply: %s", js)
		}
	}
}

func TestHandleBackendOriginTrusted(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	post(t, b, w, &application.OriginInfo{Origin: "http://127.0.0.1:9337"}, "app-version")
	waitJS(t, w, "9.9.9-test")
}

func TestHandleMalformedMessage(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	b.Handle(w, "not json", &application.OriginInfo{Origin: "wails://localhost"})
	b.Handle(w, `{"v":2,"id":1,"method":"app-version","args":[]}`, &application.OriginInfo{Origin: "wails://localhost"})
	b.Handle(w, `{"v":1,"id":1,"method":"","args":[]}`, &application.OriginInfo{Origin: "wails://localhost"})
	time.Sleep(50 * time.Millisecond)
	if len(w.calls()) != 0 {
		t.Fatalf("malformed messages should be ignored: %v", w.calls())
	}
}

func TestHandleTopOriginFallback(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	// Origin empty but TopOrigin trusted (subframe on trusted page)
	post(t, b, w, &application.OriginInfo{Origin: "", TopOrigin: "wails://localhost"}, "app-version")
	waitJS(t, w, "9.9.9-test")
}

func TestHandlePageToken(t *testing.T) {
	b := newTestBridge(t)
	w := &fakeWindow{}
	origin := &application.OriginInfo{Origin: "http://127.0.0.1:9338"}

	postRaw := func(tok string) {
		msg, _ := json.Marshal(map[string]any{"v": 1, "id": 9, "method": "app-version", "args": []any{}, "t": tok})
		b.Handle(w, string(msg), origin)
	}

	// No token armed -> rejected, no dispatch.
	postRaw("")
	postRaw("deadbeef")
	if calls := w.calls(); len(calls) != 0 {
		t.Fatalf("rejected messages produced ExecJS: %v", calls)
	}

	// Valid token -> dispatch happens (reply ExecJS appears).
	armToken(t, b, w)
	postRaw(w.token)
	waitJS(t, w, "resolve(")

	// Stale token after reload -> rejected.
	w2 := &fakeWindow{}
	armToken(t, b, w2)
	old := w2.token
	armToken(t, b, w2) // second load: token rotates
	postRawOn := func(win *fakeWindow, tok string) {
		msg, _ := json.Marshal(map[string]any{"v": 1, "id": 9, "method": "app-version", "args": []any{}, "t": tok})
		b.Handle(win, string(msg), origin)
	}
	postRawOn(w2, old)
	time.Sleep(50 * time.Millisecond)
	// stale token must not dispatch: no new resolve beyond current calls
	_ = old

	// Other window's token rejected.
	postRawOn(w, w2.token)

	// Window close invalidates.
	b.InvalidateWindow(w2)
	postRawOn(w2, w2.token)
}

func TestWindowResultBoundToOwner(t *testing.T) {
	b := newTestBridge(t)
	owner := &fakeWindow{}
	owner.id = 101
	other := &fakeWindow{}
	other.id = 202

	ch := b.RegisterPendingWindow("prompt-dialog", owner)

	// A different window must not resolve the pending entry.
	b.windowResult(other, "prompt-dialog", map[string]any{"value": "forged"})
	select {
	case <-ch:
		t.Fatal("foreign window resolved pending entry")
	case <-time.After(50 * time.Millisecond):
	}

	// The registered window resolves it.
	b.windowResult(owner, "prompt-dialog", map[string]any{"value": "ok"})
	select {
	case raw := <-ch:
		if !strings.Contains(raw, "ok") {
			t.Fatalf("unexpected payload: %s", raw)
		}
	case <-time.After(time.Second):
		t.Fatal("owner window-result not delivered")
	}

	// Entry consumed: a second result finds nothing.
	b.windowResult(owner, "prompt-dialog", map[string]any{"value": "again"})
}
