# References

Sources used for design. Add a line for each source actually used.

- PX4 Autopilot documentation: https://docs.px4.io
- ArduPilot documentation: https://ardupilot.org/dev/
- MAVSDK-Python: https://mavsdk.mavlink.io
- Open-Meteo weather API (planned weather source, field names to re-check): https://open-meteo.com/en/docs
- ExpressLRS (open-source 2.4 GHz radio link, planned manual override): https://www.expresslrs.org
- AM32 open-source ESC firmware and its list of supported microcontrollers (planned in-house ESC): https://github.com/am32-firmware/AM32
- PX4 Pixhawk hardware designs, reported as CC BY-SA 3.0. Verify in the official repository before reusing anything: https://github.com/pixhawk/Hardware
- JLCPCB, the low-markup PCB fab used as the planned production route: https://jlcpcb.com/
- Holybro, Heltec, RadioMaster, u-blox, Raspberry Pi, LCSC, DigiKey, Newark, Mouser, JC-Magnetics and other vendors appear in [parts-catalog.md](parts-catalog.md) with their price sources.

Website ([website.md](website.md)):

- GitHub Pages and GitHub Actions host and build the site: https://docs.github.com/en/pages
- three.js 0.186.1 (MIT licence), the 3D view on the parts page: https://threejs.org/
- OpenSCAD 2025.01.19 (GPL-2.0-or-later), the modelling language and renderer for the parts: https://openscad.org/ and https://github.com/openscad/openscad
- openscad-wasm-prebuilt 1.2.0, the WebAssembly build of OpenSCAD the site and `tools/render_parts.mjs` run: https://github.com/lorenzowritescode/openscad-wasm
- Manifold, the geometry engine inside that OpenSCAD build: https://github.com/elalish/manifold
- ISO 178 (plastics, flexural properties) is the source of the test bars' 80 x 10 x 4 mm shape. Only the shape is borrowed; the home test is not the standard's method.
- The chart colours, status colours and freshness ramp follow a colour-blind-checked palette from the data-visualization guidance the coding agent used, checked with its validator on 2026-10-26.

Recordings and simulation ([simulation.md](simulation.md)):

- GPX 1.1, the track format the importer reads: https://www.topografix.com/GPX/1/1/
- GPSLogger for Android writes `hdop` from the receiver's NMEA output, so it is the unitless dilution of precision, and it is sometimes missing (its GPX writer, `Gpx10FileLogger.java`, and its FAQ on missing fields, read on 2026-10-26): https://github.com/mendhak/gpslogger
- OsmAnd stores the phone's location accuracy in meters in the track point's `hdop` field (`SavingTrackHelper.java`, read on 2026-10-26): https://github.com/osmandapp/OsmAnd

Rules and places (found by agent web searches on 2026-10-26, not confirmed with the organisations):

- FAU Environmental Health and Safety, drone safety page (undated): https://www.fau.edu/ehs/info/drone-safety.pdf
- Boca Raton Airport, drone notification procedures (LAANC): https://bocaairport.com/drone-notification-procedures/
- Boca Raton Airport overview: https://en.wikipedia.org/wiki/Boca_Raton_Airport
- FAU Lab Schools' drone teams (the only FAU drone club the search found, at K-12 level): https://www.fau.edu/newsdesk/articles/fau-lab-schools-drone-teams-fly-high-in-state-national-competitions.php
