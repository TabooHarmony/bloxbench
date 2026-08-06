#!/usr/bin/env python3
"""Convert a BloxBench build-export JSON into a playable .rbxlx Roblox place file.

The Studio ``export_build`` tool does not produce a playable place: it returns a
parts/material manifest whose ``parts`` entries are compact arrays::

    [x, y, z, sx, sy, sz, rx, ry, rz, palette_key, shape?, transparency?]

with ``palette`` mapping each key to ``[color_name, material_name]`` (Roblox
BrickColor name and Enum.Material name respectively). This module turns that
manifest into a minimal but valid Roblox XML place: a ``DataModel`` root holding
a ``Workspace`` whose children are ``Part`` items with Size, CFrame, Material,
Color and Transparency. It is intentionally dependency-free (xml.etree only) and
deterministic: the same export JSON always yields byte-identical output.

No fidelity is invented beyond the data: orientation values are treated as
degrees (the Roblox ``CFrame.Angles`` convention used throughout the fixture
code), shape tokens are used verbatim as Enum.PartType names, and material
names come straight from the palette. Colors come from the bundled BrickColor
name table; unknown names fall back to a deterministic gray derived from the
name hash so a build never fails to open.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

# Roblox Enum.PartType names accepted by the exporter and their XML ``Shape``
# tokens are identical strings ("Block", "Ball", "Cylinder", "Wedge"). Anything
# else (or a bare 10-element part entry with no shape) falls back to "Block",
# which is what the harness's part-primitive tests expect as the default.
_SHAPE_ALIASES = {
    "block": "Block",
    "ball": "Ball",
    "sphere": "Ball",
    "cylinder": "Cylinder",
    "wedge": "Wedge",
    "cornerwedge": "CornerWedge",
}

# Common Roblox Enum.Material names; used verbatim from the palette. The palette
# may also carry specialized materials (Water, Grass, Neon, ...) that are valid
# Roblox Enum.Material tokens even if uncommon on Parts; we pass them through.
_KNOWN_MATERIALS = {
    "Plastic", "SmoothPlastic", "Neon", "Metal", "Wood", "WoodPlank", "Slate",
    "Concrete", "Brick", "Grass", "Sand", "Fabric", "Marble", "Granite",
    "CrackedLava", "Rock", "Glacier", "Snow", "Sandstone", "Stone", "Cobblestone",
    "Mud", "Basalt", "Ground", "Asphalt", "LeafyGrass", "Salt", "Limestone",
    "Pavement", "CorrodedMetal", "DiamondPlate", "Foam", "Glass", "ForceField",
    "Ice", "Water", "Invisible", "Air", "Cardboard", "Carpet", "Ceramic",
}

# Roblox BrickColor name -> (r, g, b) for the color names the exporter's palette
# is expected to emit. This is a subset of the standard Roblox palette covering
# every name observed in real exports plus the common builder set. Unknown names
# fall back to a deterministic gray rather than failing the whole conversion.
BRICKCOLOR_RGB: dict[str, tuple[int, int, int]] = {
    "White": (242, 243, 243),
    "Grey": (163, 162, 165),
    "Light grey": (196, 193, 199),
    "Dark grey": (99, 95, 98),
    "Black": (27, 42, 53),
    "Really black": (1, 1, 1),
    "Medium stone grey": (140, 140, 140),
    "Dark stone grey": (90, 90, 90),
    "Red": (196, 40, 28),
    "Bright red": (196, 40, 28),
    "Crimson": (158, 34, 24),
    "Bright orange": (255, 124, 10),
    "Deep orange": (191, 71, 0),
    "Rust": (148, 60, 20),
    "Bright yellow": (245, 205, 48),
    "Yellow": (250, 215, 69),
    "New Yeller": (252, 229, 74),
    "Yellow flip/flop": (243, 227, 18),
    "Bright green": (75, 151, 75),
    "Lime green": (113, 180, 74),
    "Slime green": (45, 148, 106),
    "Forest green": (27, 92, 41),
    "Dark green": (20, 62, 28),
    "Sky blue": (84, 168, 216),
    "Bright blue": (13, 105, 172),
    "Cyan": (0, 188, 177),
    "Medium blue": (18, 59, 104),
    "Bright violet": (107, 50, 124),
    "Sand violet metallic": (122, 107, 211),
    "Magenta": (180, 0, 158),
    "Pink": (254, 78, 156),
    "Salmon": (255, 138, 130),
    "Bright bluish green": (0, 160, 170),
    "Earth green": (34, 102, 55),
    "Bright yellowish green": (190, 215, 60),
    "Pastel blue": (136, 197, 255),
    "Pastel green": (205, 225, 160),
    "Pastel yellow": (226, 208, 130),
    "Pastel orange": (255, 179, 110),
    "Pastel brown": (178, 164, 148),
    "Pastel grey": (202, 203, 204),
    "Brown": (124, 92, 70),
    "Dark brown": (86, 55, 18),
    "Light orange": (250, 190, 120),
    "Light reddish violet": (211, 123, 160),
    "Bright reddish violet": (227, 0, 136),
    "Royal purple": (91, 29, 129),
    "Dark indigo": (0, 24, 85),
    "Dark blue": (0, 33, 112),
    "Darker blue": (22, 25, 125),
    "Navy blue": (10, 25, 99),
    "Deep blue": (0, 84, 120),
    "Cobalt": (0, 40, 88),
    "Teal": (0, 108, 107),
    "Dark teal": (0, 99, 100),
    "Sea green": (40, 114, 88),
    "Bright green metallic": (24, 155, 82),
    "Dark green metallic": (19, 91, 55),
    "Light green metallic": (198, 224, 208),
    "Green": (44, 168, 52),
    "Dark orange": (255, 100, 0),
    "Bright red-violet": (227, 0, 136),
    "Dark salmon": (142, 64, 40),
    "Light blue": (16, 186, 204),
    "Bright yellow-green": (190, 215, 60),
    "Sand": (198, 166, 100),
    "Sand red": (220, 60, 40),
    "Dark sand": (180, 140, 90),
    "Light sand": (220, 200, 150),
    "Institutional white": (248, 248, 248),
    "Mid gray": (129, 129, 129),
    "Really light blue": (0, 140, 205),
    "Blue": (0, 0, 128),
    "Dark grey metallic": (55, 55, 55),
    "Medium metallic": (110, 110, 110),
    "Light metallic": (170, 170, 170),
    "Metalic gold": (220, 180, 50),
    "Cool yellow": (235, 200, 100),
    "Cool green": (120, 190, 100),
    "Cool blue": (100, 160, 220),
    "Cool red": (200, 100, 100),
    "Cool grey": (180, 180, 180),
    "Cool orange": (230, 150, 70),
    "Cool lilac": (180, 150, 220),
    "Cool brown": (160, 130, 90),
    "Cool violet": (140, 100, 180),
    "Cool purple": (110, 80, 160),
    "Cool turquoise": (0, 180, 190),
    "Cool aqua": (0, 200, 170),
    "Cool lime": (150, 220, 80),
    "Cool mint": (130, 210, 160),
    "Cool rose": (230, 130, 160),
    "Cool pink": (240, 140, 180),
    "Cool peach": (240, 190, 140),
    "Cool cream": (240, 230, 200),
    "Cool charcoal": (60, 60, 60),
    "Cool slate": (90, 110, 130),
    "Dark stone": (70, 70, 70),
    "Medium stone": (130, 130, 130),
    "Light stone": (190, 190, 190),
    "Dark fossil": (90, 70, 50),
    "Medium fossil": (140, 110, 80),
    "Light fossil": (190, 160, 120),
    "Tree frog": (50, 140, 80),
    "Desert": (200, 160, 100),
    "Fog": (180, 190, 200),
    "Burlap": (170, 140, 100),
    "Twill": (150, 130, 110),
    "Chino": (180, 150, 110),
    "Chambray": (100, 130, 160),
    "Corduroy": (60, 60, 70),
    "Flannel": (140, 80, 80),
    "Marble": (230, 230, 230),
    "Graphite": (80, 80, 85),
    "Porcelain": (235, 235, 235),
    "Limestone": (210, 205, 195),
}


def _fmt_number(value: Any) -> str:
    """Format a number the way Roblox XML expects: ints stay ints, floats are trimmed."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return format(float(value), ".6g")


