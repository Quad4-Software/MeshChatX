// Package appserver is the shell's loopback front door. It serves the
// embedded shell pages under /__shell/ and reverse-proxies everything else
// to the Python backend, so the loading page and the app share ONE origin
// (and therefore one WebKit web process — no retained process after the
// loading -> app navigation).
//
// It listens on 127.0.0.1:9338 and falls back to a random free loopback
// port when 9338 is busy. The bound port is registered with
// internal/security so origin checks accept it at runtime.
package appserver

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"log"
	"mime"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/Quad4-Software/MeshChatX/desktop/internal/security"
)

const preferredAddr = "127.0.0.1:9338"

// Server is a running app server.
type Server struct {
	mu       sync.Mutex
	ln       net.Listener
	httpSrv  *http.Server
	upstream *url.URL
	shellFS  fs.FS
	// shutdownStatusFile is the JSON file the backend updates while it
	// tears down. The shutdown page polls it for live step text.
	shutdownStatusFile string
	addr               string // "127.0.0.1:PORT"
	port               string
	origin             string // "http://127.0.0.1:PORT"
}

// Addr returns the bound listen address ("127.0.0.1:PORT").
func (s *Server) Addr() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.addr
}

// Origin returns the shell origin ("http://127.0.0.1:PORT").
func (s *Server) Origin() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.origin
}

// Upstream returns the backend URL this server proxies to.
func (s *Server) Upstream() *url.URL {
	return s.upstream
}

// SetShutdownStatusFile points the server at the backend's shutdown
// status JSON so /__shell/shutdown-status can serve it.
func (s *Server) SetShutdownStatusFile(path string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.shutdownStatusFile = path
}

// Stop shuts the server down and drops its trusted-port registration so a
// later unrelated listener on the same port doesn't inherit shell trust.
func (s *Server) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.httpSrv != nil {
		_ = s.httpSrv.Close()
	}
	security.UnregisterTrustedBackendPort(s.port)
}

func isLoopbackHost(host string) bool {
	h := strings.TrimSuffix(strings.ToLower(host), ".")
	if h == "localhost" {
		return true
	}
	ip := net.ParseIP(strings.Trim(h, "[]"))
	return ip != nil && ip.IsLoopback()
}

// Start binds the preferred loopback port (falling back to a random free
// one), registers the port as trusted and serves shell+proxy until Stop.
// shellFS must be rooted at the embedded shell directory (paths like
// "loading.html", "assets/css/...").
func Start(shellFS fs.FS, upstream *url.URL) (*Server, error) {
	if upstream == nil || upstream.Host == "" {
		return nil, fmt.Errorf("appserver: upstream URL required")
	}
	if !isLoopbackHost(upstream.Hostname()) {
		return nil, fmt.Errorf("appserver: refusing non-loopback upstream %q", upstream.Host)
	}

	ln, err := net.Listen("tcp", preferredAddr)
	if err != nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			return nil, err
		}
	}
	_, portStr, err := net.SplitHostPort(ln.Addr().String())
	if err != nil {
		_ = ln.Close()
		return nil, err
	}
	if _, err := strconv.Atoi(portStr); err != nil {
		_ = ln.Close()
		return nil, fmt.Errorf("appserver: invalid bound port %q", portStr)
	}
	security.RegisterTrustedBackendPort(portStr)

	s := &Server{
		ln:       ln,
		upstream: upstream,
		shellFS:  shellFS,
		addr:     ln.Addr().String(),
		port:     portStr,
		origin:   "http://" + ln.Addr().String(),
	}
	s.httpSrv = &http.Server{
		Handler:           s.handler(),
		ReadHeaderTimeout: 10 * time.Second,
	}
	go func() {
		if err := s.httpSrv.Serve(ln); err != nil && err != http.ErrServerClosed {
			log.Printf("appserver: serve error: %v", err)
		}
	}()
	return s, nil
}

