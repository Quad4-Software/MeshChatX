package olc

import (
	"errors"
	"math"
	"testing"
)

func TestEncode_LongitudeWrap(t *testing.T) {
	zero := Encode(0, 0, 10)
	for _, lng := range []float64{360, -360, -720, 720, 1080} {
		if got := Encode(0, lng, 10); got != zero {
			t.Errorf("Encode(0, %v)=%q want %q", lng, got, zero)
		}
	}
	west := Encode(0, -180, 10)
	for _, lng := range []float64{180, -180, 540, -540, -900, -1260} {
		if got := Encode(0, lng, 10); got != west {
			t.Errorf("Encode(0, %v)=%q want %q", lng, got, west)
		}
	}
	for _, lng := range []float64{1e300, -1e300} {
		if got := Encode(0, lng, 10); !IsFull(got) {
			t.Errorf("Encode(0, %v)=%q not a full code", lng, got)
		}
	}
}

func TestEncode_NonFinite(t *testing.T) {
	zero := Encode(0, 0, 10)
	if got := Encode(math.NaN(), math.NaN(), 10); got != zero {
		t.Errorf("Encode(NaN, NaN)=%q want %q", got, zero)
	}
	if got := Encode(0, math.Inf(1), 10); got != zero {
		t.Errorf("Encode(0, +Inf)=%q want %q", got, zero)
	}
	if got := Encode(0, math.Inf(-1), 10); got != zero {
		t.Errorf("Encode(0, -Inf)=%q want %q", got, zero)
	}
	if got := Encode(math.Inf(1), 0, 10); got != Encode(90, 0, 10) {
		t.Errorf("Encode(+Inf, 0)=%q want %q", got, Encode(90, 0, 10))
	}
	if got := Encode(math.Inf(-1), 0, 10); got != Encode(-90, 0, 10) {
		t.Errorf("Encode(-Inf, 0)=%q want %q", got, Encode(-90, 0, 10))
	}
}

func TestShortenRecover_NonFiniteReference(t *testing.T) {
	const code = "849VGJQF+VX7QR3"
	if _, err := Shorten(code, math.NaN(), math.Inf(1)); err != nil {
		t.Fatalf("Shorten with non-finite reference: %v", err)
	}
	if _, err := RecoverNearest("45+G6", math.Inf(-1), math.Inf(1)); err != nil {
		t.Fatalf("RecoverNearest with non-finite reference: %v", err)
	}
}

func TestRecoverNearest_ErrorDetail(t *testing.T) {
	if _, err := RecoverNearest("8FWC2_45+G6", 0, 0); !errors.Is(err, ErrInvalid) {
		t.Fatalf("RecoverNearest invalid char: %v want ErrInvalid", err)
	}
	if _, err := RecoverNearest("8FWC2345+G", 0, 0); !errors.Is(err, ErrInvalid) {
		t.Fatalf("RecoverNearest single trailing char: %v want ErrInvalid", err)
	}
	if _, err := RecoverNearest("", 0, 0); !errors.Is(err, ErrEmpty) {
		t.Fatalf("RecoverNearest empty: %v want ErrEmpty", err)
	}
}

func TestShorten_PaddedAndTooShort(t *testing.T) {
	if _, err := Shorten("8FWCX400+", 0, 0); !errors.Is(err, ErrPadded) {
		t.Fatalf("Shorten padded: %v want ErrPadded", err)
	}
	if _, err := Shorten("8FWC22+", 0, 0); !errors.Is(err, ErrShort) {
		t.Fatalf("Shorten short code: %v want ErrShort", err)
	}
}

func TestAppendShorten_RoundTrip(t *testing.T) {
	const code = "9C3W9QCJ+2VX"
	lat, lng := 51.3708675, -1.217765625
	want, err := Shorten(code, lat, lng)
	if err != nil {
		t.Fatal(err)
	}
	dst, err := AppendShorten(nil, code, lat, lng)
	if err != nil {
		t.Fatal(err)
	}
	if string(dst) != want {
		t.Fatalf("AppendShorten=%q want %q", dst, want)
	}
	full, err := RecoverNearest(string(dst), lat, lng)
	if err != nil {
		t.Fatal(err)
	}
	if full != code {
		t.Fatalf("RecoverNearest(%q)=%q want %q", dst, full, code)
	}
}

