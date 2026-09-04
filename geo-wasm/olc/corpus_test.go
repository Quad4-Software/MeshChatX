package olc

import (
	"bufio"
	"encoding/csv"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
)

func testdataPath(name string) string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		panic("caller")
	}
	return filepath.Join(filepath.Dir(file), "testdata", name)
}

func readCSVRows(t *testing.T, name string) [][]string {
	t.Helper()
	f, err := os.Open(testdataPath(name))
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()

	var rows [][]string
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		r := csv.NewReader(strings.NewReader(line))
		cols, err := r.Read()
		if err != nil {
			t.Fatalf("%s: %v in %q", name, err, line)
		}
		rows = append(rows, cols)
	}
	if err := sc.Err(); err != nil {
		t.Fatal(err)
	}
	return rows
}

func mustFloat(t *testing.T, s string) float64 {
	t.Helper()
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func mustInt(t *testing.T, s string) int {
	t.Helper()
	v, err := strconv.Atoi(s)
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func mustInt64(t *testing.T, s string) int64 {
	t.Helper()
	v, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func TestValidityCorpus(t *testing.T) {
	for i, cols := range readCSVRows(t, "validityTests.csv") {
		if len(cols) < 4 {
			t.Fatalf("row %d: want 4 cols", i)
		}
		code := cols[0]
		wantValid := cols[1] == "true"
		wantShort := cols[2] == "true"
		wantFull := cols[3] == "true"
		if IsValid(code) != wantValid {
			t.Errorf("%q IsValid=%v want %v", code, IsValid(code), wantValid)
		}
		if IsShort(code) != wantShort {
			t.Errorf("%q IsShort=%v want %v", code, IsShort(code), wantShort)
		}
		if IsFull(code) != wantFull {
			t.Errorf("%q IsFull=%v want %v", code, IsFull(code), wantFull)
		}
	}
}

func TestEncodingCorpus(t *testing.T) {
	for i, cols := range readCSVRows(t, "encoding.csv") {
		if len(cols) < 6 {
			t.Fatalf("row %d: want 6 cols", i)
		}
		lat := mustFloat(t, cols[0])
		lng := mustFloat(t, cols[1])
		latInt := mustInt64(t, cols[2])
		lngInt := mustInt64(t, cols[3])
		length := mustInt(t, cols[4])
		want := cols[5]

		if got := latitudeAsInteger(lat); got != latInt {
			t.Errorf("row %d latInt got %d want %d", i, got, latInt)
		}
		if got := longitudeAsInteger(lng); got != lngInt {
			t.Errorf("row %d lngInt got %d want %d", i, got, lngInt)
		}
		if got := integerEncode(latInt, lngInt, length); got != want {
			t.Errorf("row %d integerEncode=%q want %q", i, got, want)
		}
		got := Encode(lat, lng, length)
		if got != want {
			t.Errorf("row %d Encode(%v,%v,%d)=%q want %q", i, lat, lng, length, got, want)
		}
	}
}

func TestDecodingCorpus(t *testing.T) {
	for i, cols := range readCSVRows(t, "decoding.csv") {
		if len(cols) < 6 {
			t.Fatalf("row %d: want 6 cols", i)
		}
		code := cols[0]
		length := mustInt(t, cols[1])
		latLo := mustFloat(t, cols[2])
		lngLo := mustFloat(t, cols[3])
		latHi := mustFloat(t, cols[4])
		lngHi := mustFloat(t, cols[5])

		area, err := Decode(code)
		if err != nil {
			t.Errorf("row %d Decode(%q): %v", i, code, err)
			continue
		}
		if area.Len != length {
			t.Errorf("row %d Len got %d want %d", i, area.Len, length)
		}
		const eps = 1e-10
		if math.Abs(area.LatLo-latLo) > eps || math.Abs(area.LngLo-lngLo) > eps ||
			math.Abs(area.LatHi-latHi) > eps || math.Abs(area.LngHi-lngHi) > eps {
			t.Errorf("row %d Decode(%q)\ngot  lo=(%v,%v) hi=(%v,%v)\nwant lo=(%v,%v) hi=(%v,%v)",
				i, code, area.LatLo, area.LngLo, area.LatHi, area.LngHi, latLo, lngLo, latHi, lngHi)
		}
	}
}

func TestShortCodeCorpus(t *testing.T) {
	for i, cols := range readCSVRows(t, "shortCodeTests.csv") {
		if len(cols) < 5 {
			t.Fatalf("row %d: want 5 cols", i)
		}
		full := cols[0]
		lat := mustFloat(t, cols[1])
		lng := mustFloat(t, cols[2])
		short := cols[3]
		kind := cols[4]

		if kind == "B" || kind == "S" {
			got, err := Shorten(full, lat, lng)
			if err != nil {
				t.Errorf("row %d Shorten: %v", i, err)
				continue
			}
			if got != short {
				t.Errorf("row %d Shorten got %q want %q", i, got, short)
			}
		}
		if kind == "B" || kind == "R" {
			got, err := RecoverNearest(short, lat, lng)
			if err != nil {
				t.Errorf("row %d RecoverNearest: %v", i, err)
				continue
			}
			if got != full {
				t.Errorf("row %d RecoverNearest got %q want %q", i, got, full)
			}
		}
	}
}

func TestEncodeDecodeRoundTripSamples(t *testing.T) {
	samples := []struct {
		lat, lng float64
		len      int
	}{
		{-1.286386, 36.817223, 10}, // Nairobi
		{47.365590, 8.524997, 11},
		{40.689253, -74.044548, 10},
		{-89.5, 179.5, 10},
		{0, 0, 8},
	}
	for _, s := range samples {
		code := Encode(s.lat, s.lng, s.len)
		area, err := Decode(code)
		if err != nil {
			t.Fatal(err)
		}
		clat, clng := area.Center()
		if math.Abs(clat-s.lat) > 0.05 || math.Abs(clng-s.lng) > 0.05 {
			t.Fatalf("%s center %+v %+v far from %v %v", code, clat, clng, s.lat, s.lng)
		}
	}
}
