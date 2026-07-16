// SPDX-License-Identifier: 0BSD

package graph_test

import (
	"fmt"
	"runtime"
	"sync"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/graph"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/leaktest"
)

func hops(v float64) *float64 { return &v }

func sampleRequest(n int) graph.Request {
	path := make([]filter.PathEntry, n)
	ann := make(map[string]graph.Announce, n)
	for i := 0; i < n; i++ {
		hash := fmt.Sprintf("%032x", i)
		h := float64(i%5 + 1)
		path[i] = filter.PathEntry{Hash: hash, Interface: "eth0", Hops: &h}
		aspect := "lxmf.delivery"
		if i%3 == 0 {
			aspect = "nomadnetwork.node"
		}
		ann[hash] = graph.Announce{
			DestinationHash: hash,
			Aspect:          aspect,
			DisplayName:     "Node" + hash[:4],
			LastSeen:        "now",
		}
	}
	return graph.Request{
		PathTable: path,
		Announces: ann,
		Positions: map[string]graph.XY{"eth0": {X: 100, Y: 200}},
		HopMax:    hops(4),
		DarkMode:  true,
		LOD:       "high",
	}
}

func TestBuildPathGraphFiltersAndBuilds(t *testing.T) {
	req := graph.Request{
		PathTable: []filter.PathEntry{
			{Hash: "aa", Interface: "eth0", Hops: hops(1)},
			{Hash: "bb", Interface: "eth0", Hops: hops(3)},
			{Hash: "cc", Interface: "eth0", Hops: hops(9)},
			{Hash: "dd", Interface: "eth0", Hops: nil},
		},
		Announces: map[string]graph.Announce{
			"aa": {DestinationHash: "aa", Aspect: "lxmf.delivery", DisplayName: "Alice", LastSeen: "now"},
			"bb": {DestinationHash: "bb", Aspect: "nomadnetwork.node", DisplayName: "Bob", LastSeen: "now"},
			"cc": {DestinationHash: "cc", Aspect: "lxmf.delivery", DisplayName: "Far", LastSeen: "now"},
		},
		Positions: map[string]graph.XY{
			"eth0": {X: 100, Y: 200},
		},
		HopMax:   hops(4),
		DarkMode: true,
		LOD:      "high",
	}
	res := graph.BuildPathGraph(req)
	if len(res.Nodes) != 2 || len(res.Edges) != 2 {
		t.Fatalf("expected 2 nodes/edges, got %d/%d", len(res.Nodes), len(res.Edges))
	}
	if res.Nodes[0].Image != "/assets/images/network-visualiser/user_1hop.png" {
		t.Fatalf("unexpected lxmf image: %s", res.Nodes[0].Image)
	}
	if res.Edges[0].Width != 2.5 {
		t.Fatalf("direct edge width: %v", res.Edges[0].Width)
	}
}

func TestBuildPathGraphSearchAndIcons(t *testing.T) {
	req := sampleRequest(20)
	req.Search = "node0000"
	req.QueueIcons = true
	req.Conversations = map[string]graph.Conversation{
		req.PathTable[0].Hash: {
			LxmfUserIcon: &graph.UserIcon{IconName: "account", ForegroundColour: "#000", BackgroundColour: "#fff"},
		},
	}
	res := graph.BuildPathGraph(req)
	if len(res.Nodes) == 0 {
		t.Fatal("expected search hits")
	}
}

func TestGraphNoGoroutineLeak(t *testing.T) {
	defer leaktest.Check(t)()
	req := sampleRequest(200)
	for i := 0; i < 50; i++ {
		_ = graph.BuildPathGraph(req)
	}
}

func TestGraphRace(t *testing.T) {
	req := sampleRequest(300)
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			local := req
			local.Positions = map[string]graph.XY{"eth0": {X: 1, Y: 2}}
			for j := 0; j < 20; j++ {
				_ = graph.BuildPathGraph(local)
			}
		}()
	}
	wg.Wait()
}

func TestGraphHeapStableAcrossRuns(t *testing.T) {
	req := sampleRequest(500)
	runtime.GC()
	var start, end runtime.MemStats
	runtime.ReadMemStats(&start)
	for i := 0; i < 30; i++ {
		_ = graph.BuildPathGraph(req)
	}
	runtime.GC()
	runtime.ReadMemStats(&end)
	// Allow generous headroom for allocator noise while catching runaway retention.
	const maxGrowth = 32 << 20
	if end.HeapAlloc > start.HeapAlloc+maxGrowth {
		t.Fatalf("heap grew too much: start=%d end=%d", start.HeapAlloc, end.HeapAlloc)
	}
}

func FuzzBuildPathGraph(f *testing.F) {
	f.Add("aa", float64(1), "lxmf.delivery", "Alice", float64(4), "ali")
	f.Add("bb", float64(9), "nomadnetwork.node", "Bob", float64(2), "")
	f.Fuzz(func(t *testing.T, hash string, hopsVal float64, aspect, name string, hopMax float64, search string) {
		if hash == "" {
			return
		}
		req := graph.Request{
			PathTable: []filter.PathEntry{{Hash: hash, Interface: "eth0", Hops: &hopsVal}},
			Announces: map[string]graph.Announce{
				hash: {DestinationHash: hash, Aspect: aspect, DisplayName: name, LastSeen: "t"},
			},
			HopMax:  &hopMax,
			Search:  search,
			DarkMode: true,
			LOD:     "medium",
		}
		res := graph.BuildPathGraph(req)
		if len(res.Nodes) != len(res.Edges) {
			t.Fatalf("nodes/edges mismatch %d/%d", len(res.Nodes), len(res.Edges))
		}
		if len(res.Nodes) != len(res.ProcessedNodeIDs) {
			t.Fatalf("node id mismatch")
		}
	})
}

func BenchmarkBuildPathGraph1000(b *testing.B) {
	req := sampleRequest(1000)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		local := req
		local.Positions = map[string]graph.XY{"eth0": {X: 100, Y: 200}}
		_ = graph.BuildPathGraph(local)
	}
}

func BenchmarkBuildPathGraph2000(b *testing.B) {
	req := sampleRequest(2000)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		local := req
		local.Positions = map[string]graph.XY{"eth0": {X: 100, Y: 200}}
		_ = graph.BuildPathGraph(local)
	}
}

func TestBuildPathGraphAllocBudget(t *testing.T) {
	req := sampleRequest(200)
	allocs := testing.AllocsPerRun(20, func() {
		local := req
		local.Positions = map[string]graph.XY{"eth0": {X: 100, Y: 200}}
		_ = graph.BuildPathGraph(local)
	})
	// Graph build must allocate output slices and titles, but stay bounded.
	const maxAllocs = 5000
	if allocs > maxAllocs {
		t.Fatalf("alloc budget exceeded: %v > %d", allocs, maxAllocs)
	}
}
