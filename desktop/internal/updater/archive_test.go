package updater

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type countingReader struct {
	r io.Reader
	n *int64
}

func (c *countingReader) Read(p []byte) (int, error) {
	n, err := c.r.Read(p)
	*c.n += int64(n)
	return n, err
}

func TestAddFileClampsToExtractCap(t *testing.T) {
	dir := t.TempDir()
	s := &extractState{root: dir, total: maxExtractBytes - 8}
	var read int64
	src := &countingReader{r: strings.NewReader(strings.Repeat("x", 1<<20)), n: &read}
	err := s.addFile(filepath.Join(dir, "f.bin"), 0o644, src, 1<<20)
	if err == nil {
		t.Fatal("expected extraction cap error")
	}
	if read > 16 {
		t.Fatalf("read %d bytes past the remaining cap", read)
	}
	if s.total > maxExtractBytes+1 {
		t.Fatalf("total overshot cap: %d", s.total)
	}
	if _, err := os.Stat(filepath.Join(dir, "f.bin")); !os.IsNotExist(err) {
		t.Fatal("partial file left behind")
	}
}
