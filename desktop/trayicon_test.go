package main

import (
	"bytes"
	"image"
	"image/color"
	"image/png"
	"testing"
)

func encodePNG(t *testing.T, img image.Image) []byte {
	t.Helper()
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		t.Fatalf("encode: %v", err)
	}
	return buf.Bytes()
}

func TestTrayIconPNGDownscales(t *testing.T) {
	src := image.NewRGBA(image.Rect(0, 0, 1024, 1024))
	for y := 0; y < 1024; y++ {
		for x := 0; x < 1024; x++ {
			src.Set(x, y, color.RGBA{200, 100, 50, 255})
		}
	}
	out := trayIconPNG(encodePNG(t, src))
	img, err := png.Decode(bytes.NewReader(out))
	if err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if got := img.Bounds().Dx(); got != trayIconSize {
		t.Fatalf("width = %d, want %d", got, trayIconSize)
	}
	if got := img.Bounds().Dy(); got != trayIconSize {
		t.Fatalf("height = %d, want %d", got, trayIconSize)
	}
	r, g, b, a := img.At(32, 32).RGBA()
	if r>>8 != 200 || g>>8 != 100 || b>>8 != 50 || a>>8 != 255 {
		t.Fatalf("centre pixel = %v,%v,%v,%v", r>>8, g>>8, b>>8, a>>8)
	}
}

func TestTrayIconPNGFallsBackOnGarbage(t *testing.T) {
	garbage := []byte("not a png")
	if got := trayIconPNG(garbage); !bytes.Equal(got, garbage) {
		t.Fatal("expected original bytes back on decode failure")
	}
}

func TestTrayIconPNGOddSize(t *testing.T) {
	src := image.NewRGBA(image.Rect(0, 0, 333, 197))
	out := trayIconPNG(encodePNG(t, src))
	img, err := png.Decode(bytes.NewReader(out))
	if err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if img.Bounds().Dx() != trayIconSize || img.Bounds().Dy() != trayIconSize {
		t.Fatalf("bounds = %v", img.Bounds())
	}
}
