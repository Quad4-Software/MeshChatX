//go:build !windows

package backendproc

func killOrphanBackendPids(exclude map[int]bool, exePath string) int {
	pids := listUnixBackendPids(exclude, exePath)
	return KillUnixPids(pids)
}
