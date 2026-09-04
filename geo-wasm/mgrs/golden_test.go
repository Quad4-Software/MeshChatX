package mgrs

import (
	"bufio"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

type goldenRow struct {
	MGRS      string   `json:"mgrs"`
	Pairs     int      `json:"pairs"`
	Lat       *float64 `json:"lat"`
	Lon       *float64 `json:"lon"`
	Zone      *int     `json:"zone"`
	North     *bool    `json:"north"`
	Easting   *float64 `json:"easting"`
	Northing  *float64 `json:"northing"`
	DecodeLat *float64 `json:"decode_lat"`
	DecodeLon *float64 `json:"decode_lon"`
	Center    bool     `json:"center"`
	TolM      float64  `json:"tol_m"`
	Encode    *bool    `json:"encode"`
	Source    string   `json:"source"`
	Notes     string   `json:"notes"`
}

func TestGoldenCorpus(t *testing.T) {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("caller")
	}
	path := filepath.Join(filepath.Dir(file), "testdata", "golden_mgrs.jsonl")
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if cerr := f.Close(); cerr != nil {
			t.Errorf("close golden corpus: %v", cerr)
		}
	})

	sc := bufio.NewScanner(f)
	lineNo := 0
	for sc.Scan() {
		lineNo++
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		var row goldenRow
		if err := json.Unmarshal(line, &row); err != nil {
			t.Fatalf("line %d: %v", lineNo, err)
		}
		doEncode := true
		if row.Encode != nil {
			doEncode = *row.Encode
		}
		if doEncode {
			var got string
			var encErr error
			switch {
			case row.Zone != nil && row.North != nil && row.Easting != nil && row.Northing != nil:
				got, encErr = EncodeGrid(Grid{
					Zone:     *row.Zone,
					North:    *row.North,
					Easting:  *row.Easting,
					Northing: *row.Northing,
				}, row.Pairs)
			case row.Lat != nil && row.Lon != nil:
				got, encErr = Encode(*row.Lat, *row.Lon, row.Pairs)
			default:
				t.Fatalf("line %d: encode entry needs lat/lon or zone grid fields", lineNo)
			}
			if encErr != nil {
				t.Fatalf("line %d encode: %v", lineNo, encErr)
			}
			if got != row.MGRS {
				t.Fatalf("line %d encode got %q want %q (%s)", lineNo, got, row.MGRS, row.Source)
			}
		}

		wantLat, wantLon := row.Lat, row.Lon
		if row.DecodeLat != nil {
			wantLat = row.DecodeLat
		}
		if row.DecodeLon != nil {
			wantLon = row.DecodeLon
		}
		if wantLat == nil || wantLon == nil {
			continue
		}
		tol := row.TolM
		if tol <= 0 {
			tol = 5
		}
		pt, err := Decode(row.MGRS, row.Center)
		if err != nil {
			t.Fatalf("line %d decode: %v", lineNo, err)
		}
		dLatM := (pt.Lat - *wantLat) * 111_111
		cosClamp := math.Max(math.Abs(math.Cos((*wantLat)*degRad)), 1e-3)
		dLonM := (pt.Lon - *wantLon) * 111_111 * cosClamp
		if math.Hypot(dLatM, dLonM) > tol {
			t.Fatalf("line %d decode residual %.3fm > %.3fm (%s) got %+v want %v,%v",
				lineNo, math.Hypot(dLatM, dLonM), tol, row.Source, pt, *wantLat, *wantLon)
		}
	}
	if err := sc.Err(); err != nil {
		t.Fatal(err)
	}
}