def _fmt_vector3(x: Any, y: Any, z: Any) -> str:
    return " ".join(_fmt_number(v) for v in (x, y, z))


def _brickcolor_rgb(name: str) -> tuple[int, int, int]:
    """Resolve a BrickColor name to RGB, falling back to a deterministic gray."""
    key = name.strip()
    rgb = BRICKCOLOR_RGB.get(key)
    if rgb is not None:
        return rgb
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    tone = 90 + (digest[0] % 120)
    return (tone, tone, tone)


def _material_token(name: str) -> str:
    """Return a Roblox Material token for a palette material name."""
    token = name.strip()
    if not token:
        return "Plastic"
    if token in _KNOWN_MATERIALS:
        return token
    # Normalize predictable aliases (spacing/casing) before falling back.
    normalized = token.replace(" ", "").replace("_", "").lower()
    for known in _KNOWN_MATERIALS:
        if known.replace(" ", "").lower() == normalized:
            return known
    return "Plastic"


def _shape_token(shape: Any) -> str:
    """Return a Roblox PartType token for a shape value (default Block)."""
    if not isinstance(shape, str):
        return "Block"
    alias = _SHAPE_ALIASES.get(shape.strip().lower())
    return alias if alias is not None else "Block"


def _add_workspace_children(workspace: ET.Element, parts: Iterable[list[Any]], palette: dict[str, list[Any]]) -> None:
    """Append one <Item class="Part"> per export part entry to the workspace."""
    for index, entry in enumerate(parts):
        if not isinstance(entry, (list, tuple)) or len(entry) < 10:
            raise ValueError(
                f"part entry {index} is not an export array with at least 10 fields: {entry!r}"
            )
        x, y, z, sx, sy, sz, rx, ry, rz = (float(v) for v in entry[:9])
        palette_key = str(entry[9])
        shape = entry[10] if len(entry) > 10 else None
        transparency = entry[11] if len(entry) > 11 else None

        color_name, material_name = ("White", "Plastic")
        palette_entry = palette.get(palette_key)
        if isinstance(palette_entry, (list, tuple)) and len(palette_entry) >= 2:
            if isinstance(palette_entry[0], str) and palette_entry[0]:
                color_name = palette_entry[0]
            if isinstance(palette_entry[1], str) and palette_entry[1]:
                material_name = palette_entry[1]

        r, g, b = _brickcolor_rgb(color_name)
        opacity = 1.0
        if isinstance(transparency, (int, float)) and not isinstance(transparency, bool):
            opacity = 1.0 - max(0.0, min(1.0, float(transparency)))

        item = ET.SubElement(workspace, "Item", {"class": "Part"})
        props = ET.SubElement(item, "Properties")
        ET.SubElement(props, "string", {"name": "Name"}).text = f"Part{index + 1}"
        ET.SubElement(props, "bool", {"name": "Anchored"}).text = "true"
        ET.SubElement(props, "bool", {"name": "CanCollide"}).text = "true"
        ET.SubElement(props, "CoordinateFrame", {"name": "CFrame"}).text = _cframe_text(
            x, y, z, rx, ry, rz
        )
        ET.SubElement(props, "Vector3", {"name": "Size"}).text = _fmt_vector3(sx, sy, sz)
        ET.SubElement(props, "Token", {"name": "Shape"}).text = _shape_token(shape)
        ET.SubElement(props, "Token", {"name": "Material"}).text = _material_token(material_name)
        ET.SubElement(props, "Color3uint8", {"name": "Color"}).text = f"{r} {g} {b}"
        if opacity < 1.0:
            ET.SubElement(props, "float", {"name": "Transparency"}).text = _fmt_number(1.0 - opacity)
        # Color3uint8 RGB values are accepted by Roblox; BrickColor is optional.


