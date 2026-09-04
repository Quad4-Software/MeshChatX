package mgrs

// UPS letter tables and tile index limits follow GeographicLib MGRS / NGA UPS.
const (
	minUPSSind    = 8
	maxUPSSind    = 32
	minUPSNind    = 13
	maxUPSNind    = 27
	upsEasting    = 20
	upsFalseEast  = float64(upsEasting * mgrsTileSize)
	upsFalseNorth = upsFalseEast
	upsScaleK0    = 0.994
)

var (
	upsband = []byte("ABYZ")
	upscols = [4]string{
		"JKLPQRSTUXYZ",
		"ABCFGHJKLPQR",
		"RSTUXYZ",
		"ABCFGHJ",
	}
	upsrows = [2]string{
		"ABCDEFGHJKLMNPQRSTUVWXYZ",
		"ABCDEFGHJKLMNP",
	}
)
