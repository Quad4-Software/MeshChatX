// Package logger ports electron/safeConsole.js: durable append to
// <storage>/logs/meshchatx.log with 5 MiB rotation, plus best-effort stdout
// mirroring only when attached to a TTY (or forced via env).
package logger

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const (
	LogPrefix   = "[wails] "
	LogMaxBytes = 5 * 1024 * 1024
)

type Logger struct {
	mu       sync.Mutex
	getDir   func() string
	disabled bool
	pending  []string
}

func New(getLogsDir func() string) *Logger {
	return &Logger{getDir: getLogsDir}
}

func (l *Logger) logPath() string {
	if l.getDir == nil {
		return ""
	}
	dir := l.getDir()
	if dir == "" {
		return ""
	}
	return filepath.Join(dir, "meshchatx.log")
}

func formatLine(message string) string {
	text := strings.TrimRight(fmt.Sprint(message), " \t\r\n")
	return fmt.Sprintf("%s %s%s\n", time.Now().UTC().Format(time.RFC3339Nano), LogPrefix, text)
}

func rotateIfNeeded(logPath string) {
	info, err := os.Stat(logPath)
	if err != nil {
		return
	}
	if info.Size() <= LogMaxBytes {
		return
	}
	prev := logPath + ".1"
	_ = os.Remove(prev)
	_ = os.Rename(logPath, prev)
}

// Write appends a durable log line and mirrors to stdout when appropriate.
func (l *Logger) Write(message any) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.writeToFile(message)
	if shouldMirrorStdout() {
		fmt.Println(message)
	}
}

func (l *Logger) writeToFile(message any) {
	if l.disabled {
		return
	}
	line := formatLine(fmt.Sprint(message))
	logPath := l.logPath()
	if logPath == "" {
		l.pending = append(l.pending, line)
		return
	}
	l.flushPendingLocked(logPath)
	if err := l.appendChunk(logPath, line); err != nil {
		l.disabled = true
	}
}

func (l *Logger) flushPendingLocked(logPath string) {
	if len(l.pending) == 0 {
		return
	}
	chunk := strings.Join(l.pending, "")
	l.pending = l.pending[:0]
	if err := l.appendChunk(logPath, chunk); err != nil {
		l.disabled = true
	}
}

func (l *Logger) appendChunk(logPath, chunk string) error {
	rotateIfNeeded(logPath)
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		return err
	}
	f, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(chunk)
	return err
}

func shouldMirrorStdout() bool {
	if os.Getenv("MESHCHAT_DISABLE_STDOUT_LOG") == "1" {
		return false
	}
	if os.Getenv("MESHCHAT_FORCE_STDOUT_LOG") == "1" {
		return true
	}
	return isTTY(os.Stdout)
}

func isTTY(f *os.File) bool {
	fi, err := f.Stat()
	if err != nil {
		return false
	}
	return fi.Mode()&os.ModeCharDevice != 0
}
