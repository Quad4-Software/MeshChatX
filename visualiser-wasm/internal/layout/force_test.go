// SPDX-License-Identifier: 0BSD

package layout_test

import (
	"math"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
)

func TestSpringLength(t *testing.T) {
	if layout.SpringLength(3) != layout.DefaultHubSpringLen {
		t.Fatalf("hub spring %v", layout.SpringLength(3))
	}
	if layout.SpringLength(1) != layout.DefaultSpringLen {
		t.Fatalf("peer spring %v", layout.SpringLength(1))
	}
}

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
	if math.Abs(res.Positions["a"].X) < 20 {
		t.Fatalf("expected a to move outward, got %#v", res.Positions["a"])
	}
}

func TestSettleNegativeGravityDisablesOriginPull(t *testing.T) {
	// Far from origin with no edges: default gravity would suck the node home.
	res := layout.Settle(layout.Request{
		Nodes: []layout.Node{
			{ID: "lonely", X: 800, Y: 600, Mass: 1},
		},
		Iterations: 40,
		Gravity:    -1,
	})
	p := res.Positions["lonely"]
	if math.Hypot(p.X-800, p.Y-600) > 5 {
		t.Fatalf("negative gravity must not pull toward origin: start=(800,600) got=%#v", p)
	}
}

func TestSettleSeparatesOverlappingPeers(t *testing.T) {
	res := layout.Settle(layout.Request{
		Nodes: []layout.Node{
			{ID: "hub", X: 0, Y: 0, Mass: 2.5, Fixed: true, Radius: 24},
			{ID: "a", X: 6, Y: 0, Mass: 1, Radius: 22},
			{ID: "b", X: 8, Y: 2, Mass: 1, Radius: 22},
		},
		Edges: []layout.Edge{
			{From: "hub", To: "a", Length: layout.DefaultSpringLen},
			{From: "hub", To: "b", Length: layout.DefaultSpringLen},
		},
		Iterations: 140,
	})
	a := res.Positions["a"]
	b := res.Positions["b"]
	dist := math.Hypot(a.X-b.X, a.Y-b.Y)
	if dist < 80 {
		t.Fatalf("peers still overlapping: dist=%v a=%#v b=%#v", dist, a, b)
	}
	if math.Hypot(a.X, a.Y) < 80 {
		t.Fatalf("peer a should leave the hub disc, got %#v", a)
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

func TestSettleStaysCompact(t *testing.T) {
	res := layout.Settle(layout.Request{
		Nodes: []layout.Node{
			{ID: "me", X: 0, Y: 0, Mass: 4, Fixed: true, Radius: 32},
			{ID: "iface", X: 210, Y: 0, Mass: 2.5, Radius: 24},
			{ID: "a", X: 350, Y: 20, Mass: 1, Radius: 22},
			{ID: "b", X: 350, Y: -20, Mass: 1, Radius: 22},
		},
		Edges: []layout.Edge{
			{From: "me", To: "iface", Length: layout.DefaultHubSpringLen},
			{From: "iface", To: "a", Length: layout.DefaultSpringLen},
			{From: "iface", To: "b", Length: layout.DefaultSpringLen},
		},
		Iterations: 140,
	})
	iface := res.Positions["iface"]
	hubDist := math.Hypot(iface.X, iface.Y)
	if hubDist < 80 || hubDist > 360 {
		t.Fatalf("interface should stay near hub rest length, got dist=%v pos=%#v", hubDist, iface)
	}
	for _, id := range []string{"a", "b"} {
		p := res.Positions[id]
		d := math.Hypot(p.X-iface.X, p.Y-iface.Y)
		if d > 420 {
			t.Fatalf("%s exploded away from interface: dist=%v p=%#v iface=%#v", id, d, p, iface)
		}
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
