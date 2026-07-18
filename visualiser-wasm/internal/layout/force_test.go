// SPDX-License-Identifier: 0BSD

package layout_test

import (
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
)

func TestSettleMovesUnfixedNodes(t *testing.T) {
	res := layout.Settle(layout.Request{
		Nodes: []layout.Node{
			{ID: "me", X: 0, Y: 0, Mass: 4, Fixed: true},
			{ID: "a", X: 10, Y: 0, Mass: 1},
			{ID: "b", X: -10, Y: 0, Mass: 1},
		},
		Edges: []layout.Edge{
			{From: "me", To: "a", Length: 200},
			{From: "me", To: "b", Length: 200},
		},
		Iterations: 80,
	})
	if len(res.Positions) != 3 {
		t.Fatalf("expected 3 positions, got %d", len(res.Positions))
	}
	if res.Positions["me"].X != 0 || res.Positions["me"].Y != 0 {
		t.Fatalf("me should stay fixed: %#v", res.Positions["me"])
	}
	// Springs should push a/b outward from the tiny start distance.
	if abs(res.Positions["a"].X) < 20 {
		t.Fatalf("expected a to move outward, got %#v", res.Positions["a"])
	}
}

func TestSettlePreservesAndUpdatesVelocity(t *testing.T) {
	nodes := []layout.Node{
		{ID: "me", X: 0, Y: 0, Mass: 4, Fixed: true},
		{ID: "a", X: 20, Y: 0, Vx: 5, Vy: 0, Mass: 1},
	}
	res := layout.Settle(layout.Request{
		Nodes:      nodes,
		Edges:      []layout.Edge{{From: "me", To: "a", Length: 180}},
		Iterations: 3,
		Damping:    0.5,
		MaxSpeed:   20,
	})
	if len(res.Positions) != 2 {
		t.Fatalf("positions %d", len(res.Positions))
	}
	// Request nodes are updated in place so live Tick can carry momentum.
	if nodes[1].Vx == 5 && nodes[1].X == 20 {
		t.Fatalf("expected velocity/position to integrate, got vx=%v x=%v", nodes[1].Vx, nodes[1].X)
	}
}

func BenchmarkSettle500(b *testing.B) {
	nodes := make([]layout.Node, 500)
	edges := make([]layout.Edge, 0, 500)
	nodes[0] = layout.Node{ID: "me", Fixed: true, Mass: 4}
	for i := 1; i < 500; i++ {
		id := "n" + itoa(i)
		nodes[i] = layout.Node{ID: id, X: float64(i%50) * 10, Y: float64(i/50) * 10, Mass: 1}
		edges = append(edges, layout.Edge{From: "me", To: id, Length: 200})
	}
	req := layout.Request{Nodes: nodes, Edges: edges, Iterations: 60}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = layout.Settle(req)
	}
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var buf [16]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	return string(buf[i:])
}

func abs(v float64) float64 {
	if v < 0 {
		return -v
	}
	return v
}
