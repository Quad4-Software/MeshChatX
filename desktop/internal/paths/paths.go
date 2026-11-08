// Package paths resolves storage roots, user CLI arguments and the backend
// executable location. Mirrors electron/mainHelpers.js.
package paths

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

var ignoredCLIArguments = map[string]bool{
	"--no-sandbox":                  true,
	"--ozone-platform-hint=auto":    true,
	"--disable-gpu":                 true,
	"--disable-gpu-sandbox":         true,
	"--disable-gpu-compositing":     true,
	"--disable-software-rasterizer": true,
	"--enable-logging":              true,
	"--enable-logging=stderr":       true,
}

// GetUserProvidedArguments returns argv[1:] minus known shell noise flags and
// URL-scheme deep links (the backend argparse would reject them).
func GetUserProvidedArguments(argv []string) []string {
	if len(argv) < 2 {
		return nil
	}
	out := make([]string, 0, len(argv)-1)
	for _, arg := range argv[1:] {
		if ignoredCLIArguments[arg] {
			continue
		}
		if hasURLSchemePrefix(arg) {
			continue
		}
		out = append(out, arg)
	}
	return out
}

func hasURLSchemePrefix(arg string) bool {
	idx := strings.Index(arg, "://")
	if idx <= 0 {
		return false
	}
	first := arg[0]
	if !isWordChar(first) {
		return false
	}
	for i := 1; i < idx; i++ {
		c := arg[i]
		if !isWordChar(c) && c != '+' && c != '-' && c != '.' {
			return false
		}
	}
	return true
}

func isWordChar(c byte) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_'
}

// IsProtocolURL reports whether raw uses a deep-link scheme the shell
// forwards to the app page (the desktop entry registers lxmf + rns handlers).
func IsProtocolURL(raw string) bool {
	lower := strings.ToLower(strings.TrimSpace(raw))
	return strings.HasPrefix(lower, "lxmf://") || strings.HasPrefix(lower, "rns://")
}

// FindProtocolUrlArg returns the first lxmf:// or rns:// argument, or "".
func FindProtocolUrlArg(argv []string) string {
	for _, arg := range argv {
		if IsProtocolURL(arg) {
			return arg
		}
	}
	return ""
}

// HasArgvFlag reports whether argv contains "--flag" or "--flag=value".
func HasArgvFlag(argv []string, flagName string) bool {
	prefix := flagName + "="
	for _, arg := range argv {
		if arg == flagName || strings.HasPrefix(arg, prefix) {
			return true
		}
	}
	return false
}

// ParseArgvFlag reads "--flag value" or "--flag=value" forms.
func ParseArgvFlag(argv []string, flagName string) string {
	prefix := flagName + "="
	for _, arg := range argv {
		if strings.HasPrefix(arg, prefix) {
			value := arg[len(prefix):]
			if value == "" {
				return ""
			}
			return value
		}
	}
	for i, arg := range argv {
		if arg == flagName && i+1 < len(argv) {
			value := argv[i+1]
			if value == "" || strings.HasPrefix(value, "--") {
				return ""
			}
			return value
		}
	}
	return ""
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if strings.TrimSpace(v) != "" {
			return strings.TrimSpace(v)
		}
	}
	return ""
}

// ResolvePortableStorageRoots mirrors meshchatx path_utils.resolve_meshchat_data_roots:
// explicit flags/env, then --data-dir/MESHCHAT_DATA_DIR, then Windows portable
// dir, then the user home directory.
func ResolvePortableStorageRoots(argv []string, env map[string]string, homeDir string, isWindows bool, portableExecutableDir string) (storageDir, reticulumConfigDir string) {
	userArgv := GetUserProvidedArguments(argv)

	storageDir = firstNonEmpty(ParseArgvFlag(userArgv, "--storage-dir"), envValue(env, "MESHCHAT_STORAGE_DIR"))
	reticulumConfigDir = firstNonEmpty(ParseArgvFlag(userArgv, "--reticulum-config-dir"), envValue(env, "MESHCHAT_RETICULUM_CONFIG_DIR"))

	dataDir := firstNonEmpty(ParseArgvFlag(userArgv, "--data-dir"), envValue(env, "MESHCHAT_DATA_DIR"))
	if dataDir != "" {
		root := filepath.Clean(dataDir)
		if storageDir == "" {
			storageDir = filepath.Join(root, "storage")
		}
		if reticulumConfigDir == "" {
			reticulumConfigDir = filepath.Join(root, ".reticulum")
		}
	}

	if isWindows && portableExecutableDir != "" {
		if storageDir == "" {
			storageDir = filepath.Join(portableExecutableDir, ".reticulum-meshchatx")
		}
		if reticulumConfigDir == "" {
			reticulumConfigDir = filepath.Join(portableExecutableDir, ".reticulum")
		}
	}

	if storageDir == "" {
		storageDir = filepath.Join(homeDir, ".reticulum-meshchatx")
	}
	if reticulumConfigDir == "" {
		reticulumConfigDir = filepath.Join(homeDir, ".reticulum")
	}
	return storageDir, reticulumConfigDir
}

