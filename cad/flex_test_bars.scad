// Test bars for a simple break test: print them with the material and settings you
// want to compare, then bend each one to failure. Unprinted and untested design.
// The bars follow the 80 x 10 x 4 mm shape of the ISO 178 bending test, but this
// is a home comparison, not a standard test.

/* [Bars] */
// Bar length (mm)
length = 80; // [40:5:120]
// Bar width (mm)
width = 10; // [5:1:20]
// Bar thickness (mm)
thickness = 4; // [2:0.5:8]
// Number of bars
count = 3; // [1:1:5]
// Gap between bars on the plate (mm)
gap = 5; // [2:1:15]

/* [Hidden] */
mark_w = 0.8; // side grooves that number the bars: one for the first, two for the second...
mark_d = 0.6;
mark_pitch = 1.6;

module bar(index) {
    difference() {
        cube([length, width, thickness]);
        // Shallow grooves on one side face near the end, outside a centred test span.
        for (k = [0 : index])
            translate([1 + k * mark_pitch, -0.01, -0.01])
                cube([mark_w, mark_d + 0.01, thickness + 0.02]);
    }
}

for (i = [0 : count - 1])
    translate([0, i * (width + gap), 0])
        bar(i);