// shellCSP guards the embedded shell pages. They are static trusted assets
// whose markup carries inline <script> blocks, so script-src must allow
// 'unsafe-inline' here; all dynamic content is rendered via textContent.
const shellCSP = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:*; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"

// fallbackCSP mirrors the Electron webRequest.onHeadersReceived policy,
// applied to proxied HTML responses that carry no CSP of their own.
const fallbackCSP = "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://*.cartocdn.com https://tiles.openfreemap.org https://*.openfreemap.org; font-src 'self' data: https://tiles.openfreemap.org https://*.openfreemap.org; connect-src 'self' http://127.0.0.1:9337 https://127.0.0.1:9337 http://localhost:9337 https://localhost:9337 ws://127.0.0.1:* wss://127.0.0.1:* ws://localhost:* wss://localhost:* blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://nominatim.openstreetmap.org https://github.com https://*.cartocdn.com https://tiles.openfreemap.org https://*.openfreemap.org; media-src 'self' blob:; worker-src 'self' blob:; frame-src 'self'; object-src 'none'; base-uri 'self'"

// hostAllowed enforces DNS-rebinding protection: only literal loopback
// Host headers for THIS server's port are served.
func (s *Server) hostAllowed(r *http.Request) bool {
	host := r.Host
	var port string
	if h, p, err := net.SplitHostPort(host); err == nil {
		host, port = h, p
	}
	host = strings.TrimSuffix(strings.ToLower(host), ".")
	switch host {
	case "127.0.0.1", "localhost", "::1", "[::1]":
	default:
		return false
	}
	// A Host header carrying a port must name THIS server's port.
	if port != "" && port != s.port {
		return false
	}
	return true
}

func (s *Server) handler() http.Handler {
	proxy := s.newProxy()
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !s.hostAllowed(r) {
			http.Error(w, "misdirected request", http.StatusMisdirectedRequest)
			return
		}
		if p := r.URL.Path; p == "/__shell/shutdown-status" {
			s.serveShutdownStatus(w, r)
			return
		}
		if p := r.URL.Path; p == "/__shell" || strings.HasPrefix(p, "/__shell/") {
			s.serveShell(w, r)
			return
		}
		proxy.ServeHTTP(w, r)
	})
}

// serveShell serves embedded shell assets. GET/HEAD only, no directory
// listing, no path traversal (explicit ".." rejection + fs.ValidPath).
func (s *Server) serveShell(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	rel := strings.TrimPrefix(r.URL.Path, "/__shell")
	rel = strings.TrimPrefix(rel, "/")
	if rel == "" {
		rel = "index.html"
	}
	if strings.Contains(rel, "..") || strings.ContainsRune(rel, '\\') || strings.HasPrefix(rel, "/") {
		http.NotFound(w, r)
		return
	}
	name := path.Clean("/" + rel)
	name = strings.TrimPrefix(name, "/")
	if name == "" || !fs.ValidPath(name) {
		http.NotFound(w, r)
		return
	}
	info, err := fs.Stat(s.shellFS, name)
	if err != nil || !info.Mode().IsRegular() {
		http.NotFound(w, r)
		return
	}
	if ct := mime.TypeByExtension(path.Ext(name)); ct != "" {
		w.Header().Set("Content-Type", ct)
	}
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Content-Security-Policy", shellCSP)
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("X-Frame-Options", "DENY")
	if r.Method == http.MethodHead {
		w.WriteHeader(http.StatusOK)
		return
	}
	f, err := s.shellFS.Open(name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()
	_, _ = io.Copy(w, f)
}

// serveShutdownStatus returns the backend's last written shutdown step, or
// a waiting placeholder before the file exists and after it is gone.
func (s *Server) serveShutdownStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.mu.Lock()
	statusPath := s.shutdownStatusFile
	s.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-cache")
	data := []byte(`{"step":"waiting","detail":""}`)
	if statusPath != "" {
		if raw, err := os.ReadFile(statusPath); err == nil && json.Valid(raw) {
			data = raw
		}
	}
	w.WriteHeader(http.StatusOK)
	if r.Method == http.MethodGet {
		_, _ = w.Write(data)
	}
}

