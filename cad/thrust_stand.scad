// Thrust-stand jig for measuring one motor on the bench: a base that holds the fixed
// end of a straight-bar load cell, and a plate that bolts to the cell's free end and
// carries the motor, prop facing up. Both print flat, side by side.
// Unprinted and untested design. Bar load cells vary: measure yours and set the cell
// values before printing. Clamp the base down, and run the first tests without a prop.

/* [Load cell] */
// Load cell length (mm)
cell_l = 80; // [50:1:120]
// Load cell width and height (mm)
cell_w = 12.7; // [8:0.1:20]
// Distance from the cell's end to its first bolt hole (mm)
hole_inset = 5; // [3:0.5:15]
// Distance between the two bolt holes at each end (mm)
hole_spacing = 15; // [8:0.5:30]
// Clearance hole for the cell's bolts (mm): 4.4 for M4, 5.4 for M5
bolt_d = 4.4; // [3:0.1:6]
// Bolt head diameter, for the counterbores (mm)
head_d = 7.6; // [5:0.1:11]
// Bolt head height (mm)
head_h = 4; // [2:0.5:6]

/* [Motor] */
// Motor bell diameter (mm)
motor_d = 28; // [18:1:40]
// Motor screw pattern, centre to centre (mm)
motor_spacing = 16; // [9:0.5:25]
// Motor screw clearance (mm): 3.3 for M3
motor_screw_d = 3.3; // [2:0.1:4]
// Centre hole for the motor's shaft clip and bearing (mm)
motor_centre_d = 9; // [4:0.5:14]

/* [Printing] */
// Motor plate thickness (mm)
plate_t = 7; // [5:0.5:12]
// Base height (mm)
base_h = 20; // [12:1:40]

/* [Hidden] */
$fn = 40;
end_gap = 3; // the cell's end sits this far inside each part's edge
seat_l = hole_spacing + 2 * hole_inset + 2 * end_gap;
base_w = max(cell_w + 16, 36);
tab_l = 40;
tab_t = 6;
rib_w = 3;
rib_h = 6;
plate_w = motor_d + 8;
plate_l = seat_l + motor_d + 4;

module counterbored(x, y, z_top, from_top) {
    translate([x, y, -1]) cylinder(d = bolt_d, h = z_top + 2);
    if (from_top)
        translate([x, y, z_top - head_h]) cylinder(d = head_d, h = head_h + 1);
    else
        translate([x, y, -1]) cylinder(d = head_d, h = head_h + 1);
}

module base() {
    cy = base_w / 2;
    difference() {
        union() {
            cube([seat_l, base_w, base_h]);
            translate([-tab_l, 0, 0]) cube([tab_l, base_w, tab_t]);
        }
        // A shallow seat that lines the cell up, open toward its free end.
        translate([end_gap - 0.2, cy - cell_w / 2 - 0.2, base_h - 1.5])
            cube([seat_l, cell_w + 0.4, 2]);
        // Bolts come up from underneath into the cell; heads sit in counterbores.
        for (x = [end_gap + hole_inset, end_gap + hole_inset + hole_spacing])
            counterbored(x, cy, base_h, false);
        // Slots for two screws or a clamp to hold the base on a board.
        for (y = [cy - 10, cy + 10])
            hull() {
                translate([-tab_l + 8, y, -1]) cylinder(d = 5, h = tab_t + 2);
                translate([-tab_l + 22, y, -1]) cylinder(d = 5, h = tab_t + 2);
            }
    }
}

module motor_plate() {
    cy = plate_w / 2;
    mx = seat_l + motor_d / 2 + 2;
    cell_end = seat_l - end_gap;
    difference() {
        union() {
            cube([plate_l, plate_w, plate_t]);
            // Ribs over the bolted end only, clear of the spinning motor bell.
            for (y = [0, plate_w - rib_w])
                translate([0, y, 0]) cube([seat_l, rib_w, plate_t + rib_h]);
        }
        // Bolts go down through the plate into the cell's free end.
        for (x = [cell_end - hole_inset, cell_end - hole_inset - hole_spacing])
            counterbored(x, cy, plate_t, true);
        // Motor screws come up from below.
        for (dx = [-1, 1], dy = [-1, 1])
            translate([mx + dx * motor_spacing / 2, cy + dy * motor_spacing / 2, -1])
                cylinder(d = motor_screw_d, h = plate_t + 2);
        translate([mx, cy, -1]) cylinder(d = motor_centre_d, h = plate_t + 2);
    }
}

base();
translate([0, -plate_w - 8, 0]) motor_plate();
