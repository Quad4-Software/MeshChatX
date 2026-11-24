package backendproc

import (
	"bufio"
	"io"
	"strings"
	"testing"
)

func TestPumpReadLineLongLine(t *testing.T) {
	big := strings.Repeat("x", 3<<20)
	r := bufio.NewReaderSize(strings.NewReader(big+"\nnormal\n"), pumpLineCap+1)
	line, err := pumpReadLine(r)
	if err != nil {
		t.Fatal(err)
	}
	if len(line) != pumpLineCap+len("...[truncated]") {
		t.Fatalf("len=%d", len(line))
	}
	if !strings.HasSuffix(line, "...[truncated]") {
		t.Fatal("missing truncation marker")
	}
	if line[:pumpLineCap] != big[:pumpLineCap] {
		t.Fatal("kept bytes are not the line prefix")
	}
	line2, err := pumpReadLine(r)
	if err != nil || line2 != "normal" {
		t.Fatalf("second line: %q err %v", line2, err)
	}
	if _, err := pumpReadLine(r); err != io.EOF {
		t.Fatalf("expected EOF, got %v", err)
	}
}

func TestPumpReadLineExactCap(t *testing.T) {
	line := strings.Repeat("y", pumpLineCap)
	r := bufio.NewReaderSize(strings.NewReader(line+"\n"), pumpLineCap+1)
	got, err := pumpReadLine(r)
	if err != nil {
		t.Fatal(err)
	}
	if got != line {
		t.Fatalf("exact-cap line truncated: len=%d", len(got))
	}
}

func TestPumpReadLineUnterminatedTail(t *testing.T) {
	r := bufio.NewReaderSize(strings.NewReader("tail-no-newline"), pumpLineCap+1)
	got, err := pumpReadLine(r)
	if err != io.EOF || got != "tail-no-newline" {
		t.Fatalf("got %q err %v", got, err)
	}
}