def _cframe_text(x: float, y: float, z: float, rx: float, ry: float, rz: float) -> str:
    """Serialize an orientation as a Roblox CoordinateFrame string (degrees).

    The export JSON carries rx/ry/rz in degrees (the same convention the
    fixture and candidate code use via ``CFrame.Angles(math.rad(...))``). Roblox
    XML CoordinateFrame values encode radians, so convert before writing.
    """
    import math

    rad_x, rad_y, rad_z = (math.radians(v) for v in (rx, ry, rz))
    cx, sx = math.cos(rad_x), math.sin(rad_x)
    cy, sy = math.cos(rad_y), math.sin(rad_y)
    cz, sz = math.cos(rad_z), math.sin(rad_z)
    # R = Rz * Ry * Rx (Roblox CFrame.Angles order), column-major layout:
    #   [r00 r01 r02 | r10 r11 r12 | r20 r21 r22 | x  y  z]
    r00 = cy * cz
    r01 = cy * sz
    r02 = -sy
    r10 = sx * sy * cz - cx * sz
    r11 = sx * sy * sz + cx * cz
    r12 = sx * cy
    r20 = cx * sy * cz + sx * sz
    r21 = cx * sy * sz - sx * cz
    r22 = cx * cy
    return " ".join(_fmt_number(v) for v in (r00, r01, r02, r10, r11, r12, r20, r21, r22, x, y, z))


