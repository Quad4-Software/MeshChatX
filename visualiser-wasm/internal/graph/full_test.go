// SPDX-License-Identifier: 0BSD

package graph_test

import (
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/graph"
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
}