func envValue(env map[string]string, key string) string {
	if env == nil {
		return ""
	}
	return env[key]
}

// DefaultStorageDir / DefaultReticulumConfigDir resolve the roots for the
// running process (os.Args, os.Environ, user home).
func DefaultStorageDir() string {
	storage, _ := ResolvePortableStorageRoots(os.Args, environMap(), homeDir(), runtime.GOOS == "windows", os.Getenv("PORTABLE_EXECUTABLE_DIR"))
	return storage
}

func DefaultReticulumConfigDir() string {
	_, rns := ResolvePortableStorageRoots(os.Args, environMap(), homeDir(), runtime.GOOS == "windows", os.Getenv("PORTABLE_EXECUTABLE_DIR"))
	return rns
}

func environMap() map[string]string {
	m := make(map[string]string)
	for _, kv := range os.Environ() {
		for i := 0; i < len(kv); i++ {
			if kv[i] == '=' {
				m[kv[:i]] = kv[i+1:]
				break
			}
		}
	}
	return m
}

func homeDir() string {
	if h, err := os.UserHomeDir(); err == nil && h != "" {
		return h
	}
	return "."
}

// ArchSegment maps runtime.GOARCH to the freeze build layout segment.
func ArchSegment() string {
	switch runtime.GOARCH {
	case "arm64":
		return "arm64"
	case "386":
		return "ia32"
	case "arm":
		return "armv7l"
	default:
		return "x64"
	}
}

// PlatformFolder maps runtime.GOOS to the freeze build layout folder.
func PlatformFolder() string {
	switch runtime.GOOS {
	case "windows":
		return "win32"
	case "darwin":
		return "darwin"
	default:
		return "linux"
	}
}

// FindBackendExecutable locates ReticulumMeshChatX next to candidate roots.
// devRepoRoot may be empty; when set it enables <repo>/build/exe lookups.
func FindBackendExecutable(exePath, resourcesPath, devRepoRoot string) (string, []string) {
	exeName := "ReticulumMeshChatX"
	if runtime.GOOS == "windows" {
		exeName += ".exe"
	}
	selfDir := ""
	if exePath != "" {
		selfDir = filepath.Dir(exePath)
	}
	archSeg := PlatformFolder() + "-" + ArchSegment()

	var candidates []string
	add := func(p string) {
		if p != "" {
			candidates = append(candidates, p)
		}
	}

	// MESHCHATX_BACKEND_EXE is an explicit override for development/testing.
	if override := strings.TrimSpace(os.Getenv("MESHCHATX_BACKEND_EXE")); override != "" {
		add(override)
	}
	if selfDir != "" {
		add(filepath.Join(selfDir, "backend", exeName))
		add(filepath.Join(selfDir, "..", "lib", "reticulum-meshchatx", "backend", exeName))
	}
	if resourcesPath != "" {
		add(filepath.Join(resourcesPath, "backend", exeName))
		add(filepath.Join(resourcesPath, archSeg, exeName))
		add(filepath.Join(resourcesPath, "exe", exeName))
	}
	// macOS bundle layout: <bundle>/Contents/Resources/backend/...
	if runtime.GOOS == "darwin" && selfDir != "" {
		bundleResources := filepath.Join(selfDir, "..", "Resources")
		add(filepath.Join(bundleResources, "backend", exeName))
	}
	if devRepoRoot != "" {
		add(filepath.Join(devRepoRoot, "build", "exe", archSeg, exeName))
		add(filepath.Join(devRepoRoot, "build", "exe", exeName))
	}
	if selfDir != "" {
		add(filepath.Join(selfDir, "build", "exe", exeName))
	}

	for _, candidate := range candidates {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			return candidate, candidates
		}
	}
	return "", candidates
}
