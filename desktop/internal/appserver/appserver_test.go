package appserver

import (
	"io"
	"io/fs"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
)

func testFS() fs.FS {
	return fstest.MapFS{
		"loading.html":      {Data: []byte("<html>loading</html>")},
		"crash.html":        {Data: []byte("<html>crash</html>")},
		"desktop-bridge.js": {Data: []byte("// bridge")},
		"assets/css/x.css":  {Data: []byte("body{}")},
	}
}

func startTestServer(t *testing.T, upstream *url.URL) *Server {
	t.Helper()
	s, err := Start(testFS(), upstream)
	if err != nil {
		t.Fatalf("Start: %v", err)
	}
	t.Cleanup(s.Stop)
	return s
}

func TestServeShellAssets(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("shell path should not hit upstream")
	}))
	defer up.Close()
	u, _ := url.Parse(up.URL)
	s := startTestServer(t, u)

	base := "http://" + s.Addr()
	for path, want := range map[string]string{
		"/__shell/loading.html":      "<html>loading</html>",
		"/__shell/crash.html":        "<html>crash</html>",
		"/__shell/desktop-bridge.js": "// bridge",
		"/__shell/assets/css/x.css":  "body{}",
	} {
		resp, err := http.Get(base + path)
		if err != nil {
			t.Fatalf("GET %s: %v", path, err)
		}
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		if resp.StatusCode != 200 || string(body) != want {
			t.Fatalf("GET %s = %d %q", path, resp.StatusCode, body)
		}
		if ct := resp.Header.Get("Content-Type"); !strings.Contains(ct, "text/html") && !strings.Contains(ct, "css") && !strings.Contains(ct, "javascript") {
			t.Fatalf("GET %s content-type %q", path, ct)
		}
	}
}

func TestServeShellRejectsTraversalAndMethods(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	defer up.Close()
	u, _ := url.Parse(up.URL)
	s := startTestServer(t, u)
	base := "http://" + s.Addr()

	for _, p := range []string{
		"/__shell/../secret",
		"/__shell/..%2fsecret",
		"/__shell/assets/../../etc/passwd",
		"/__shell/desktop-bridge.js/../loading.html",
		"/__shell/",
		"/__shell/nonexistent.js",
	} {
		resp, err := http.Get(base + p)
		if err != nil {
			t.Fatalf("GET %s: %v", p, err)
		}
		resp.Body.Close()
		if resp.StatusCode != 404 && resp.StatusCode != 400 {
			t.Fatalf("GET %s = %d, want 404/400", p, resp.StatusCode)
		}
	}

	req, _ := http.NewRequest("POST", base+"/__shell/loading.html", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("POST /__shell = %d, want 405", resp.StatusCode)
	}
}

func TestHostRebindingRejected(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("proxied"))
	}))
	defer up.Close()
	u, _ := url.Parse(up.URL)
	s := startTestServer(t, u)

	for _, host := range []string{"evil.example", "127.0.0.1:1", "localhost:9999"} {
		req, _ := http.NewRequest("GET", "http://"+s.Addr()+"/api/v1/status", nil)
		req.Host = host
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("GET host=%s: %v", host, err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusMisdirectedRequest {
			t.Fatalf("Host %q = %d, want 421", host, resp.StatusCode)
		}
	}
}

func TestProxyPassesAndRewrites(t *testing.T) {
	var gotHost, gotOrigin, gotReferer string
	var gotCookie string
	up := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotHost = r.Host
		gotOrigin = r.Header.Get("Origin")
		gotReferer = r.Header.Get("Referer")
		gotCookie = r.Header.Get("Cookie")
		w.Header().Add("Set-Cookie", "sess=abc; Secure; Path=/; HttpOnly")
		w.Write([]byte("backend-ok"))
	}))
	defer up.Close()
	u, _ := url.Parse(up.URL)
	s := startTestServer(t, u)

	req, _ := http.NewRequest("GET", "http://"+s.Addr()+"/api/v1/status", nil)
	req.Header.Set("Cookie", "sess=abc")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != 200 || string(body) != "backend-ok" {
		t.Fatalf("proxy = %d %q", resp.StatusCode, body)
	}
	if gotHost != u.Host {
		t.Fatalf("upstream Host = %q, want %q", gotHost, u.Host)
	}
	if !strings.Contains(gotCookie, "sess=abc") {
		t.Fatalf("cookie not forwarded: %q", gotCookie)
	}
	setCookie := resp.Header.Get("Set-Cookie")
	if strings.Contains(setCookie, "Secure") {
		t.Fatalf("Set-Cookie still Secure: %q", setCookie)
	}
	_ = gotOrigin
	_ = gotReferer
}

