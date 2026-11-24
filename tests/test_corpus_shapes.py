"""Regression cases found in the EMSolution validation corpus."""

import json
import tempfile
import unittest
from pathlib import Path

from emso_post import SeriesError, export_csv, load_output, select_series
from run_corpus import classify_unindexed


class CorpusShapeTest(unittest.TestCase):
    def test_corpus_report_classifies_expected_absences(self):
        status, notes = classify_unindexed(
            "030_AC/010_ComplexPermeability/010_100Hz/output2_2026.09.2_20261015.json",
            ("postData.heat.heatData: null",),
        )
        self.assertEqual(status, "empty_result")
        self.assertIn("solver bug", notes[0])
        self.assertEqual(classify_unindexed("coil.json", (
            "postData.coilForce.coilForceData[1].forceX: mesh spatial values (267 points)",
        ))[0], "spatial")
        self.assertEqual(classify_unindexed("future.json", ("unknown values",))[0], "incomplete")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "output.json"

    def load(self, raw):
        self.path.write_text(json.dumps(raw), encoding="utf-8")
        return load_output(self.path)

    def test_ac_frequency_min_max_and_null_group(self):
        output = self.load({
            "timeStep": {"numSteps": 1, "frequency": 50.0},
            "postData": {
                "ironLoss": {"type": "minMax", "lossUnit": "W", "ironLossData": [
                    {"propertyNum": 2, "Loss": [1.5, 3.5]},
                ]},
                "heat": {"heatData": None},
            },
        })
        self.assertEqual(output.axes["frequency"].values, (50.0,))
        self.assertEqual({series.field: series.values for series in output.series},
                         {"Loss.min": (1.5,), "Loss.max": (3.5,)})
        self.assertEqual(output.unindexed, ("postData.heat.heatData: null",))
        exported = export_csv(output, self.path.parent / "csv")
        self.assertEqual(len(exported), 1)
        self.assertIn("frequency [Hz]", exported[0].read_text(encoding="utf-8-sig"))

    def test_duplicate_ids_can_be_selected_together(self):
        output = self.load({
            "timeStep": {"stepNo": [1, 2], "time": [0, 1]},
            "postData": {"forceJB": {"forceJBData": [
                {"propertyNum": 7, "forceX": [1, 2]},
                {"propertyNum": 7, "forceX": [3, 4]},
            ]}},
        })
        self.assertEqual([series.identity for series in output.series], [
            (("propertyNum", 7), ("recordNo", 1)),
            (("propertyNum", 7), ("recordNo", 2)),
        ])
        selected = select_series(output, {"exports": [{"post": "forceJB", "ids": [7]}]})
        self.assertEqual(len(selected), 2)

    def test_empty_and_spatial_arrays_are_reported(self):
        output = self.load({
            "timeStep": {"stepNo": [1], "time": [0]},
            "postData": {"coilForce": {"coilForceData": [
                {"seriesNum": 1, "divisionNum": 1, "coilType": "MESH",
                 "forceX": [1, 2, 3], "forceY": []},
            ]}},
        })
        self.assertEqual(output.series, ())
        self.assertEqual(len(output.unindexed), 2)
        self.assertIn("mesh spatial values", output.unindexed[0])
        self.assertIn("empty array", output.unindexed[1])
        self.assertEqual(output.raw["postData"]["coilForce"]["coilForceData"][0]["forceX"], [1, 2, 3])

    def test_null_postdata_is_distinct_from_missing_postdata(self):
        output = self.load({"timeStep": {"stepNo": [1], "time": [0]}, "postData": None})
        self.assertEqual(output.series, ())
        self.assertEqual(output.unindexed, ("postData: no post results",))
        with self.assertRaises(SeriesError):
            self.load({"timeStep": {"stepNo": [1], "time": [0]}})

    def test_non_spatial_length_mismatch_still_fails(self):
        with self.assertRaisesRegex(SeriesError, "2 "):
            self.load({
                "timeStep": {"stepNo": [1, 2], "time": [0, 1]},
                "postData": {"forceJB": {"forceJBData": [
                    {"propertyNum": 1, "forceX": [1]},
                ]}},
            })


if __name__ == "__main__":
    unittest.main()
