// SPDX-License-Identifier: 0BSD

package filter_test

import (
	"sync"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/leaktest"
)

func ptr(v float64) *float64 { return &v }

func TestPathHashesWithinHopFilter(t *testing.T) {
	table := []filter.PathEntry{
		{Hash: "aa", Hops: ptr(1)},
		{Hash: "bb", Hops: ptr(4)},
		{Hash: "cc", Hops: ptr(5)},
		{Hash: "dd", Hops: nil},
		{Hash: "aa", Hops: ptr(1)},
	}
	got := filter.PathHashesWithinHopFilter(table, ptr(4))
	if len(got) != 2 || got[0] != "aa" || got[1] != "bb" {
		t.Fatalf("unexpected: %#v", got)
	}
	gotAll := filter.PathHashesWithinHopFilter(table, nil)
	if len(gotAll) != 3 {
		t.Fatalf("expected 3 unique hashes, got %#v", gotAll)
	}
	if filter.PathHashesWithinHopFilter(nil, ptr(1)) != nil {
		t.Fatal("empty should return nil")
	}
}

func TestMatchesSearch(t *testing.T) {
	if !filter.MatchesSearch("", "anything") {
		t.Fatal("empty query should match")
	}
	if !filter.MatchesSearch("foo", "FooBar") {
		t.Fatal("expected case-insensitive match")
	}
	if filter.MatchesSearch("zzz", "abc") {
		t.Fatal("expected miss")
	}
	if !filter.MatchesSearch("café", "Café Latte") {
		t.Fatal("expected unicode fold match")
	}
}

func TestFilterNoGoroutineLeak(t *testing.T) {
	defer leaktest.Check(t)()
	table := make([]filter.PathEntry, 200)
	for i := range table {
		h := float64(i % 8)
		table[i] = filter.PathEntry{Hash: "h" + string(rune('a'+i%26)), Hops: &h}
	}
	for i := 0; i < 200; i++ {
		_ = filter.PathHashesWithinHopFilter(table, ptr(4))
		_ = filter.MatchesSearch("ab", "Alphabet")
	}
}

func TestFilterRace(t *testing.T) {
	table := make([]filter.PathEntry, 500)
	for i := range table {
		h := float64(i%6 + 1)
		table[i] = filter.PathEntry{Hash: "hash-" + string(rune('0'+i%10)), Interface: "eth0", Hops: &h}
	}
	var wg sync.WaitGroup
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				_ = filter.PathHashesWithinHopFilter(table, ptr(3))
				_ = filter.MatchesSearch("hash", "HASH-1")
			}
		}()
	}
	wg.Wait()
}

func FuzzPathHashesWithinHopFilter(f *testing.F) {
	f.Add("aa", float64(1), float64(4))
	f.Add("", float64(0), float64(0))
	f.Fuzz(func(t *testing.T, hash string, hops, hopMax float64) {
		table := []filter.PathEntry{{Hash: hash, Hops: &hops}}
		out := filter.PathHashesWithinHopFilter(table, &hopMax)
		if hops > hopMax {
			if len(out) != 0 {
				t.Fatalf("expected empty for hops>%v", hopMax)
			}
			return
		}
		if hash == "" {
			if len(out) != 0 {
				t.Fatal("empty hash should be skipped")
			}
			return
		}
		if len(out) != 1 || out[0] != hash {
			t.Fatalf("unexpected %#v", out)
		}
	})
}

func FuzzMatchesSearch(f *testing.F) {
	f.Add("foo", "FooBar")
	f.Add("", "x")
	f.Add("z", "")
	f.Fuzz(func(t *testing.T, q, text string) {
		_ = filter.MatchesSearch(q, text)
		if q == "" && !filter.MatchesSearch(q, text) {
			t.Fatal("empty query must match")
		}
	})
}

func BenchmarkPathHashesWithinHopFilter(b *testing.B) {
	table := make([]filter.PathEntry, 2000)
	for i := range table {
		h := float64(i%8 + 1)
		table[i] = filter.PathEntry{Hash: "h" + string(rune('a'+i%26)) + string(rune('0'+i%10)), Hops: &h}
	}
	max := 4.0
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = filter.PathHashesWithinHopFilter(table, &max)
	}
}

func BenchmarkMatchesSearchASCII(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = filter.MatchesSearch("mesh", "ReticulumMeshNode")
	}
}

func TestMatchesSearchASCIIZeroAllocs(t *testing.T) {
	allocs := testing.AllocsPerRun(1000, func() {
		_ = filter.MatchesSearch("mesh", "ReticulumMeshNode")
	})
	if allocs != 0 {
		t.Fatalf("expected 0 allocs for ASCII search, got %v", allocs)
	}
}
