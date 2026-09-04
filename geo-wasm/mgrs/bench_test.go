package mgrs

import (
	"strconv"
	"testing"
)

const benchDecodeSample = "19TDJ3858897366"

func benchCoordEUR() (float64, float64) { return 52.658, 5.892 }
func benchCoordAUS() (float64, float64) { return -33.8688, 151.2093 }

func BenchmarkEncode_DefaultDigitPairs(b *testing.B) {
	lat, lon := benchCoordEUR()
	for i := 0; i < b.N; i++ {
		if _, err := Encode(lat, lon, DefaultDigitPairs); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkEncodeBytes_DefaultDigitPairs(b *testing.B) {
	lat, lon := benchCoordEUR()
	for i := 0; i < b.N; i++ {
		if _, err := EncodeBytes(lat, lon, DefaultDigitPairs); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkEncodeTo_preallocated(b *testing.B) {
	lat, lon := benchCoordEUR()
	var dst [MaxEncodedLen]byte
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := EncodeTo(dst[:], lat, lon, DefaultDigitPairs); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkAppendEncode_reuseBacking(b *testing.B) {
	lat, lon := benchCoordEUR()
	dst := make([]byte, 0, 96)
	var err error
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		dst = dst[:0]
		dst, err = AppendEncode(dst, lat, lon, DefaultDigitPairs)
		if err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkEncode_digitPairSweep(b *testing.B) {
	lat, lon := benchCoordEUR()
	for pp := int32(1); pp <= MaxDigitPairs; pp++ {
		pairs := int(pp)
		name := strconv.Itoa(pairs)
		b.Run(name, func(b *testing.B) {
			for i := 0; i < b.N; i++ {
				if _, err := Encode(lat, lon, pairs); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}

func BenchmarkDecode_knownCatalogMgrs(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if _, err := Decode(benchDecodeSample, false); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkRoundTrip_EncodeDecode(b *testing.B) {
	lat, lon := benchCoordEUR()
	for i := 0; i < b.N; i++ {
		s, err := Encode(lat, lon, DefaultDigitPairs)
		if err != nil {
			b.Fatal(err)
		}
		if _, err := Decode(s, false); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkLongitudeZone_hotPath(b *testing.B) {
	lat, lon := benchCoordAUS()
	for i := 0; i < b.N; i++ {
		if _, err := LongitudeZone(lat, lon); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTM_inverseOnly(b *testing.B) {
	lat, lon := benchCoordEUR()
	zone := longitudeZoneStandard(lat, lon)
	south := lat < 0
	east, north := forwardTM(lat, lon, zone, south)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = inverseTM(east, north, zone, south)
	}
}

func BenchmarkTM_forwardOnly(b *testing.B) {
	lat, lon := benchCoordEUR()
	zone := longitudeZoneStandard(lat, lon)
	south := lat < 0
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = forwardTM(lat, lon, zone, south)
	}
}
