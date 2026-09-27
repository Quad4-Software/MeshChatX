// SPDX-License-Identifier: 0BSD

package graph_test

import (
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/graph"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
)

func TestBuildFullGraphIncludesMeAndInterfaces(t *testing.T) {
	h := 1.0
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		MeTitle: "Local",
		MeImage: "/logo.png",
		Interfaces: []graph.InterfaceIn{
			{Name: "eth0", Label: "eth0", Title: "eth0 online", Online: true},
		},
		PathTable: []filter.PathEntry{
			{Hash: "aa", Interface: "eth0", Hops: &h},
		},
		Announces: map[string]graph.Announce{
			"aa": {DestinationHash: "aa", Aspect: "lxmf.delivery", DisplayName: "Alice", LastSeen: "now"},
		},
		DarkMode: true,
		LOD:      "high",
	})
	if len(res.Nodes) < 3 {
		t.Fatalf("expected me+iface+announce, got %d", len(res.Nodes))
	}
	if len(res.LayoutNodes) != len(res.Nodes) {
		t.Fatalf("layout bodies mismatch")
	}
	if len(res.LayoutEdges) != len(res.Edges) {
		t.Fatalf("layout springs mismatch")
	}
	if res.LayoutEdges[0].Length != layout.DefaultHubSpringLen {
		t.Fatalf("hub spring length got %v", res.LayoutEdges[0].Length)
	}
}

func nodeIDs(res graph.FullResult) map[string]bool {
	out := make(map[string]bool, len(res.Nodes))
	for _, n := range res.Nodes {
		out[n.ID] = true
	}
	return out
}

func edgeIDs(res graph.FullResult) map[string]bool {
	out := make(map[string]bool, len(res.Edges))
	for _, e := range res.Edges {
		out[e.ID] = true
	}
	return out
}

func TestBuildFullGraphDiscoveredNodes(t *testing.T) {
	h1 := 1.0
	h9 := 9.0
	hopMax := 4.0
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		Discovered: []graph.DiscoveredIn{
			{ID: "discovered~a", Label: "Alpha", Connected: true, Hops: &h1},
			{ID: "discovered~b", Label: "Beta", Hops: &h9},
			{ID: "discovered~c", Label: "Gamma"},
		},
		HopMax:         &hopMax,
		ShowDiscovered: true,
		LOD:            "high",
	})
	ids := nodeIDs(res)
	if !ids["discovered~a"] {
		t.Fatalf("expected discovered~a node")
	}
	if ids["discovered~b"] {
		t.Fatalf("hop_max should have filtered discovered~b")
	}
	if !ids["discovered~c"] {
		t.Fatalf("nil hops should bypass hop_max, expected discovered~c")
	}
	eids := edgeIDs(res)
	if !eids["me~discovered~a"] || !eids["me~discovered~c"] {
		t.Fatalf("expected me edges to kept discovered nodes, got %v", eids)
	}
	if eids["me~discovered~b"] {
		t.Fatalf("unexpected edge to filtered discovered~b")
	}
	for _, n := range res.Nodes {
		if n.ID == "discovered~a" && n.Group != "discovered" {
			t.Fatalf("discovered node group got %q", n.Group)
		}
	}
}

func TestBuildFullGraphDiscoveredHiddenWhenDisabled(t *testing.T) {
	h1 := 1.0
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		Discovered: []graph.DiscoveredIn{
			{ID: "discovered~a", Label: "Alpha", Hops: &h1},
		},
		ShowDiscovered: false,
		LOD:            "high",
	})
	if nodeIDs(res)["discovered~a"] {
		t.Fatalf("show_discovered=false should emit no discovered nodes")
	}
}