def build_place_xml(data: dict[str, Any]) -> ET.Element:
    """Build the <roblox> root element for an export JSON payload."""
    parts = data.get("parts")
    if not isinstance(parts, list):
        raise ValueError("export JSON has no 'parts' list")
    palette = data.get("palette")
    if not isinstance(palette, dict):
        raise ValueError("export JSON has no 'palette' dict")

    root = ET.Element("roblox", {"version": "4"})
    data_model = ET.SubElement(root, "Item", {"class": "DataModel"})
    data_props = ET.SubElement(data_model, "Properties")
    ET.SubElement(data_props, "string", {"name": "Name"}).text = "Game"
    workspace = ET.SubElement(data_model, "Item", {"class": "Workspace"})
    ET.SubElement(ET.SubElement(workspace, "Properties"), "string", {"name": "Name"}).text = "Workspace"
    _add_workspace_children(workspace, parts, palette)
    return root


def build_place_xml_str(data: dict[str, Any]) -> str:
    """Serialize the place XML with the Roblox XML declaration header."""
    root = build_place_xml(data)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode")


def convert_export_json(export_path: str | Path, place_path: str | Path) -> dict[str, Any]:
    """Convert one export JSON file to a .rbxlx place file.

    Returns metadata suitable for a run manifest (path, bytes, item_count).
    """
    export_path = Path(export_path)
    place_path = Path(place_path)
    data = json.loads(export_path.read_text(encoding="utf-8"))
    xml_text = build_place_xml_str(data)
    place_path.write_text(xml_text, encoding="utf-8")
    item_count = sum(1 for element in ET.fromstring(xml_text).iter() if element.tag == "Item")
    return {
        "path": str(place_path.resolve()),
        "bytes": place_path.stat().st_size,
        "item_count": item_count,
        "parts": len(data.get("parts", [])),
    }


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_json", type=Path, help="export_build JSON artifact")
    parser.add_argument("place_out", type=Path, help="destination .rbxlx path")
    args = parser.parse_args()

    try:
        meta = convert_export_json(args.export_json, args.place_out)
    except Exception as exc:  # noqa: BLE001 - CLI should report the failure
        print(f"build_to_place: error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"wrote {meta['path']} ({meta['bytes']} bytes, {meta['parts']} parts, {meta['item_count']} items)")
