package main

import (
	"bytes"
	"image"
	"image/png"
	"sync"
)

const trayIconSize = 64

// trayIconPNG decodes the embedded icon and re-encodes it downscaled for the
// system tray. StatusNotifier hosts pick small sizes and several render a
// 1024px IconPixmap as blank, so the raw PNG is unsuitable. On any failure the
// original bytes are returned so a host can still try to scale it.
func trayIconPNG(src []byte) []byte {
	img, err := png.Decode(bytes.NewReader(src))
	if err != nil {
		return src
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, downscaleRGBA(img, trayIconSize, trayIconSize)); err != nil {
		return src
	}
	return buf.Bytes()
}

var scaledTrayIconPNG = sync.OnceValue(func() []byte { return trayIconPNG(appIconPNG) })

// downscaleRGBA box-averages src into a w*h RGBA image.
func downscaleRGBA(src image.Image, w, h int) *image.RGBA {
	b := src.Bounds()
	sw, sh := b.Dx(), b.Dy()
	dst := image.NewRGBA(image.Rect(0, 0, w, h))
	for y := 0; y < h; y++ {
		y0 := y * sh / h
		y1 := (y + 1) * sh / h
		for x := 0; x < w; x++ {
			x0 := x * sw / w
			x1 := (x + 1) * sw / w
			var r, g, bl, a, n uint32
			for sy := y0; sy < y1; sy++ {
				for sx := x0; sx < x1; sx++ {
					cr, cg, cb, ca := src.At(b.Min.X+sx, b.Min.Y+sy).RGBA()
					r += cr
					g += cg
					bl += cb
					a += ca
					n++
				}
			}
			if n == 0 {
				n = 1
			}
			i := dst.PixOffset(x, y)
			dst.Pix[i+0] = uint8((r / n) >> 8)
			dst.Pix[i+1] = uint8((g / n) >> 8)
			dst.Pix[i+2] = uint8((bl / n) >> 8)
			dst.Pix[i+3] = uint8((a / n) >> 8)
		}
	}
	return dst
}
