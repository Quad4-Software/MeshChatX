// SPDX-License-Identifier: 0BSD

package icon_test

import (
	"sync"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/icon"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/leaktest"
)

func TestDedupeQueueEntries(t *testing.T) {
	queue := []icon.QueueItem{
		{NodeID: "n1", CacheKey: "k1", IconName: "a", FG: "#000", BG: "#fff", Size: 64, Generation: 1},
		{NodeID: "n2", CacheKey: "k1", IconName: "a", FG: "#000", BG: "#fff", Size: 64, Generation: 1},
		{NodeID: "n3", CacheKey: "k2", IconName: "b", FG: "#111", BG: "#eee", Size: 64, Generation: 1},
		{NodeID: "n1", CacheKey: "k1", IconName: "a", FG: "#000", BG: "#fff", Size: 64, Generation: 1},
	}
	out := icon.DedupeQueueEntries(queue)
	if len(out) != 2 {
		t.Fatalf("expected 2 buckets, got %d", len(out))
	}
	if len(out[0].NodeIDs) != 2 || out[0].NodeIDs[0] != "n1" || out[0].NodeIDs[1] != "n2" {
		t.Fatalf("unexpected k1 nodes: %#v", out[0].NodeIDs)
	}
	if icon.DedupeQueueEntries(nil) == nil {
		// nil or empty both acceptable if empty result length is 0
	}
	if len(icon.DedupeQueueEntries(nil)) != 0 {
		t.Fatal("empty queue should yield empty result")
	}
}

func TestIconNoGoroutineLeak(t *testing.T) {
	defer leaktest.Check(t)()
	queue := make([]icon.QueueItem, 200)
	for i := range queue {
		queue[i] = icon.QueueItem{
			NodeID:   "n" + string(rune('0'+i%10)),
			CacheKey: "k" + string(rune('a'+i%5)),
			IconName: "ico",
			FG:       "#000",
			BG:       "#fff",
			Size:     64,
		}
	}
	for i := 0; i < 100; i++ {
		_ = icon.DedupeQueueEntries(queue)
	}
}

func TestIconRace(t *testing.T) {
	queue := make([]icon.QueueItem, 300)
	for i := range queue {
		queue[i] = icon.QueueItem{
			NodeID:   "n" + string(rune('0'+i%10)),
			CacheKey: "k" + string(rune('a'+i%8)),
			IconName: "ico",
			Size:     64,
		}
	}
	var wg sync.WaitGroup
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 50; j++ {
				_ = icon.DedupeQueueEntries(queue)
			}
		}()
	}
	wg.Wait()
}

func FuzzDedupeQueueEntries(f *testing.F) {
	f.Add("n1", "k1", "icon", "#000", "#fff")
	f.Add("", "k", "i", "", "")
	f.Fuzz(func(t *testing.T, nodeID, cacheKey, name, fg, bg string) {
		queue := []icon.QueueItem{
			{NodeID: nodeID, CacheKey: cacheKey, IconName: name, FG: fg, BG: bg, Size: 64},
			{NodeID: nodeID, CacheKey: cacheKey, IconName: name, FG: fg, BG: bg, Size: 64},
		}
		out := icon.DedupeQueueEntries(queue)
		if cacheKey == "" || nodeID == "" {
			if len(out) != 0 {
				t.Fatalf("expected skip, got %#v", out)
			}
			return
		}
		if len(out) != 1 || len(out[0].NodeIDs) != 1 {
			t.Fatalf("unexpected %#v", out)
		}
	})
}

func BenchmarkDedupeQueueEntries(b *testing.B) {
	queue := make([]icon.QueueItem, 1000)
	for i := range queue {
		queue[i] = icon.QueueItem{
			NodeID:   "n" + string(rune('0'+i%20)),
			CacheKey: "k" + string(rune('a'+i%10)),
			IconName: "ico",
			FG:       "#000",
			BG:       "#fff",
			Size:     64,
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = icon.DedupeQueueEntries(queue)
	}
}
