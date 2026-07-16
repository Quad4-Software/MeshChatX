// SPDX-License-Identifier: 0BSD

package lod_test

import (
	"sync"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/leaktest"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/lod"
)

func TestLevelFromScale(t *testing.T) {
	if lod.LevelFromScale(0.1) != "low" {
		t.Fatal("expected low")
	}
	if lod.LevelFromScale(0.3) != "medium" {
		t.Fatal("expected medium")
	}
	if lod.LevelFromScale(0.8) != "high" {
		t.Fatal("expected high")
	}
}

func TestComputeUpdatesLow(t *testing.T) {
	orig := 25.0
	nodes := []lod.NodeIn{
		{ID: "n1", Shape: "circularImage", Size: 25, OriginalShape: "circularImage", OriginalSize: orig},
	}
	out := lod.ComputeUpdates(nodes, "low", false)
	if len(out) != 1 || out[0].Shape != "dot" {
		t.Fatalf("unexpected: %#v", out)
	}
	if out[0].Size == nil || *out[0].Size != 10 {
		t.Fatalf("expected size 10, got %#v", out[0].Size)
	}
}

func TestComputeUpdatesNoChange(t *testing.T) {
	sz := 10.0
	fs := 0.0
	nodes := []lod.NodeIn{
		{ID: "n1", Shape: "dot", Size: 10, OriginalShape: "circularImage", OriginalSize: 25, Font: &lod.FontIn{Size: &fs}},
	}
	out := lod.ComputeUpdates(nodes, "low", false)
	_ = sz
	if len(out) != 0 {
		t.Fatalf("expected no updates, got %#v", out)
	}
}

func TestLODNoGoroutineLeak(t *testing.T) {
	defer leaktest.Check(t)()
	nodes := make([]lod.NodeIn, 500)
	for i := range nodes {
		nodes[i] = lod.NodeIn{
			ID:            "n" + string(rune('a'+i%26)),
			Shape:         "circularImage",
			Size:          25,
			OriginalShape: "circularImage",
			OriginalSize:  25,
		}
	}
	for i := 0; i < 100; i++ {
		_ = lod.ComputeUpdates(nodes, "low", true)
		_ = lod.LevelFromScale(0.25)
	}
}

func TestLODRace(t *testing.T) {
	nodes := make([]lod.NodeIn, 1000)
	for i := range nodes {
		nodes[i] = lod.NodeIn{
			ID:            "n" + string(rune('0'+i%10)),
			Shape:         "circularImage",
			Size:          25,
			OriginalShape: "circularImage",
			OriginalSize:  25,
		}
	}
	var wg sync.WaitGroup
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func(level string) {
			defer wg.Done()
			for j := 0; j < 50; j++ {
				_ = lod.ComputeUpdates(nodes, level, j%2 == 0)
				_ = lod.LevelFromScale(float64(j) / 100)
			}
		}([]string{"low", "medium", "high"}[i%3])
	}
	wg.Wait()
}

func FuzzLevelFromScale(f *testing.F) {
	f.Add(0.0)
	f.Add(0.2)
	f.Add(0.5)
	f.Add(1.0)
	f.Fuzz(func(t *testing.T, scale float64) {
		level := lod.LevelFromScale(scale)
		switch level {
		case "low", "medium", "high":
		default:
			t.Fatalf("bad level %q", level)
		}
	})
}

func FuzzComputeUpdates(f *testing.F) {
	f.Add("n1", "circularImage", 25.0, "low", true)
	f.Add("me", "dot", 15.0, "high", false)
	f.Fuzz(func(t *testing.T, id, shape string, size float64, level string, dark bool) {
		nodes := []lod.NodeIn{{
			ID:            id,
			Shape:         shape,
			Size:          size,
			OriginalShape: "circularImage",
			OriginalSize:  25,
		}}
		_ = lod.ComputeUpdates(nodes, level, dark)
	})
}

func BenchmarkComputeUpdatesLow(b *testing.B) {
	nodes := make([]lod.NodeIn, 2000)
	for i := range nodes {
		nodes[i] = lod.NodeIn{
			ID:            "n" + string(rune('a'+i%26)),
			Shape:         "circularImage",
			Size:          25,
			OriginalShape: "circularImage",
			OriginalSize:  25,
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = lod.ComputeUpdates(nodes, "low", false)
	}
}

func BenchmarkLevelFromScale(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = lod.LevelFromScale(0.33)
	}
}

func TestLevelFromScaleZeroAllocs(t *testing.T) {
	allocs := testing.AllocsPerRun(1000, func() {
		_ = lod.LevelFromScale(0.33)
	})
	if allocs != 0 {
		t.Fatalf("expected 0 allocs, got %v", allocs)
	}
}
