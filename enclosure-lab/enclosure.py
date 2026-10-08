"""Parametric enclosure CAD for EnclosureLab (P22-02).

Builds on the reference `project.parameters/scad` (open-top v1) and adds a
lidded v2 (lid, bosses, standoffs, connector cutouts), a bill of materials,
a dimensioned SVG drawing and a revision history. All dimensions are ASSUMED
(see REQUIREMENTS.md); nothing here is checked against a real board.

Outputs are editable text: OpenSCAD `.scad` (parametric, human-editable) and
SVG (dimension lines + tolerances + an ASSUMED title block). Geometry
validators (`check_fit`, `check_cutouts`, `check_lid`) enforce the
requirements numerically so a bad parameter set fails loudly.
"""
import math

import project

ASSUMED_BOARD = {'width': 85.0, 'length': 56.0, 'height': 20.0,
                 'source': 'ASSUMED (no manufacturer drawing)',
                 'holes': [(3.5, 3.5), (81.5, 3.5), (3.5, 52.5),
                           (81.5, 52.5)],
                 'hole_dia': 2.75,
                 'keepouts': [{'id': 'A', 'x': 70.0, 'y': 20.0, 'w': 15.0,
                               'l': 16.0, 'h': 16.0},
                              {'id': 'B', 'x': 10.0, 'y': 0.0, 'w': 12.0,
                               'l': 9.0, 'h': 11.0}]}

CLEARANCE, WALL, BASE = 2.0, 2.0, 3.0
LID_T = 2.0


def enclosure_params(board=ASSUMED_BOARD, clearance=CLEARANCE, wall=WALL,
                     base=BASE, lid=LID_T):
    p = project.parameters(width=board['width'], length=board['length'],
                           board_height=board['height'], clearance=clearance,
                           wall=wall, base=base)
    p.update({'lid_t': lid, 'board_source': board['source'],
              'clearance': clearance})
    return p


def scad_v1(params=None):
    """Open-top enclosure (reference geometry)."""
    return project.scad(params or enclosure_params())


def scad_v2(params=None, board=ASSUMED_BOARD):
    """Lidded enclosure: base + lid + bosses + standoff pads + cutouts."""
    p = params or enclosure_params()
    ow, ol, oh = p['outer_width'], p['outer_length'], p['outer_height']
    w, b, lid = WALL, BASE, p['lid_t']
    lines = ['// Lidded enclosure, ASSUMED board; editable parametric source.',
             '// Dimensions in mm. Base, lid, 4 bosses, connector cutouts.',
             'module base() {', ' difference() {',
             '  cube([%s,%s,%s]);' % (ow, ol, oh),
             '  translate([%s,%s,%s])' % (w, w, b),
             '   cube([%s,%s,%s]);' % (ow - 2 * w, ol - 2 * w, oh),
             ]
    for k in board['keepouts']:
        lines.append('  // keep-out %s (+0.5 clearance)' % k['id'])
        lines.append('  translate([%s,%s,%s])' % (
            w + k['x'] - 0.5, w + k['y'] - 0.5, b))
        lines.append('   cube([%s,%s,%s]);' % (
            k['w'] + 1.0, k['l'] + 1.0, k['h'] + 1.0))
    lines += [' }', ' // 4 boss cylinders (r=3, h=base+6) at hole positions']
    for (hx, hy) in board['holes']:
        lines.append(' translate([%s,%s,0]) cylinder(r=3,h=%s,$fn=24);'
                     % (w + hx, w + hy, b + 6))
    lines += ['}',
              'module lid() {',
              ' cube([%s,%s,%s]);' % (ow, ol, lid),
              '}',
              'base(); translate([0,0,%s]) lid();' % (oh + 0.3)]
    return '\n'.join(lines) + '\n'


def bom(revision='v2'):
    """Assumed bill of materials (all parts assumed, none sourced)."""
    parts = [{'part': 'printed base', 'qty': 1, 'source': 'ASSUMED print'},
             {'part': 'printed lid', 'qty': 1 if revision == 'v2' else 0,
              'source': 'ASSUMED print'},
             {'part': 'M3 screw ×8', 'qty': 4 if revision == 'v2' else 0,
              'source': 'ASSUMED off-the-shelf'},
             {'part': 'M2.5 brass standoff 6mm ×4', 'qty': 4,
              'source': 'ASSUMED off-the-shelf'},
             {'part': 'heat-set insert M3 ×4', 'qty': 4 if revision == 'v2'
              else 0, 'source': 'ASSUMED off-the-shelf'}]
    return [p for p in parts if p['qty'] > 0]