func TestProxyOriginRefererRewrite(t *testing.T) {
	var gotOrigin, gotReferer string
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotOrigin = r.Header.Get("Origin")
		gotReferer = r.Header.Get("Referer")
		w.Write([]byte("ok"))
	}))
	defer up.Close()
	u, _ := url.Parse(up.URL)
	s := startTestServer(t, u)

	req, _ := http.NewRequest("GET", "http://"+s.Addr()+"/x", nil)
	req.Header.Set("Origin", "http://"+s.Addr())
	req.Header.Set("Referer", "http://"+s.Addr()+"/page")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if gotOrigin != "http://"+u.Host {
		t.Fatalf("Origin rewritten to %q, want %q", gotOrigin, "http://"+u.Host)
	}
	if gotReferer != "http://"+u.Host+"/page" {
		t.Fatalf("Referer rewritten to %q", gotReferer)
	}
}

func TestUpstreamDownRedirectsHTMLNavigation(t *testing.T) {
	// Upstream that is guaranteed dead: pick a listener then close it.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	dead := "http://" + ln.Addr().String()
	_ = ln.Close()
	u, _ := url.Parse(dead)
	s := startTestServer(t, u)

	// Top-level HTML navigation -> redirect to shell loading page.
	req, _ := http.NewRequest("GET", "http://"+s.Addr()+"/?nocache=1&theme=dark", nil)
	req.Header.Set("Accept", "text/html,application/xhtml+xml")
	client := &http.Client{CheckRedirect: func(req *http.Request, via []*http.Request) error {
		return http.ErrUseLastResponse
	}}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusFound {
		t.Fatalf("HTML nav = %d, want 302", resp.StatusCode)
	}
	loc := resp.Header.Get("Location")
	if !strings.Contains(loc, "/__shell/loading.html") || !strings.Contains(loc, "startup_error=backend_unreachable") || !strings.Contains(loc, "theme=dark") {
		t.Fatalf("redirect Location = %q", loc)
	}

	// Non-HTML request -> plain 502, no redirect.
	resp2, err := http.Get("http://" + s.Addr() + "/api/v1/status")
	if err != nil {
		t.Fatal(err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != http.StatusBadGateway {
		t.Fatalf("API = %d, want 502", resp2.StatusCode)
	}
}

func TestRegisteredPortIsTrusted(t *testing.T) {
	s := startTestServer(t, mustURL(t, "http://127.0.0.1:1"))
	_, port, _ := net.SplitHostPort(s.Addr())
	if !security.IsLocalBackendURL("http://127.0.0.1:" + port + "/api") {
		t.Fatalf("app-server origin not trusted")
	}
	if security.IsLocalBackendURL("http://127.0.0.1:1/api") {
		t.Fatal("random port must not be trusted")
	}
}

func TestStripSecureCookieAttr(t *testing.T) {
	in := "sess=abc; Secure; Path=/; HttpOnly; Partitioned"
	got := stripSecureCookieAttr(in)
	want := "sess=abc; Path=/; HttpOnly; Partitioned"
	if got != want {
		t.Fatalf("stripSecureCookieAttr = %q, want %q", got, want)
	}
	// case-insensitive, no Secure attr, no attrs at all
	if got := stripSecureCookieAttr("a=b; secure"); got != "a=b" {
		t.Fatalf("lowercase secure: %q", got)
	}
	if got := stripSecureCookieAttr("a=b"); got != "a=b" {
		t.Fatalf("plain cookie: %q", got)
	}
	// a cookie *named* Secure must survive (only bare attrs are stripped)
	if got := stripSecureCookieAttr("Secure=1; Path=/"); got != "Secure=1; Path=/" {
		t.Fatalf("cookie named Secure mangled: %q", got)
	}
}

func TestRewriteBridgeOrigin(t *testing.T) {
	upstream, _ := url.Parse("http://127.0.0.1:9337")
	bridgeAddr := "127.0.0.1:9338"

	got := rewriteBridgeOrigin("http://127.0.0.1:9338/page?next=127.0.0.1:9338", bridgeAddr, upstream)
	want := "http://127.0.0.1:9337/page?next=127.0.0.1:9338"
	if got != want {
		t.Fatalf("referer rewrite = %q, want %q", got, want)
	}
	if got := rewriteBridgeOrigin("http://127.0.0.1:9338", bridgeAddr, upstream); got != "http://127.0.0.1:9337" {
		t.Fatalf("origin rewrite = %q", got)
	}
	// non-matching authority untouched, including lookalikes
	for _, v := range []string{
		"null",
		"http://127.0.0.1:9338.evil.com/x",
		"http://127.0.0.1:9999/x",
		"https://example.com/?q=127.0.0.1:9338",
	} {
		if got := rewriteBridgeOrigin(v, bridgeAddr, upstream); got != v {
			t.Fatalf("%q rewritten to %q", v, got)
		}
	}
}

func mustURL(t *testing.T, raw string) *url.URL {
	t.Helper()
	u, err := url.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	return u
}
