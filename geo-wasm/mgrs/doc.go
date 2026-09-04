// Package mgrs converts between WGS84 geographic coordinates and the Military
// Grid Reference System (MGRS) over UTM and polar UPS.
//
// It follows the letter-grid rules described in NGA references on UTM/MGRS
// (e.g. TM8358.1, Universal Grids and Grid Reference Systems) and matches
// GeographicLib / MSP GEOTRANS conventions for Norway/Svalbard zone widening,
// UPS lettering, and upper-bound ~nanometre coordinate nudges.
//
// Coverage is the full globe: UTM for latitudes in [-80°, 84°) and UPS outside
// that belt (bands A/B south, Y/Z north). ZoneUPS (0) identifies polar grid
// metres in the Grid API.
//
// EncodeBytes, AppendEncode, EncodeTo, and EncodeGridTo support allocation-
// conscious callers. DecodeParts returns structured zone, band, square,
// precision, metres, and lat/lon. FormatSpaced pretty-prints compact refs.
//
// Tests include a checked-in golden corpus plus optional external oracles.
// Set MGRS_REQUIRE_ORACLES=1 to fail (instead of skip) when PROJ or
// GeographicLib GeoConvert are missing. CI installs those tools and requires them.
package mgrs
