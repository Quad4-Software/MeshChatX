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

	file     *os.File
	filePath string
	fileSize int64
}

// openFileStat is indirected so tests can prove stat only happens when the
// log file is opened, not on every line write.
var openFileStat = func(f *os.File) (os.FileInfo, error) {
	return f.Stat()
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
	if err := l.flushPendingLocked(logPath); err != nil {
		l.disableLocked()
		return
	}
	if err := l.appendChunkLocked(logPath, line); err != nil {
		l.disableLocked()
	}
}

func (l *Logger) flushPendingLocked(logPath string) error {
	if len(l.pending) == 0 {
		return nil
	}
	chunk := strings.Join(l.pending, "")
	l.pending = l.pending[:0]
	return l.appendChunkLocked(logPath, chunk)
}

func (l *Logger) appendChunkLocked(logPath, chunk string) error {
	if err := l.ensureFileLocked(logPath); err != nil {
		return err
	}
	if l.fileSize > 0 && l.fileSize+int64(len(chunk)) > LogMaxBytes {
		if err := l.rotateLocked(logPath); err != nil {
			return err
		}
	}
	n, err := l.file.WriteString(chunk)
	l.fileSize += int64(n)
	return err
}

func (l *Logger) ensureFileLocked(logPath string) error {
	if l.file != nil && l.filePath == logPath {
		return nil
	}
	l.closeFileLocked()
	if err := os.MkdirAll(filepath.Dir(logPath), 0o700); err != nil {
		return err
	}
	f, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	info, err := openFileStat(f)
	if err != nil {
		_ = f.Close()
		return err
	}
	l.file = f
	l.filePath = logPath
	l.fileSize = info.Size()
	return nil
}

func (l *Logger) rotateLocked(logPath string) error {
	// Windows cannot rename an open file, and closing first also makes the
	// size counter reset explicit even on Unix-like systems.
	l.closeFileLocked()
	prev := logPath + ".1"
	_ = os.Remove(prev)
	// Rotation is best-effort, as before: if the rename fails, reopening the
	// original path keeps logging alive instead of disabling it.
	_ = os.Rename(logPath, prev)
	return l.ensureFileLocked(logPath)
}

func (l *Logger) disableLocked() {
	l.disabled = true
	l.closeFileLocked()
}

func (l *Logger) closeFileLocked() {
	if l.file != nil {
		_ = l.file.Close()
	}
	l.file = nil
	l.filePath = ""
	l.fileSize = 0
}

// Close releases the lazily opened log file. Writes after Close reopen it,
// so this is safe to use on shutdown without making the logger unusable in
// tests or unusual restart paths.
func (l *Logger) Close() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.closeFileLocked()
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