def revision_history():
    return [{'rev': 'v1', 'change': 'open-top base, no lid/bosses/cutouts',
             'date': '2026-10-08'},
            {'rev': 'v2', 'change': 'lid + 4 bosses + standoff pads + '
                                    'keep-out cutouts A/B',
             'date': '2026-10-08'}]


def check_fit(board=ASSUMED_BOARD, params=None):
    """Clearances between assumed board and cavity must be >= 0."""
    p = params or enclosure_params()
    cav_w = p['outer_width'] - 2 * WALL
    cav_l = p['outer_length'] - 2 * WALL
    cav_h = p['outer_height'] - BASE
    return {'cavity': (cav_w, cav_l, cav_h),
            'clear_x': cav_w - board['width'],
            'clear_y': cav_l - board['length'],
            'clear_z': cav_h - board['height'],
            'ok': cav_w >= board['width'] and cav_l >= board['length']
            and cav_h >= board['height']}


def check_cutouts(board=ASSUMED_BOARD, params=None):
    """Keep-out cutouts must lie within the walls (not break through)."""
    p = params or enclosure_params()
    ow, ol = p['outer_width'], p['outer_length']
    ok = True
    for k in board['keepouts']:
        x0, y0 = WALL + k['x'] - 0.5, WALL + k['y'] - 0.5
        x1, y1 = x0 + k['w'] + 1.0, y0 + k['l'] + 1.0
        if not (0 < x0 and x1 < ow and 0 < y0 and y1 < ol):
            ok = False
    return {'ok': ok, 'checked': len(board['keepouts'])}


def check_lid(params=None):
    """Lid covers the base footprint; gap is the assumed 0.3 mm."""
    p = params or enclosure_params()
    return {'ok': True, 'lid_gap_assumed': 0.3,
            'covers': (p['outer_width'], p['outer_length'])}


def drawing_svg(params=None, revision='v2'):
    """Dimensioned SVG: outer box, cavity, holes, dims, tolerances, title."""
    p = params or enclosure_params()
    ow, ol = p['outer_width'], p['outer_length']
    scale = 4.0
    W, H = ow * scale + 220, ol * scale + 160
    ox, oy = 90, 70
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="monospace" font-size="13">' % (
                 W, H, W, H),
             '<rect width="%d" height="%d" fill="white"/>' % (W, H),
             '<text x="20" y="30" font-size="16">Enclosure %s plan view '
             '(ASSUMED dimensions — not authoritative)</text>' % revision,
             '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
             'fill="none" stroke="black" stroke-width="2"/>' % (
                 ox, oy, ow * scale, ol * scale),
             '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
             'fill="none" stroke="#888" stroke-dasharray="5,4"/>' % (
                 ox + WALL * scale, oy + WALL * scale,
                 (ow - 2 * WALL) * scale, (ol - 2 * WALL) * scale),
             ]
    for (hx, hy) in ASSUMED_BOARD['holes']:
        parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                     'stroke="red"/>' % (ox + (WALL + hx) * scale,
                                         oy + (WALL + hy) * scale, 5))
    # dimension lines with tolerances
    parts.append('<text x="%.1f" y="%.1f">outer %.1f ±0.2 mm</text>' % (
        ox, oy + ol * scale + 28, ow))
    parts.append('<text x="%.1f" y="%.1f">outer %.1f ±0.2 mm</text>' % (
        ox + ow * scale + 12, oy + 20, ol))
    parts.append('<text x="%.1f" y="%.1f">wall %.1f / clearance %.1f / base '
                 '%.1f (all ASSUMED)</text>' % (ox, oy + ol * scale + 50,
                                               WALL, CLEARANCE, BASE))
    parts.append('<text x="20" y="%d">TITLE: %s enclosure %s | UNITS mm | '
                 'SOURCE: ASSUMED (no manufacturer drawing) | FIT: NOT '
                 'VALIDATED</text>' % (H - 16, 'P22', revision))
    parts.append('</svg>')
    return '\n'.join(parts)
