//go:build !windows

package backendproc

func killOrphanBackendPids(exclude map[int]bool) int {
	pids := listUnixBackendPids(exclude)
	KillUnixPids(pids)
	return len(pids)
}
