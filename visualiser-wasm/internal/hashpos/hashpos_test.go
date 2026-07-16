// SPDX-License-Identifier: 0BSD

package hashpos_test

import (
	"math"
	"sync"
	"testing"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/hashpos"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/leaktest"
)

func TestAngle01Stable(t *testing.T) {
	a1 := hashpos.Angle01("abc")
	a2 := hashpos.Angle01("abc")
	if a1 != a2 {
		t.Fatalf("unstable angle: %v vs %v", a1, a2)
	}
	if a1 < 0 || a1 >= 2*math.Pi {
		t.Fatalf("angle out of range: %v", a1)
	}
}

func TestDist01Range(t *testing.T) {
	d := hashpos.Dist01("node", "r")
	if d < 0 || d >= 1 {
		t.Fatalf("dist out of range: %v", d)
	}
}

func TestXYAroundFinite(t *testing.T) {
	x, y := hashpos.XY("n1", 600, 200)
	if math.IsNaN(x) || math.IsNaN(y) || math.IsInf(x, 0) || math.IsInf(y, 0) {
		t.Fatalf("bad XY: %v %v", x, y)
	}
	ax, ay := hashpos.Around("n1", 10, 20, 150, 150)
	if math.IsNaN(ax) || math.IsNaN(ay) {
		t.Fatalf("bad Around: %v %v", ax, ay)
	}
}

func TestHashposNoGoroutineLeak(t *testing.T) {
	defer leaktest.Check(t)()
	for i := 0; i < 1000; i++ {
		_, _ = hashpos.XY("node", 100, 50)
		_, _ = hashpos.Around("node", 1, 2, 10, 10)
	}
}

func TestHashposRace(t *testing.T) {
	var wg sync.WaitGroup
	for i := 0; i < 32; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			id := "race-" + string(rune('a'+n%26))
			for j := 0; j < 200; j++ {
				_ = hashpos.Angle01(id)
				_ = hashpos.Dist01(id, "r")
				_, _ = hashpos.XY(id, 600, 200)
				_, _ = hashpos.Around(id, 0, 0, 150, 150)
			}
		}(i)
	}
	wg.Wait()
}

func FuzzAngle01(f *testing.F) {
	f.Add("")
	f.Add("me")
	f.Add("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
	f.Fuzz(func(t *testing.T, id string) {
		a := hashpos.Angle01(id)
		if math.IsNaN(a) || math.IsInf(a, 0) {
			t.Fatalf("bad angle %v for %q", a, id)
		}
		d := hashpos.Dist01(id, "r")
		if d < 0 || d >= 1 || math.IsNaN(d) {
			t.Fatalf("bad dist %v for %q", d, id)
		}
		x, y := hashpos.XY(id, 1, 1)
		if math.IsNaN(x) || math.IsNaN(y) {
			t.Fatalf("bad xy")
		}
	})
}

func BenchmarkAngle01(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = hashpos.Angle01("destinationhash0123456789abcdef")
	}
}

func BenchmarkDist01(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = hashpos.Dist01("destinationhash0123456789abcdef", "r")
	}
}

func BenchmarkXY(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_, _ = hashpos.XY("destinationhash0123456789abcdef", 600, 200)
	}
}

func BenchmarkAround(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_, _ = hashpos.Around("destinationhash0123456789abcdef", 100, 200, 150, 150)
	}
}

func TestHashposZeroAllocs(t *testing.T) {
	allocs := testing.AllocsPerRun(1000, func() {
		_ = hashpos.Angle01("destinationhash0123456789abcdef")
		_ = hashpos.Dist01("destinationhash0123456789abcdef", "r")
		_, _ = hashpos.XY("destinationhash0123456789abcdef", 600, 200)
		_, _ = hashpos.Around("destinationhash0123456789abcdef", 0, 0, 150, 150)
	})
	if allocs != 0 {
		t.Fatalf("expected 0 allocs, got %v", allocs)
	}
}
