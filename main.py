"""Assign packages, simulate deliveries, and save a daily report for FastBox."""

import argparse
import csv
import json
import math
import sys
from pathlib import Path


def check_id(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")


def check_location(location, label):
    if not isinstance(location, list) or len(location) != 2:
        raise ValueError(f"{label} must contain two numbers: [x, y].")
    for coordinate in location:
        if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
            raise ValueError(f"{label} must contain numbers, not text or booleans.")
        if not math.isfinite(coordinate):
            raise ValueError(f"{label} must contain finite numbers.")


def read_locations(items, label):
    """The base case uses lists; the other supplied files use dictionaries."""
    if isinstance(items, dict):
        entries = items.items()
    elif isinstance(items, list):
        entries = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Each entry in {label} must be an object.")
            entries.append((item.get("id"), item.get("location")))
    else:
        raise ValueError(f"{label} must be a dictionary or a list.")

    locations = {}
    for item_id, location in entries:
        check_id(item_id, f"ID in {label}")
        if item_id in locations:
            raise ValueError(f"Duplicate ID in {label}: {item_id}")
        check_location(location, f"Location of {item_id}")
        locations[item_id] = location[:]
    return locations


def prepare_data(data):
    """Validate the input and convert both supported formats to one structure."""
    if not isinstance(data, dict):
        raise ValueError("The input JSON must be an object.")
    for key in ("warehouses", "agents", "packages"):
        if key not in data:
            raise ValueError(f"Missing required field: {key}")

    warehouses = read_locations(data["warehouses"], "warehouses")
    agents = read_locations(data["agents"], "agents")
    if "best_agent" in agents:
        raise ValueError("Agent ID 'best_agent' is reserved for the report.")
    if not isinstance(data["packages"], list):
        raise ValueError("packages must be a list.")
    if data["packages"] and not agents:
        raise ValueError("At least one agent is needed to deliver packages.")

    packages = []
    seen_ids = set()
    for package in data["packages"]:
        if not isinstance(package, dict):
            raise ValueError("Each package must be an object.")
        package_id = package.get("id")
        check_id(package_id, "Package ID")
        if package_id in seen_ids:
            raise ValueError(f"Duplicate package ID: {package_id}")
        seen_ids.add(package_id)

        warehouse_id = package.get("warehouse_id", package.get("warehouse"))
        check_id(warehouse_id, f"Warehouse ID for {package_id}")
        if "warehouse_id" in package and "warehouse" in package:
            if package["warehouse_id"] != package["warehouse"]:
                raise ValueError(f"Conflicting warehouse fields for {package_id}.")
        if warehouse_id not in warehouses:
            raise ValueError(f"Unknown warehouse for {package_id}: {warehouse_id}")
        destination = package.get("destination")
        check_location(destination, f"Destination of {package_id}")
        packages.append({
            "id": package_id,
            "warehouse_id": warehouse_id,
            "destination": destination[:],
        })
    return warehouses, agents, packages


def load_data(filename):
    with open(filename, encoding="utf-8-sig") as file:
        return json.load(file)


def distance(point_a, point_b):
    """Euclidean distance: square root of dx squared plus dy squared."""
    result = math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])
    if not math.isfinite(result):
        raise ValueError("Coordinates are too large to calculate a finite distance.")
    return result


def assign_packages(warehouses, agents, packages):
    assignments = {}
    for package in packages:
        warehouse = warehouses[package["warehouse_id"]]
        # Assignment happens before deliveries, using the starting locations.
        # Equal distances are resolved by agent ID in alphabetical order.
        nearest_agent = min(
            agents,
            key=lambda agent_id: (distance(agents[agent_id], warehouse), agent_id),
        )
        assignments[package["id"]] = nearest_agent
    return assignments


def build_report(totals):
    report = {}
    scores = {}
    for agent_id, stats in totals.items():
        count = stats["packages_delivered"]
        total = stats["total_distance"]
        average = total / count if count else None
        report[agent_id] = {
            "packages_delivered": count,
            "total_distance": round(total, 2),
            "efficiency": round(average, 2) if count else None,
        }
        if count:
            # Use full precision for ranking; round only the saved values.
            scores[agent_id] = (average, -count, agent_id)
    report["best_agent"] = min(scores, key=scores.get) if scores else None
    return report


def simulate(data):
    warehouses, agents, packages = prepare_data(data)
    assignments = assign_packages(warehouses, agents, packages)
    positions = agents.copy()
    totals = {
        agent_id: {"packages_delivered": 0, "total_distance": 0.0}
        for agent_id in agents
    }
    delivery_log = []

    for package in packages:
        agent_id = assignments[package["id"]]
        start = positions[agent_id]
        warehouse = warehouses[package["warehouse_id"]]
        destination = package["destination"]
        pickup_distance = distance(start, warehouse)
        delivery_distance = distance(warehouse, destination)
        trip_distance = pickup_distance + delivery_distance

        totals[agent_id]["packages_delivered"] += 1
        totals[agent_id]["total_distance"] += trip_distance
        if not math.isfinite(totals[agent_id]["total_distance"]):
            raise ValueError("Total distance is too large to represent.")
        # The next pickup starts where this delivery ended, not at the depot.
        positions[agent_id] = destination
        delivery_log.append({
            "package_id": package["id"],
            "agent_id": agent_id,
            "warehouse_id": package["warehouse_id"],
            "start": start,
            "warehouse": warehouse,
            "destination": destination,
            "pickup_distance": round(pickup_distance, 2),
            "delivery_distance": round(delivery_distance, 2),
            "trip_distance": round(trip_distance, 2),
        })

    delivered = sum(stats["packages_delivered"] for stats in totals.values())
    if delivered != len(packages):
        raise RuntimeError("Package count mismatch after simulation.")
    return build_report(totals), delivery_log


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, allow_nan=False)
        file.write("\n")


def export_best_agent(filename, report):
    fields = ["agent_id", "packages_delivered", "total_distance", "efficiency"]
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        best_agent = report["best_agent"]
        if best_agent is not None:
            writer.writerow({"agent_id": best_agent, **report[best_agent]})


def main():
    parser = argparse.ArgumentParser(description="FastBox delivery simulator")
    parser.add_argument("input", nargs="?", default="base_case.json",
                        help="input JSON file (default: base_case.json)")
    parser.add_argument("--output-dir", default=".", help="folder for generated files")
    parser.add_argument("--csv", action="store_true", help="also export the best agent")
    args = parser.parse_args()

    try:
        report, delivery_log = simulate(load_data(args.input))
        output_dir = Path(args.output_dir)
        filenames = ["report.json", "delivery_log.json"]
        if args.csv:
            filenames.append("best_agent.csv")
        for name in filenames:
            if (output_dir / name).resolve() == Path(args.input).resolve():
                raise ValueError("Choose another output folder to avoid overwriting the input.")
        output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_dir / "report.json", report)
        save_json(output_dir / "delivery_log.json", delivery_log)
        if args.csv:
            export_best_agent(output_dir / "best_agent.csv", report)
    except (OSError, ValueError, OverflowError, RecursionError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Delivered {len(delivery_log)} packages.")
    print(f"Best agent: {report['best_agent'] or 'None (no deliveries)'}")
    for name in filenames:
        print(f"Saved: {output_dir / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
