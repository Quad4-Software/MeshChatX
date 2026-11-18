// Safe archive extraction for portable update payloads. Guards against
// zip-slip (absolute paths, .. segments, drive letters), caps total
// decompressed bytes, rejects non-regular entry types, and defers symlink
// creation until after every regular file is written so no file write can
// traverse a planted symlink.
package updater

import (
	"archive/tar"
	"archive/zip"
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// maxExtractBytes bounds total decompressed payload bytes (zip-bomb guard);
// artifacts are already capped at 2 GiB compressed on staging.
const maxExtractBytes = int64(4) << 30

// sanitizeRelPath turns an archive entry name into a safe path relative to
// the extraction root. Rejects absolute paths, drive letters and any ".."
// segment; both / and \ are treated as separators.
func sanitizeRelPath(name string) (string, bool) {
	name = strings.ReplaceAll(name, "\\", "/")
	if name == "" || strings.HasPrefix(name, "/") {
		return "", false
	}
	if len(name) >= 2 && name[1] == ':' {
		return "", false
	}
	parts := strings.Split(name, "/")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if p == "" || p == "." {
			continue
		}
		if p == ".." {
			return "", false
		}
		out = append(out, p)
	}
	if len(out) == 0 {
		return "", false
	}
	return filepath.Join(out...), true
}

// insideRoot reports whether p (already cleaned) stays under root.
func insideRoot(root, p string) bool {
	return p == root || strings.HasPrefix(p, root+string(filepath.Separator))
}

type deferredLink struct {
	path   string
	target string
}

// symlinkSafe validates a link target lexically: non-absolute and resolving
// inside the extraction root relative to the link's own directory.
func symlinkSafe(root, linkPath, target string) bool {
	if target == "" || filepath.IsAbs(target) || strings.HasPrefix(target, "/") || strings.HasPrefix(target, "\\") {
		return false
	}
	if len(target) >= 2 && target[1] == ':' {
		return false
	}
	resolved := filepath.Clean(filepath.Join(filepath.Dir(linkPath), target))
	return insideRoot(root, resolved)
}

type extractState struct {
	root     string
	total    int64
	symlinks []deferredLink
}

func (s *extractState) destPath(name string) (string, error) {
	rel, ok := sanitizeRelPath(name)
	if !ok {
		return "", fmt.Errorf("unsafe archive entry %q", name)
	}
	full := filepath.Join(s.root, rel)
	if !insideRoot(s.root, full) {
		return "", fmt.Errorf("archive entry escapes destination %q", name)
	}
	return full, nil
}

func (s *extractState) addDir(path string, mode os.FileMode) error {
	perm := mode.Perm() & 0o777
	if perm == 0 {
		perm = 0o755
	}
	return os.MkdirAll(path, perm)
}

// addFile writes one regular entry, fsyncing before close.
func (s *extractState) addFile(path string, mode os.FileMode, r io.Reader, limit int64) error {
	if s.total > maxExtractBytes {
		return fmt.Errorf("payload exceeds extraction cap")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	perm := mode.Perm() & 0o777
	if perm == 0 {
		// Entries with no mode info (zips made on Windows, or writers that
		// don't store Unix attrs) get the executable bit: a portable app
		// payload must stay runnable after the swap, and extra +x on data
		// files is harmless.
		perm = 0o755
	}
	out, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, perm)
	if err != nil {
		return err
	}
	n, err := io.CopyN(out, r, limit+1)
	s.total += n
	if err == nil || err == io.EOF {
		err = nil
		if n > limit || s.total > maxExtractBytes {
			err = fmt.Errorf("payload exceeds extraction cap")
		}
	}
	if err == nil {
		err = out.Sync()
	}
	if cerr := out.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		_ = os.Remove(path)
	}
	return err
}

// finishSymlinks creates deferred links after all regular content exists.
func (s *extractState) finishSymlinks() error {
	for _, l := range s.symlinks {
		if !symlinkSafe(s.root, l.path, l.target) {
			return fmt.Errorf("unsafe symlink target %q -> %q", l.path, l.target)
		}
		if err := os.MkdirAll(filepath.Dir(l.path), 0o755); err != nil {
			return err
		}
		_ = os.Remove(l.path)
		if err := os.Symlink(l.target, l.path); err != nil {
			return err
		}
	}
	return nil
}

func extractArchive(stagedPath, dest, arch string) error {
	s := &extractState{root: filepath.Clean(dest)}
	var err error
	switch arch {
	case "zip":
		err = extractZip(stagedPath, s)
	case "tar":
		err = extractTar(stagedPath, s, false)
	case "targz":
		err = extractTar(stagedPath, s, true)
	default:
		err = fmt.Errorf("unsupported archive format %q", arch)
	}
	if err != nil {
		return err
	}
	return s.finishSymlinks()
}

func extractZip(path string, s *extractState) error {
	r, err := zip.OpenReader(path)
	if err != nil {
		return err
	}
	defer r.Close()
	for _, f := range r.File {
		mode := f.Mode()
		full, err := s.destPath(f.Name)
		if err != nil {
			return err
		}
		switch {
		case mode.IsDir():
			if err := s.addDir(full, mode); err != nil {
				return err
			}
		case mode&os.ModeSymlink != 0:
			rc, err := f.Open()
			if err != nil {
				return err
			}
			buf, err := io.ReadAll(io.LimitReader(rc, 4096))
			rc.Close()
			if err != nil {
				return err
			}
			s.symlinks = append(s.symlinks, deferredLink{path: full, target: string(buf)})
		case mode.IsRegular():
			rc, err := f.Open()
			if err != nil {
				return err
			}
			limit := maxExtractBytes
			if sz := int64(f.UncompressedSize64); sz >= 0 && sz < limit {
				limit = sz
			}
			err = s.addFile(full, mode, rc, limit)
			rc.Close()
			if err != nil {
				return err
			}
		default:
			return fmt.Errorf("unsupported archive entry type %q", f.Name)
		}
	}
	return nil
}

func extractTar(path string, s *extractState, gzipped bool) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	var r io.Reader = f
	if gzipped {
		gz, err := gzip.NewReader(f)
		if err != nil {
			return err
		}
		defer gz.Close()
		r = gz
	}
	tr := tar.NewReader(r)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		full, err := s.destPath(hdr.Name)
		if err != nil {
			return err
		}
		switch hdr.Typeflag {
		case tar.TypeDir:
			if err := s.addDir(full, hdr.FileInfo().Mode()); err != nil {
				return err
			}
		case tar.TypeReg, tar.TypeRegA:
			limit := hdr.Size
			if limit < 0 || limit > maxExtractBytes {
				limit = maxExtractBytes
			}
			if err := s.addFile(full, hdr.FileInfo().Mode(), tr, limit); err != nil {
				return err
			}
		case tar.TypeSymlink:
			s.symlinks = append(s.symlinks, deferredLink{path: full, target: hdr.Linkname})
		default:
			// Hardlinks, devices, fifos and extensions are refused rather
			// than silently mangled.
			return fmt.Errorf("unsupported tar entry type %d for %q", hdr.Typeflag, hdr.Name)
		}
	}
}