// rewriteBridgeOrigin rewrites an Origin/Referer header whose URL authority is
// this server's loopback address to the upstream backend address. Only the
// parsed host is compared — a bare substring replace could mangle the
// "127.0.0.1:PORT" text appearing inside a path, query or userinfo.
func rewriteBridgeOrigin(v, bridgeAddr string, upstream *url.URL) string {
	u, err := url.Parse(v)
	if err != nil || u.Host == "" {
		return v
	}
	if !strings.EqualFold(u.Host, bridgeAddr) {
		return v
	}
	u.Host = upstream.Host
	return u.String()
}

// stripSecureCookieAttr removes only the Secure attribute from a raw
// Set-Cookie header value. Re-serializing via http.Cookie would drop
// non-standard attributes the backend may set (e.g. Partitioned).
func stripSecureCookieAttr(setCookie string) string {
	parts := strings.Split(setCookie, ";")
	kept := parts[:0]
	for _, p := range parts {
		if strings.EqualFold(strings.TrimSpace(p), "secure") {
			continue
		}
		kept = append(kept, p)
	}
	return strings.Join(kept, ";")
}

// newProxy reverse-proxies to the backend upstream, rewriting Host/Origin/
// Referer and relaxing Secure cookies (same rules as the old TLS bridge).
// When the upstream is unreachable, top-level HTML navigations are sent back
// to the shell loading page instead of a bare 502.
func (s *Server) newProxy() *httputil.ReverseProxy {
	upstream := s.upstream
	bridgeAddr := s.Addr()
	proxy := httputil.NewSingleHostReverseProxy(upstream)
	proxy.Transport = &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, // loopback upstream only
	}
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = upstream.Scheme
		req.URL.Host = upstream.Host
		// The browser-visible origin travels in X-Forwarded-Host so the
		// backend can stamp the real app-server port into the opaque
		// crash-tab CSP. Set always overwrites a client-supplied value.
		req.Header.Set("X-Forwarded-Host", req.Host)
		req.Host = upstream.Host
		for _, h := range []string{"Origin", "Referer"} {
			if v := req.Header.Get(h); v != "" {
				req.Header.Set(h, rewriteBridgeOrigin(v, bridgeAddr, upstream))
			}
		}
	}
	proxy.ModifyResponse = func(resp *http.Response) error {
		if resp.Header.Get("X-Content-Type-Options") == "" {
			resp.Header.Set("X-Content-Type-Options", "nosniff")
		}
		if resp.Header.Get("Referrer-Policy") == "" {
			resp.Header.Set("Referrer-Policy", "no-referrer")
		}
		if resp.Header.Get("Content-Security-Policy") == "" &&
			resp.Header.Get("content-security-policy") == "" &&
			strings.Contains(resp.Header.Get("Content-Type"), "text/html") {
			resp.Header.Set("Content-Security-Policy", fallbackCSP)
		}
		cookies := resp.Header.Values("Set-Cookie")
		if len(cookies) == 0 {
			return nil
		}
		resp.Header.Del("Set-Cookie")
		for _, c := range cookies {
			resp.Header.Add("Set-Cookie", stripSecureCookieAttr(c))
		}
		return nil
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		// Top-level page navigations bounce back to the shell loading page so
		// the user sees the startup diagnostics instead of a dead proxy error.
		// /__shell paths never reach here (handled before the proxy).
		if r.Method == http.MethodGet && strings.Contains(r.Header.Get("Accept"), "text/html") {
			theme := r.URL.Query().Get("theme")
			target := "/__shell/loading.html?startup_error=backend_unreachable"
			if theme == "dark" || theme == "light" {
				target += "&theme=" + theme
			}
			http.Redirect(w, r, target, http.StatusFound)
			return
		}
		http.Error(w, "backend unreachable", http.StatusBadGateway)
	}
	return proxy
}
