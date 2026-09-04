package olc

import "testing"

func BenchmarkEncode_Default(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = Encode(-1.286386, 36.817223, 10)
	}
}

func BenchmarkEncodeTo_preallocated(b *testing.B) {
	var dst [MaxEncodedLen]byte
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := EncodeTo(dst[:], -1.286386, 36.817223, 10); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkAppendEncode_reuseBacking(b *testing.B) {
	buf := make([]byte, 0, MaxEncodedLen)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		buf = AppendEncode(buf[:0], -1.286386, 36.817223, 10)
	}
}

func BenchmarkEncodeBytes_Default(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = EncodeBytes(-1.286386, 36.817223, 10)
	}
}

func BenchmarkDecode_Full(b *testing.B) {
	const code = "6GCRPR78+CV"
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := Decode(code); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkRoundTrip_EncodeDecode(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		code := Encode(-1.286386, 36.817223, 10)
		if _, err := Decode(code); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkShorten_Recover(b *testing.B) {
	const full = "6GCRPR78+CV"
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		short, err := Shorten(full, -1.286386, 36.817223)
		if err != nil {
			b.Fatal(err)
		}
		if _, err := RecoverNearest(short, -1.286386, 36.817223); err != nil {
			b.Fatal(err)
		}
	}
}
