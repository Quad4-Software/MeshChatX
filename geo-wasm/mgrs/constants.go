package mgrs

// MGRS letter tables (100 km columns per zone group, 100 km row letters). These
// follow the NATO/NGA lettering scheme used by MSP GEOTRANS / GeographicLib.
const (
	utmerowPeriod          = 20
	utmevenRowShift        = 5
	mgrsTileSize           = 100_000 // meters per side of a letter block
	utmeastingTiles        = 5       // central meridian at 500 km = 5 * tile
	minUTMCols             = 1
	maxUTMCols             = 9
	minUTMsRowTiles        = 10
	maxUTMsRowTiles        = 100
	minUTMnRowTiles        = 0
	maxUTMnRowTiles        = 95
	utmNorthernShift       = (maxUTMsRowTiles - minUTMnRowTiles) * mgrsTileSize
	mgrsdigitBase          = 10
	coordMultiply          = 1_000_000
	utmFalseEastM          = float64(utmeastingTiles * mgrsTileSize)
	utmSouthernFalseNorthM = float64(utmNorthernShift)
	tileScaleMicro         = int64(coordMultiply) * int64(mgrsTileSize)
)

// pow10Int64[d] equals 10^d for digit scaling in the numerical MGRS tail.
var pow10Int64 = [...]int64{
	1,
	10,
	100,
	1_000,
	10_000,
	100_000,
	1_000_000,
	10_000_000,
	100_000_000,
	1_000_000_000,
	10_000_000_000,
	100_000_000_000,
}

var (
	utmcols = [3]string{"ABCDEFGH", "JKLMNPQR", "STUVWXYZ"}
	utmrows = []byte("ABCDEFGHJKLMNPQRSTUV")
	latBand = []byte("CDEFGHJKLMNPQRSTUVWX")

	digits = []byte("0123456789")
)

func zoneCentralMeridianDeg(zone int) float64 {
	return float64(zone)*6.0 - 183.0
}
