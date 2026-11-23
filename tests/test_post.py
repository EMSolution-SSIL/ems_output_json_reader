"""Producer-shaped fixtures and real-sample checks for output.json."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from emso_post import SelectionError, SeriesError, export_csv, load_output, load_selection, select_series
from emso_post.cli import main


ROOT = Path(__file__).resolve().parents[1]


def producer_fixture() -> dict:
    """Use the keys and layouts written by current post_files/EMSOJson.cpp."""
    force = {"forceX": [1.0, 2.0], "forceY": [3.0, 4.0], "forceZ": [0.0, 0.0],
             "forceMX": [5.0, 6.0], "forceMY": [7.0, 8.0], "forceMZ": [9.0, 10.0]}
    return {
        "metaData": {"EMSolutionVersion": "test"},
        "analysisCondition": {"analysisType": "TRANSIENT"},
        # electriccEnergy intentionally absent: the producer does not list it.
        "postDataList": {"dataList": ["NETWORK", "NODAL_FORCE", "DEMAG_RATIO"]},
        "timeStep": {"numSteps": 2, "stepNo": [1, 2], "timeUnit": "second",
                     "time": [0.0, 0.1], "positionUnit": "deg",
                     "position": [[10.0, 11.0]], "angleUnit": "deg.",
                     "electricalAngle": [0.0, 2.0]},
        "postData": {
            "electrostatic": {"electrostaticUnit": ["V", "C"], "sourceData": [
                {"sourceID": 7, "potential": [1.0, 2.0], "charge": [3.0, 4.0]}]},
            "circuit": {"circuitUnit": ["A", "V", "Wb"],
                        "sourceData": [{"serialNum": 1, "current": [1.0, 2.0],
                                        "voltage": [3.0, 4.0], "flux": [5.0, 6.0]}],
                        "powerSourceData": [{"serialNum": 1, "current": [2.0, 3.0],
                                             "voltage": [4.0, 5.0]}]},
            "network": {"networkUnit": ["A", "V", "Wb"],
                        "networkData": [{"elementNum": 1, "elementName": "FEM",
                                         "current": [1.0, 2.0], "voltage": [3.0, 4.0],
                                         "flux": [5.0, 6.0]},
                                        {"elementNum": 2, "elementName": "FEM",
                                         "current": [2.0, 3.0], "voltage": [4.0, 5.0],
                                         "flux": [6.0, 7.0]},
                                        {"elementNum": 3, "elementName": "FEM",
                                         "current": [3.0, 4.0], "voltage": [5.0, 6.0],
                                         "flux": [7.0, 8.0]}],
                        "convertedData": [{"elementNum": 100, "elementName": "dq-axis",
                                           "d-current": [1.0, 2.0], "q-flux": [3.0, 4.0]}]},
            "binteg": {"coordinateUnit": "m", "magneticDensityUnit": "T",
                       "calculationPoints": 2,
                       "points": {"pointNum": [1, 2], "x": [0.0, 1.0],
                                  "y": [0.0, 0.0], "z": [0.0, 0.0]},
                       "magneticDensity": [
                           {"stepNo": 1, "bx": [1.0, 2.0], "by": [3.0, 4.0],
                            "bz": [5.0, 6.0], "absB": [7.0, 8.0]},
                           {"stepNo": 2, "bx": [11.0, 12.0], "by": [13.0, 14.0],
                            "bz": [15.0, 16.0], "absB": [17.0, 18.0]}]},
            "magFlux": {"fluxUnit": ["Wb", "T"], "fluxData": [
                {"loopNum": 3, "flux": [1.0, 2.0], "absB": [3.0, 4.0]}]},
            "curFlux": {"currentUnit": ["A"], "currentData": [
                {"surfaceNum": 4, "current": [1.0, 2.0]}]},
            "heat": {"heatUnit": "W", "heatData": [
                {"propertyNum": "total", "heat": [10.0, 11.0]},
                {"propertyNum": 2, "heat": [1.0, 2.0]}],
                "sourceHeatData": [{"sourceNum": 1, "heat": [3.0, 4.0]}]},
            "forceJB": {"forceUnit": ["N", "Nm"], "forceJBData": [
                {"propertyNum": "total", **force}]},
            "forceNodal": {"forceUnit": ["N", "Nm"], "forceNodalData": [
                {"propertyNum": 10, **force}, {"propertyNum": "rotor", **force}],
                "forceNodalExtendData": [{"propertyNum": 1, **force}]},
            "magneticEnergy": {"energyUnit": "J", "magneticEnergyData": [
                {"propertyNum": "total", "energy": [1.0, 2.0],
                 "coenergy": [3.0, 4.0], "bh2": [5.0, 6.0]}]},
            "electriccEnergy": {"energyUnit": "J", "electricEnergyData": [
                {"propertyNum": 1, "energy": [1.0, 2.0], "coenergy": [3.0, 4.0]}]},
            "ironLoss": {"lossUnit": "W", "type": "waveform", "ironLossData": [
                {"propertyNum": 1, "jouleLoss": [1.0, 2.0],
                 "hysteresisLoss": [3.0, 4.0]}]},
            "coilForce": {"forceUnit": "N", "coilForceData": [
                {"seriesNum": 1, "coilType": "GCE", "divisionNum": 1,
                 "forceX": [1.0, 2.0], "forceY": [3.0, 4.0], "forceZ": [5.0, 6.0]},
                {"seriesNum": 1, "coilType": "GCE", "divisionNum": 2,
                 "forceX": [6.0, 7.0]}]},
            "demagRatio": {"demagRatioUnit": "-", "demagRatioData": [
                {"propertyNum": 5, "demagRatio": [0.01, 0.02]}]},
        },
    }


class PostProcessingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "output.json"
        self.raw = producer_fixture()
        self.write_fixture()

    def write_fixture(self):
        self.path.write_text(json.dumps(self.raw), encoding="utf-8")

    def test_all_producer_groups_and_axes(self):
        output = load_output(self.path)
        self.assertEqual(set(output.raw["postData"]), {s.post for s in output.series})
        self.assertEqual(output.num_steps, 2)
        self.assertEqual(set(output.axes), {"stepNo", "time", "position[1]", "electricalAngle"})
        self.assertEqual(output.series_for("electriccEnergy")[0].unit, "J")
        point = next(s for s in output.series_for("binteg") if s.identity == (("pointNum", 2),) and s.field == "bx")
        self.assertEqual(point.values, (2.0, 12.0))
        self.assertEqual(next(s for s in output.series_for("magFlux") if s.field == "absB").unit, "T")
        self.assertEqual(next(s for s in output.series_for("network", "convertedData") if s.field == "q-flux").unit, "Wb")

    def test_yaml_selection_csv_and_points(self):
        output = load_output(self.path)
        selected = select_series(output, {"exports": [
            {"post": "forceNodal", "group": "forceNodalData", "ids": ["rotor"], "fields": ["forceMZ"]},
            {"post": "coilForce", "ids": [{"seriesNum": 1, "divisionNum": 2}], "fields": ["forceX"]},
            {"post": "binteg", "ids": [2], "fields": ["bx"]},
        ]})
        self.assertEqual(len(selected), 3)
        paths = export_csv(output, self.directory / "csv", {"exports": [
            {"post": "binteg", "ids": [2], "fields": ["bx"]},
        ]})
        self.assertEqual({p.name for p in paths}, {"binteg_magneticDensity.csv", "binteg_points.csv"})
        with (self.directory / "csv" / "binteg_magneticDensity.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0][-1], "pointNum=2 bx [T]")
        self.assertEqual([row[-1] for row in rows[1:]], ["2.0", "12.0"])
        with self.assertRaises(SeriesError):
            export_csv(output, self.directory / "csv", {"exports": [{"post": "binteg"}]})
        export_csv(output, self.directory / "csv", {"exports": [{"post": "binteg"}]}, overwrite=True)

    def test_bad_selections_and_lengths_are_explicit(self):
        output = load_output(self.path)
        with self.assertRaisesRegex(SelectionError, "ID 999"):
            select_series(output, {"exports": [{"post": "forceNodal", "ids": [999]}]})
        with self.assertRaisesRegex(SelectionError, "項目"):
            select_series(output, {"exports": [{"post": "network", "fields": ["wrong"]}]})
        with self.assertRaisesRegex(SelectionError, "に項目 'forceZ' がありません"):
            select_series(output, {"exports": [
                {"post": "coilForce", "ids": [{"seriesNum": 1, "divisionNum": 2}], "fields": ["forceZ"]}
            ]})
        self.raw["postData"]["network"]["networkData"][0]["current"] = [1.0]
        self.write_fixture()
        with self.assertRaisesRegex(SeriesError, "2 個が必要"):
            load_output(self.path)

    def test_unknown_post_does_not_silently_disappear(self):
        self.raw["postData"]["futureData"] = {"futureList": [{"id": 1, "value": [1.0, 2.0]}]}
        self.write_fixture()
        with self.assertRaisesRegex(SeriesError, "未対応"):
            load_output(self.path)

    def test_real_samples(self):
        if not (ROOT / "output.json").exists() or not (ROOT / "output0Arms0deg.json").exists():
            self.skipTest("ローカル専用の実サンプルがないため省略")
        for filename, count in (("output.json", 1), ("output0Arms0deg.json", 61)):
            with self.subTest(filename=filename):
                output = load_output(ROOT / filename)
                self.assertEqual(output.num_steps, count)
                self.assertEqual({s.post for s in output.series}, {"network", "forceNodal"})
                rotor = next(s for s in output.series_for("forceNodal")
                             if s.identity == (("propertyNum", "rotor"),) and s.field == "forceMZ")
                self.assertEqual(rotor.values[0], output.raw["postData"]["forceNodal"]["forceNodalData"][-1]["forceMZ"][0])
                self.assertTrue(any(s.group == "convertedData" for s in output.series) if count > 1 else True)

    def test_cli_headless_export(self):
        code = main(["export", str(self.path), "--out", str(self.directory / "csv")])
        self.assertEqual(code, 0)
        self.assertTrue((self.directory / "csv" / "demagRatio_demagRatioData.csv").exists())
        self.assertEqual(len(list((self.directory / "csv").glob("*.csv"))), 19)

    def test_yaml_file_and_real_example(self):
        yaml_path = self.directory / "selection.yaml"
        yaml_path.write_text("exports:\n  - post: forceNodal\n    ids: [rotor]\n    fields: [forceMZ]\n", encoding="utf-8")
        output = load_output(self.path)
        self.assertEqual(len(select_series(output, load_selection(yaml_path))), 1)
        self.assertEqual(len(select_series(output, load_selection(ROOT / "examples" / "selection.yaml"))), 10)


if __name__ == "__main__":
    unittest.main()