func TestAppendRecoverNearest_FullCodeUppercased(t *testing.T) {
	dst, err := AppendRecoverNearest(nil, "8fwc2345+g6", 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if string(dst) != "8FWC2345+G6" {
		t.Fatalf("AppendRecoverNearest=%q want %q", dst, "8FWC2345+G6")
	}
}

func TestRecoverNearest_OverlongShortCode(t *testing.T) {
	cases := []struct {
		code string
		want string
	}{
		{"45+G6GGGGGGGG", "849VHJ45+G6GGGGG"},
		{"+G6GGGGGGGGGGGGGGGG", "849VGJQG+G6GGGGG"},
	}
	for _, tc := range cases {
		got, err := RecoverNearest(tc.code, 37.5397, -122.3751)
		if err != nil {
			t.Fatalf("RecoverNearest(%q): %v", tc.code, err)
		}
		if got != tc.want {
			t.Errorf("RecoverNearest(%q)=%q want %q", tc.code, got, tc.want)
		}
	}
}

func TestRecoverNearest_OverlongFullCodeUnchanged(t *testing.T) {
	const code = "849vgjqf+vx7qr3jw"
	got, err := RecoverNearest(code, 37.5397, -122.3751)
	if err != nil {
		t.Fatal(err)
	}
	if got != "849VGJQF+VX7QR3JW" {
		t.Fatalf("RecoverNearest=%q want full overlong code uppercased", got)
	}
}

func TestShorten_OverlongFullCode(t *testing.T) {
	const code = "849VGJQF+VX7QR3JW"
	got, err := Shorten(code, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if got != code {
		t.Fatalf("Shorten far reference=%q want %q", got, code)
	}
	got, err = Shorten(code, 37.53966914, -122.37506976)
	if err != nil {
		t.Fatal(err)
	}
	if got != "+VX7QR3JW" {
		t.Fatalf("Shorten near reference=%q want %q", got, "+VX7QR3JW")
	}
}

func TestRecoverNearest_PolarBoundary(t *testing.T) {
	cases := []struct {
		code string
		lat  float64
		want string
	}{
		{"2222+22", 89.6, "CFX22222+22"},
		{"XXXXXX+XX", -81, "2CXXXXXX+XX"},
	}
	for _, tc := range cases {
		got, err := RecoverNearest(tc.code, tc.lat, 0)
		if err != nil {
			t.Fatalf("RecoverNearest(%q): %v", tc.code, err)
		}
		if got != tc.want {
			t.Errorf("RecoverNearest(%q, %v, 0)=%q want %q", tc.code, tc.lat, got, tc.want)
		}
		if !IsFull(got) {
			t.Errorf("RecoverNearest(%q)=%q is not a valid full code", tc.code, got)
		}
	}
}

func TestShortenRecover_Antimeridian(t *testing.T) {
	cases := []struct {
		name    string
		codeLng float64
		refLng  float64
		short   string
		full    string
	}{
		{"east code west reference", 179.999, -179.9998, "2X+2J", "6VGX2X2X+2J"},
		{"west code east reference", -179.999, 179.9998, "22+2C", "62G22222+2C"},
		{"four digit trim", 179.9, -179.9, "2W22+22", "6VGX2W22+22"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			code := Encode(0, tc.codeLng, 10)
			if code != tc.full {
				t.Fatalf("Encode(0, %v)=%q want %q", tc.codeLng, code, tc.full)
			}
			short, err := Shorten(code, 0, tc.refLng)
			if err != nil {
				t.Fatal(err)
			}
			if short != tc.short {
				t.Fatalf("Shorten=%q want %q", short, tc.short)
			}
			full, err := RecoverNearest(short, 0, tc.refLng)
			if err != nil {
				t.Fatal(err)
			}
			if full != code {
				t.Fatalf("RecoverNearest=%q want %q", full, code)
			}
		})
	}
}

func TestFloorMul_DoesNotSnapRepresentableBoundaryGap(t *testing.T) {
	const boundary = float64(1e9)
	x := boundary
	for range 4 {
		x = math.Nextafter(x, 0)
	}
	if got := floorMul(x, 1); got != int64(boundary)-1 {
		t.Fatalf("floorMul(%v, 1)=%d want %d", x, got, int64(boundary)-1)
	}
}