func TestBuildFullGraphDiscoveredSearchMatchesReachableOn(t *testing.T) {
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		Search:  "10.0.0",
		Discovered: []graph.DiscoveredIn{
			{ID: "discovered~a", Label: "Alpha", ReachableOn: "10.0.0.9"},
			{ID: "discovered~b", Label: "Beta", TransportID: "aa10.0.0bb"},
			{ID: "discovered~c", Label: "Gamma"},
		},
		ShowDiscovered: true,
		LOD:            "high",
	})
	ids := nodeIDs(res)
	if !ids["discovered~a"] || !ids["discovered~b"] {
		t.Fatalf("reachable_on/transport_id should match search, got %v", ids)
	}
	if ids["discovered~c"] {
		t.Fatalf("discovered~c should not match search")
	}
	// Search misses the me label, so me and its edges must not appear.
	if ids["me"] {
		t.Fatalf("me should be filtered out by search")
	}
	for id := range edgeIDs(res) {
		if len(id) >= 3 && id[:3] == "me~" {
			t.Fatalf("unexpected me edge %q without me node", id)
		}
	}
}

func TestBuildFullGraphSkipsEdgesToFilteredInterfaces(t *testing.T) {
	h1 := 1.0
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		// The search matches the announce but not the interface name, so
		// eth0 is dropped and the eth0~aa edge must not dangle.
		Search: "alice",
		Interfaces: []graph.InterfaceIn{
			{Name: "eth0", Label: "eth0", Online: true},
		},
		PathTable: []filter.PathEntry{
			{Hash: "aa", Interface: "eth0", Hops: &h1},
		},
		Announces: map[string]graph.Announce{
			"aa": {DestinationHash: "aa", Aspect: "lxmf.delivery", DisplayName: "Alice"},
		},
		LOD: "high",
	})
	if !nodeIDs(res)["aa"] {
		t.Fatalf("announce node should be emitted")
	}
	if nodeIDs(res)["eth0"] {
		t.Fatalf("eth0 should be filtered out by search")
	}
	for _, e := range res.Edges {
		if !nodeIDs(res)[e.From] || !nodeIDs(res)[e.To] {
			t.Fatalf("dangling edge %q (%s -> %s)", e.ID, e.From, e.To)
		}
	}
	if len(res.Edges) != 0 {
		t.Fatalf("expected no edges, got %v", res.Edges)
	}
	if len(res.LayoutEdges) != len(res.Edges) {
		t.Fatalf("layout springs mismatch: %d vs %d", len(res.LayoutEdges), len(res.Edges))
	}
}

func TestBuildFullGraphKeepsPerNodeFontsAtHighLOD(t *testing.T) {
	h1 := 1.0
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		Interfaces: []graph.InterfaceIn{
			{Name: "eth0", Label: "eth0", Online: true},
		},
		Discovered: []graph.DiscoveredIn{
			{ID: "discovered~a", Label: "Alpha", Hops: &h1},
		},
		ShowDiscovered: true,
		LOD:            "high",
	})
	fonts := make(map[string]map[string]any, len(res.Nodes))
	for _, n := range res.Nodes {
		fonts[n.ID] = n.Font
	}
	me := fonts["me"]
	if me == nil || me["size"] != 16.0 || me["bold"] != true {
		t.Fatalf("me font should stay bold 16, got %v", me)
	}
	iface := fonts["eth0"]
	if iface == nil || iface["size"] != 12.0 || iface["bold"] != true {
		t.Fatalf("interface font should stay bold 12, got %v", iface)
	}
	disc := fonts["discovered~a"]
	if disc == nil || disc["size"] != 10.0 {
		t.Fatalf("discovered font should stay size 10, got %v", disc)
	}
}

func TestBuildFullGraphInterfaceEdgesNeedMe(t *testing.T) {
	res := graph.BuildFullGraph(graph.FullRequest{
		MeLabel: "Home",
		Search:  "eth0",
		Interfaces: []graph.InterfaceIn{
			{Name: "eth0", Label: "eth0", Online: true},
		},
		LOD: "high",
	})
	ids := nodeIDs(res)
	if ids["me"] {
		t.Fatalf("me should be filtered out by search")
	}
	if !ids["eth0"] {
		t.Fatalf("eth0 should match search")
	}
	if edgeIDs(res)["me~eth0"] {
		t.Fatalf("me~eth0 edge emitted without me node")
	}
}
