import unittest

from scripts.analyze_spatial_relation_pilot import parse_structure_dump, relation_passes


SAMPLE = """\
Part:TowerShaft parent=RepairTarget Pos=(0.0,7.5,0.0) Size=(8.0,14.0,8.0) Mat=Enum.Material.Cobblestone Anchored=true
Part:LookoutPlatform parent=RepairTarget Pos=(0.0,15.0,0.0) Size=(12.0,1.0,12.0) Mat=Enum.Material.Wood Anchored=true
Part:LookoutColumn parent=RepairTarget Pos=(0.0,19.5,0.0) Size=(4.0,8.0,4.0) Mat=Enum.Material.Cobblestone Anchored=true
Part:LooseRoof parent=RepairTarget Pos=(0.0,24.0,0.0) Size=(10.0,1.0,10.0) Mat=Enum.Material.Wood Anchored=true
Part:Flagpole parent=RepairTarget Pos=(0.0,27.0,0.0) Size=(0.4,6.0,0.4) Mat=Enum.Material.Wood Anchored=true
Part:Flag parent=RepairTarget Pos=(1.3,28.5,0.0) Size=(2.5,1.5,0.1) Mat=Enum.Material.Fabric Anchored=true
"""


class SpatialRelationAnalysisTests(unittest.TestCase):
    def test_parser_extracts_named_parts_and_geometry(self):
        parts = parse_structure_dump(SAMPLE)
        self.assertEqual(parts["LookoutColumn"][0].position, (0.0, 19.5, 0.0))
        self.assertEqual(parts["LooseRoof"][0].size, (10.0, 1.0, 10.0))

    def test_relation_predicates_distinguish_attached_and_detached(self):
        parts = parse_structure_dump(SAMPLE)
        self.assertTrue(relation_passes(parts, "LooseRoof", "centered_over", "LookoutColumn"))
        self.assertTrue(relation_passes(parts, "LooseRoof", "supported_by", "LookoutColumn"))
        self.assertTrue(relation_passes(parts, "Flag", "attached_to", "Flagpole"))
        parts["Flag"][0] = parts["Flag"][0].with_position((4.5, 28.5, 0.0))
        self.assertFalse(relation_passes(parts, "Flag", "attached_to", "Flagpole"))


if __name__ == "__main__":
    unittest.main()
