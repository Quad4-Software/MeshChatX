// Command appimage-stub-backend is a minimal stand-in for the MeshChatX
// Python backend, used only by scripts/ci/test-appimage.sh to prove an
// AppImage can start the shell, spawn WebKit helpers and reach the bridge.
// It is NOT shipped in any package.
//
// Usage: appimage-stub-backend --headless --port 9337 --no-https \
//
//	--storage-dir DIR --reticulum-config-dir DIR
//
// Endpoints:
//
//	/api/v1/status    -> readiness JSON the loading page polls
//	/desktop-bridge.js -> the real shell bridge (read next to the exe)
//	/                 -> probe page exercising window.desktop.appVersion()
//	/result           -> POST sink; appends JSONL to the results file
//
// Results are appended to $STUB_RESULTS_FILE when set, otherwise to
// <storage-dir>/stub-results.jsonl (or $HOME/.meshchatx-stub-results.jsonl).
package main

import (
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func argValue(args []string, name string) string {
	for i, a := range args {
		if a == name && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(a, name+"=") {
			return strings.TrimPrefix(a, name+"=")
		}
	}
	return ""
}

var results *os.File

func main() {
	log.SetPrefix("[stub-backend] ")
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)

	args := os.Args[1:]
	port := argValue(args, "--port")
	if port == "" {
		port = "9337"
	}
	storageDir := argValue(args, "--storage-dir")

	resPath := os.Getenv("STUB_RESULTS_FILE")
	if resPath == "" {
		if storageDir != "" {
			resPath = filepath.Join(storageDir, "stub-results.jsonl")
		} else {
			home, _ := os.UserHomeDir()
			resPath = filepath.Join(home, ".meshchatx-stub-results.jsonl")
		}
	}
	if err := os.MkdirAll(filepath.Dir(resPath), 0o755); err == nil {
		if f, err := os.OpenFile(resPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644); err == nil {
			results = f
			defer f.Close()
		}
	}
	log.Printf("listening on :%s storage=%q results=%q", port, storageDir, resPath)

	exeDir := ""
	if exe, err := os.Executable(); err == nil {
		exeDir = filepath.Dir(exe)
	}
	bridgeJS, _ := os.ReadFile(filepath.Join(exeDir, "desktop-bridge.js"))

	mux := http.NewServeMux()
	mux.HandleFunc("/api/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"status":"ok","stage":"ready","version":"stub","network_ready":true,"ui_ready":true,"app":"stub"}`)
	})
	mux.HandleFunc("/desktop-bridge.js", func(w http.ResponseWriter, r *http.Request) {
		if len(bridgeJS) == 0 {
			http.Error(w, "no bridge", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/javascript")
		w.Write(bridgeJS)
	})
	mux.HandleFunc("/result", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", http.StatusMethodNotAllowed)
			return
		}
		body := make([]byte, 1<<20)
		n, _ := r.Body.Read(body)
		line := strings.TrimSpace(string(body[:n]))
		log.Printf("RESULT %s", line)
		if results != nil {
			results.WriteString(line + "\n")
			results.Sync()
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, probePage)
	})

	ln, err := net.Listen("tcp", net.JoinHostPort("127.0.0.1", port))
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	log.Printf("serving http://127.0.0.1:%s/", port)
	log.Fatal(http.Serve(ln, mux))
}

const probePage = `<!doctype html>
<html><head><meta charset="utf-8"><title>stub-backend</title></head>
<body style="background:#111;color:#eee;font-family:sans-serif;padding:2em">
<pre id="out">probe running…</pre>
<script src="/desktop-bridge.js"></script>
<script>
(async () => {
  const out = {};
  const t = (name, p) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 8000))]).then(
    v => { out[name] = v; }, e => { out[name + 'Err'] = String(e && e.message || e); });
  await t('isSecureContext', Promise.resolve(window.isSecureContext));
  await t('hasDesktop', Promise.resolve(typeof window.desktop !== 'undefined' && window.desktop !== null));
  await t('appVersion', window.desktop ? window.desktop.appVersion() : Promise.reject(new Error('no desktop')));
  await t('statusFetch', fetch('/api/v1/status').then(r => r.text()));
  await t('httpsFetch', fetch('https://example.com/', { mode: 'no-cors', cache: 'no-store' }).then(() => 'sent'));
  await t('localStorage', Promise.resolve((localStorage.setItem('probe', '1'), localStorage.getItem('probe'))));
  // Listen for protocol-link forwards (second-instance lxmf:// hand-off).
  // Every received URL is accumulated and the full list POSTed back so the
  // test can assert delivery even when links arrive after the probe result.
  const protocolLinks = [];
  const postLinks = () => fetch('/result', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ protocolLinks: protocolLinks.slice() }) });
  if (window.desktop && typeof window.desktop.onProtocolLink === 'function') {
    out.protocolListener = 'armed';
    window.desktop.onProtocolLink(function (payload) {
      const url = typeof payload === 'string' ? payload : (payload && payload.url);
      protocolLinks.push(url);
      postLinks().catch(() => {});
    });
  } else {
    out.protocolListener = 'missing';
  }
  out.protocolLinks = protocolLinks.slice();
  document.getElementById('out').textContent = JSON.stringify(out, null, 2);
  document.title = 'STUB ' + (out.appVersion || out.appVersionErr || '?');
  try {
    await fetch('/result', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(out) });
  } catch (e) { console.error('result post failed', e); }
})();
</script>
</body></html>`
