// Hole-size gauge: find the clearance this printer needs for M2 to M4 screws before
// printing parts with screw holes. Unprinted and untested design.
// Rows are screw sizes (M2, M2.5, M3, M4, numbered by notches on the left edge).
// Columns add more clearance from left to right; one notch on the front edge marks
// the column with the least.

/* [Holes] */
// Smallest extra clearance added to each screw size (mm)
start = 0.1; // [0:0.05:0.5]
// Extra clearance added per column (mm)
step = 0.1; // [0.05:0.05:0.3]
// Number of columns
columns = 5; // [2:1:8]
// Plate thickness (mm)
thickness = 3; // [2:0.5:6]

/* [Hidden] */
sizes = [2, 2.5, 3, 4];
pitch = 9;
margin = 6;
$fn = 40;

plate_w = 2 * margin + (columns - 1) * pitch;
plate_h = 2 * margin + (len(sizes) - 1) * pitch;

difference() {
    cube([plate_w, plate_h, thickness]);
    for (r = [0 : len(sizes) - 1], c = [0 : columns - 1])
        translate([margin + c * pitch, margin + r * pitch, -1])
            cylinder(d = sizes[r] + start + c * step, h = thickness + 2);
    // Row notches on the left edge: one for M2, up to four for M4.
    for (r = [0 : len(sizes) - 1], k = [0 : r])
        translate([-0.01, margin + r * pitch - 2 + k * 1.3, -0.01])
            cube([0.8, 0.6, thickness + 0.02]);
    // One notch on the front edge under the first column.
    translate([margin - 0.3, -0.01, -0.01])
        cube([0.6, 0.8, thickness + 0.02]);
}
