// Case for the rider's tag: a base with board posts, a USB slot and strap ears, and a
// push-fit lid. Base and lid print side by side, lid upside down (flat face on the bed).
// Unprinted and untested design. The tag board is not drawn yet (see docs/pcb-plan.md),
// so the board size here is a placeholder: set it from the real board before printing.

/* [Board] */
// Board length (mm)
board_l = 45; // [25:1:90]
// Board width (mm)
board_w = 30; // [20:1:60]
// Board thickness (mm)
board_t = 1.6; // [0.8:0.1:2]
// Tallest part above the board, usually the GNSS patch antenna (mm)
above = 6; // [2:0.5:15]
// Board mounting holes, from the board's corners (mm)
hole_inset = 3.5; // [2:0.5:8]

/* [Battery] */
// Space under the board for a flat battery (mm); 0 for none
battery_t = 5; // [0:0.5:12]

/* [Case] */
// Wall thickness (mm)
wall = 1.8; // [1.2:0.1:3]
// Floor thickness (mm)
floor_t = 1.6; // [1:0.1:3]
// Lid thickness (mm); keep it thin and plastic over the GNSS antenna
lid_t = 1.6; // [1:0.1:3]
// Clearance between the lid's lip and the walls (mm)
fit = 0.3; // [0.1:0.05:0.6]
// Outside corner radius (mm); rounded corners are kinder in a fall
corner_r = 3; // [2:0.5:6]

/* [Openings] */
// USB connector slot width (mm)
usb_w = 9.5; // [6:0.5:14]
// USB connector slot height (mm)
usb_h = 3.8; // [2:0.2:6]
// Strap width (mm)
strap_w = 20; // [10:1:30]

/* [Hidden] */
$fn = 36;
side_gap = 1;
inner_l = board_l + 2 * side_gap;
inner_w = board_w + 2 * side_gap;
outer_l = inner_l + 2 * wall;
outer_w = inner_w + 2 * wall;
post_h = battery_t + 1.5;
inner_h = post_h + board_t + above;
base_h = floor_t + inner_h;
board_top = floor_t + post_h + board_t;
post_d = 5;
screw_pilot = 1.7; // M2 self-tapping screw into the post
lip_h = 2.5;
ear_w = 7;
ear_t = 3.5;

module rounded_box(l, w, h, r) {
    rr = max(r, 0.5);
    hull()
        for (x = [rr, l - rr], y = [rr, w - rr])
            translate([x, y, 0]) cylinder(r = rr, h = h);
}

module ear(y0, dir) {
    // A tab on a long side with a slot for the strap.
    ear_l = strap_w + 8;
    x0 = outer_l / 2 - ear_l / 2;
    difference() {
        hull() {
            translate([x0, y0 - 0.01, 0]) cube([ear_l, 0.02, ear_t]);
            for (x = [x0 + 3, x0 + ear_l - 3])
                translate([x, y0 + dir * (ear_w - 3), 0]) cylinder(r = 3, h = ear_t);
        }
        translate([outer_l / 2 - strap_w / 2, y0 + dir * ear_w / 2 - 1.3, -1])
            cube([strap_w, 2.6, ear_t + 2]);
    }
}

module base() {
    difference() {
        union() {
            rounded_box(outer_l, outer_w, base_h, corner_r);
            ear(0, -1);
            ear(outer_w, 1);
        }
        translate([wall, wall, floor_t])
            rounded_box(inner_l, inner_w, inner_h + 1, corner_r - wall);
        // USB slot in the near end wall, level with the top of the board.
        translate([-1, outer_w / 2 - usb_w / 2, board_top - 0.5])
            cube([wall + 2, usb_w, usb_h]);
    }
    // Posts the board screws onto, at its four corner holes.
    for (x = [hole_inset, board_l - hole_inset], y = [hole_inset, board_w - hole_inset])
        translate([wall + side_gap + x, wall + side_gap + y, floor_t - 0.01])
            difference() {
                cylinder(d = post_d, h = post_h);
                cylinder(d = screw_pilot, h = post_h + 1);
            }
}

module lid() {
    lip_l = inner_l - 2 * fit;
    lip_w = inner_w - 2 * fit;
    difference() {
        union() {
            rounded_box(outer_l, outer_w, lid_t, corner_r);
            translate([wall + fit, wall + fit, lid_t - 0.01])
                difference() {
                    rounded_box(lip_l, lip_w, lip_h, corner_r - wall - fit);
                    translate([1.2, 1.2, -1])
                        rounded_box(lip_l - 2.4, lip_w - 2.4, lip_h + 2, corner_r - wall - fit - 1.2);
                }
        }
        // Keep the lip clear of the USB slot when the board sits low.
        translate([-1, outer_w / 2 - usb_w / 2 - 1, lid_t])
            cube([wall + fit + 2.4, usb_w + 2, lip_h + 1]);
    }
}

base();
translate([0, outer_w + ear_w + 6, 0]) lid();
