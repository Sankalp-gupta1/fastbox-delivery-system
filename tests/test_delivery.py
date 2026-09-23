import copy
import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from main import build_report, distance, export_best_agent, load_data, simulate


ROOT = Path(__file__).resolve().parents[1]


def small_case():
    return {
        "warehouses": {"W1": [0, 0]},
        "agents": {"A1": [0, 0], "A2": [20, 0]},
        "packages": [{"id": "P1", "warehouse": "W1", "destination": [3, 4]}],
    }


class DeliveryTests(unittest.TestCase):
    def test_euclidean_distance(self):
        self.assertEqual(distance([0, 0], [3, 4]), 5)
        self.assertEqual(distance([2, -3], [2, -3]), 0)
        self.assertEqual(distance([-3, -4], [0, 0]), 5)
        self.assertAlmostEqual(distance([0.5, 0.5], [3.5, 4.5]), 5)

    def test_base_case_against_hand_calculated_result(self):
        report, log = simulate(load_data(ROOT / "base_case.json"))
        self.assertEqual(report, {
            "A1": {"packages_delivered": 2, "total_distance": 121.21, "efficiency": 60.61},
            "A2": {"packages_delivered": 2, "total_distance": 79.21, "efficiency": 39.60},
            "A3": {"packages_delivered": 1, "total_distance": 14.14, "efficiency": 14.14},
            "best_agent": "A3",
        })
        self.assertEqual([row["agent_id"] for row in log], ["A1", "A2", "A3", "A1", "A2"])

    def test_both_input_formats_produce_same_result(self):
        data = load_data(ROOT / "base_case.json")
        dictionary_data = {
            "warehouses": {item["id"]: item["location"] for item in data["warehouses"]},
            "agents": {item["id"]: item["location"] for item in data["agents"]},
            "packages": [
                {"id": p["id"], "warehouse": p["warehouse_id"], "destination": p["destination"]}
                for p in data["packages"]
            ],
        }
        self.assertEqual(simulate(data), simulate(dictionary_data))

    def test_assignment_is_to_warehouse_not_destination(self):
        data = small_case()
        data["packages"][0]["destination"] = [20, 0]
        report, log = simulate(data)
        self.assertEqual(log[0]["agent_id"], "A1")
        self.assertEqual(report["A1"]["total_distance"], 20)

    def test_assignment_stays_fixed_and_next_trip_starts_at_last_destination(self):
        data = small_case()
        data["agents"]["A2"] = [1, 0]
        data["packages"] = [
            {"id": "P1", "warehouse": "W1", "destination": [3, 4]},
            {"id": "P2", "warehouse": "W1", "destination": [0, 6]},
        ]
        report, log = simulate(data)
        self.assertEqual([row["agent_id"] for row in log], ["A1", "A1"])
        self.assertEqual(log[1]["start"], [3, 4])
        # 5 to the first customer, 5 back to W1, 6 to the second customer.
        self.assertEqual(report["A1"]["total_distance"], 16)
        self.assertEqual(report["A1"]["efficiency"], 8)

    def test_agent_visits_different_warehouses(self):
        data = small_case()
        data["warehouses"]["W2"] = [6, 8]
        data["packages"].append({"id": "P2", "warehouse": "W2", "destination": [6, 12]})
        report, log = simulate(data)
        self.assertEqual(log[1]["agent_id"], "A1")
        self.assertEqual(log[1]["pickup_distance"], 5)
        self.assertEqual(report["A1"]["total_distance"], 14)

    def test_assignment_tie_uses_alphabetical_id(self):
        data = small_case()
        data["agents"] = {"A2": [1, 0], "A1": [-1, 0]}
        _, log = simulate(data)
        self.assertEqual(log[0]["agent_id"], "A1")

    def test_idle_agent_cannot_be_best(self):
        report, _ = simulate(small_case())
        self.assertEqual(report["A2"], {
            "packages_delivered": 0, "total_distance": 0.0, "efficiency": None,
        })
        self.assertEqual(report["best_agent"], "A1")
        json.dumps(report, allow_nan=False)

    def test_best_agent_ties_and_unrounded_scores(self):
        cases = [
            ({"A1": (1, 5), "A2": (2, 10)}, "A2"),
            ({"A2": (1, 5), "A1": (1, 5)}, "A1"),
            ({"A1": (1, 1.004), "A2": (1, 1.003)}, "A2"),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                totals = {key: {"packages_delivered": count, "total_distance": total}
                          for key, (count, total) in values.items()}
                self.assertEqual(build_report(totals)["best_agent"], expected)

    def test_zero_distance_delivery_is_valid(self):
        data = small_case()
        data["packages"][0]["destination"] = [0, 0]
        report, _ = simulate(data)
        self.assertEqual(report["A1"]["efficiency"], 0)
        self.assertEqual(report["best_agent"], "A1")

    def test_empty_day_and_empty_fleet(self):
        data = small_case()
        data["packages"] = []
        report, log = simulate(data)
        self.assertIsNone(report["best_agent"])
        self.assertIsNone(report["A1"]["efficiency"])
        self.assertEqual(log, [])
        self.assertEqual(simulate({"warehouses": {}, "agents": {}, "packages": []}),
                         ({"best_agent": None}, []))

    def test_invalid_top_level_data(self):
        for data in ([], {}, {"warehouses": {}, "agents": {}}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                simulate(data)

    def test_missing_agents_unknown_warehouse_and_bad_collections(self):
        changes = [
            ("agents", {}), ("warehouses", {}), ("packages", {}),
            ("agents", "A1"), ("agents", ["A1"]),
            ("agents", {"best_agent": [0, 0]}), ("packages", ["P1"]),
        ]
        for field, value in changes:
            data = small_case()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                simulate(data)

    def test_invalid_ids_and_coordinates(self):
        for package_id in (None, 4, "", " "):
            data = small_case()
            data["packages"][0]["id"] = package_id
            with self.subTest(package_id=package_id), self.assertRaises(ValueError):
                simulate(data)
        for location in ([1], [1, 2, 3], "1,2", [True, 2], ["1", 2], [math.nan, 0], [math.inf, 0]):
            data = small_case()
            data["packages"][0]["destination"] = location
            with self.subTest(location=location), self.assertRaises(ValueError):
                simulate(data)

    def test_duplicate_ids_are_rejected(self):
        data = small_case()
        data["packages"].append(copy.deepcopy(data["packages"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate package"):
            simulate(data)
        for field in ("agents", "warehouses"):
            data = small_case()
            data[field] = [{"id": "X", "location": [0, 0]}, {"id": "X", "location": [1, 1]}]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Duplicate ID"):
                simulate(data)

    def test_conflicting_warehouse_aliases(self):
        data = small_case()
        data["packages"][0]["warehouse_id"] = "W2"
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            simulate(data)
        data["packages"][0]["warehouse_id"] = "W1"
        self.assertEqual(len(simulate(data)[1]), 1)

    def test_input_is_not_modified_and_runs_are_repeatable(self):
        data = load_data(ROOT / "base_case.json")
        original = copy.deepcopy(data)
        first = simulate(data)
        self.assertEqual(first, simulate(data))
        self.assertEqual(data, original)

    def test_all_ten_supplied_cases(self):
        paths = sorted((ROOT / "test_cases").glob("test_case_*.json"))
        self.assertEqual(len(paths), 10)
        for path in paths:
            with self.subTest(case=path.name):
                data = load_data(path)
                report, log = simulate(data)
                self.assertEqual([r["package_id"] for r in log], [p["id"] for p in data["packages"]])
                self.assertEqual(sum(report[a]["packages_delivered"] for a in data["agents"]), len(log))
                positions = copy.deepcopy(data["agents"])
                totals = {a: 0.0 for a in positions}
                counts = {a: 0 for a in positions}
                for package, row in zip(data["packages"], log):
                    warehouse = data["warehouses"][package["warehouse"]]
                    # Check against math.dist, separately from the solution's helper.
                    expected_agent = min(data["agents"], key=lambda a: (
                        math.dist(data["agents"][a], warehouse), a))
                    self.assertEqual(row["agent_id"], expected_agent)
                    self.assertEqual(row["start"], positions[expected_agent])
                    trip = (math.dist(positions[expected_agent], warehouse)
                            + math.dist(warehouse, package["destination"]))
                    self.assertEqual(row["trip_distance"], round(trip, 2))
                    totals[expected_agent] += trip
                    counts[expected_agent] += 1
                    positions[expected_agent] = package["destination"]
                for agent in positions:
                    self.assertEqual(report[agent]["total_distance"], round(totals[agent], 2))
                    self.assertEqual(report[agent]["packages_delivered"], counts[agent])
                    average = round(totals[agent] / counts[agent], 2) if counts[agent] else None
                    self.assertEqual(report[agent]["efficiency"], average)
                active = [a for a in positions if counts[a]]
                winner = min(active, key=lambda a: (totals[a] / counts[a], -counts[a], a))
                self.assertEqual(report["best_agent"], winner)
                json.dumps(report, allow_nan=False)

    def test_csv_without_deliveries_has_only_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "best_agent.csv"
            export_best_agent(path, {"best_agent": None})
            with path.open(newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                self.assertEqual(reader.fieldnames, ["agent_id", "packages_delivered", "total_distance", "efficiency"])
                self.assertEqual(list(reader), [])

    def test_cli_runs_all_supplied_inputs_and_writes_outputs(self):
        inputs = [ROOT / "base_case.json"] + sorted((ROOT / "test_cases").glob("*.json"))
        with tempfile.TemporaryDirectory() as folder:
            for source in inputs:
                with self.subTest(case=source.name):
                    destination = Path(folder) / source.stem
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "main.py"), str(source),
                         "--output-dir", str(destination), "--csv"],
                        capture_output=True, text=True, cwd=folder,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected_report, expected_log = simulate(load_data(source))
                    self.assertEqual(load_data(destination / "report.json"), expected_report)
                    self.assertEqual(load_data(destination / "delivery_log.json"), expected_log)
                    with (destination / "best_agent.csv").open(newline="", encoding="utf-8") as file:
                        rows = list(csv.DictReader(file))
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["agent_id"], expected_report["best_agent"])

    def test_cli_rejects_bad_json_missing_input_and_input_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "report.json"
            source.write_text("{ broken json", encoding="utf-8")
            for filename in (source, Path(folder) / "missing.json"):
                result = subprocess.run([sys.executable, str(ROOT / "main.py"), str(filename)],
                                        capture_output=True, text=True, cwd=folder)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
            original = json.dumps(small_case())
            source.write_text(original, encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), str(source)],
                                    capture_output=True, text=True, cwd=folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn("overwriting the input", result.stderr)
            self.assertEqual(source.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
