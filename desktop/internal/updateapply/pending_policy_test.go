package updateapply

import (
	"os"
	"path/filepath"
	"testing"
)

func writeMarkerJSON(t *testing.T, dir, body string) {
	t.Helper()
	upd := filepath.Join(dir, "updates")
	if err := os.MkdirAll(upd, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(upd, "pending.json"), []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestPendingApplyPolicy(t *testing.T) {
	dir := t.TempDir()
	if got := PendingApplyPolicy(dir); got != "" {
		t.Fatalf("expected empty policy, got %q", got)
	}
	writeMarkerJSON(t, dir, `{"apply_policy":"on_restart","file":"a.AppImage"}`)
	if got := PendingApplyPolicy(dir); got != "on_restart" {
		t.Fatalf("expected on_restart, got %q", got)
	}
	writeMarkerJSON(t, dir, `{"apply_policy":"manual","file":"a.AppImage"}`)
	if got := PendingApplyPolicy(dir); got != "manual" {
		t.Fatalf("expected manual, got %q", got)
	}
	writeMarkerJSON(t, dir, `{"file":"a.AppImage"}`)
	if got := PendingApplyPolicy(dir); got != "" {
		t.Fatalf("expected empty for missing policy, got %q", got)
	}
	writeMarkerJSON(t, dir, `not json`)
	if got := PendingApplyPolicy(dir); got != "" {
		t.Fatalf("expected empty for corrupt marker, got %q", got)
	}
}
