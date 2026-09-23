# FastBox Delivery Simulator

A small Python program that assigns packages to delivery agents and calculates
their travel distance for the day. It reads a JSON file and creates a report
with each agent's delivery count, average distance per package, and the best agent.

## Run it

Use Python 3.9 or newer. No external packages, database, or API keys are needed.
Open a terminal in the project folder and run:

```bash
python main.py
```

This uses `base_case.json` and writes `report.json` and `delivery_log.json`.
On systems where Python is named `python3`, replace `python` in these commands.

To try a supplied test case and the optional CSV export:

```bash
python main.py test_cases/test_case_1.json --output-dir output/case_1 --csv
```

The output folder is created if needed. Each run replaces the generated files
in that folder, so use a different `--output-dir` to keep several reports.
The program refuses to write over the input file itself.

## Input and output

Both supplied input formats work:

- The PDF and numbered test cases store warehouses and agents as dictionaries,
  such as `"W1": [0, 0]`. Packages use the field `warehouse`.
- `base_case.json` stores warehouses and agents as lists of objects with `id`
  and `location`. Packages use `warehouse_id`.

The program converts both formats to the same internal structure. If both
warehouse fields appear in a package, they must agree.

| File | Purpose |
| --- | --- |
| `main.py` | Input checks, assignment, simulation, and output |
| `base_case.json` | Original base input, unchanged |
| `test_cases/` | All ten original numbered inputs, unchanged |
| `tests/test_delivery.py` | Tests for calculations, routing, input checks, and CLI |
| `report.json` | Agent totals and best agent; included example is from the base case |
| `delivery_log.json` | Package IDs, assigned agents, route points, and trip distances |
| `best_agent.csv` | Optional CSV containing the top performer |

## How the calculation works

The straight-line distance between two points is:

```text
distance = sqrt((x2 - x1)^2 + (y2 - y1)^2)
```

For each package, the program compares the warehouse with every agent's starting
location and selects the nearest agent. After assignment, it processes the
packages in input order. A trip has two parts: current position to warehouse,
then warehouse to destination. The agent's position becomes that destination.

```text
efficiency = total_distance / packages_delivered
```

A smaller value means less distance per delivered package. It is not a percentage.
All calculations use full precision; output values are rounded to two decimals.

## Assumptions

The brief leaves some routing details open. These are the choices used here:

1. **JSON parsing:** "manually" is interpreted as reading the file directly with
   Python's built-in `json` module and handling the data with dictionaries and
   loops. There is no Pandas import, external parser, or hardcoded input.
2. **Assignment first:** all packages are assigned using agents' initial positions,
   before anyone moves. This follows the assignment-then-simulation task order.
   Packages are not reassigned during delivery.
3. **One package per trip:** deliveries follow input order for each agent. There is
   no batching or route optimization. This is a simple deterministic simulator,
   not a claim of the shortest possible overall route.
4. **Movement:** an agent continues from the last delivery destination. Travel back
   to a warehouse is counted when picking up the next package, but there is no
   extra return journey after the final delivery.
5. **Ties:** equally near agents are chosen by alphabetical ID. Equal unrounded
   efficiency scores are resolved by more deliveries, then alphabetical ID.
6. **Idle agents:** their distance is zero and efficiency is `null` because no
   average can be calculated. They cannot win. If no packages are delivered,
   `best_agent` is also `null`; a requested CSV then contains just its header.
7. **Coordinates and time:** coordinates are 2D points in unspecified distance
   units, not necessarily kilometres. Negative and decimal coordinates are valid.
   There are no road restrictions, capacities, travel times, or deadlines in the
   input. All packages are available at the start and deliveries succeed.
8. **Invalid input:** missing fields, invalid coordinates, repeated IDs in lists,
   repeated package IDs, unknown warehouses, or packages without agents cause a
   clear error instead of silently dropping deliveries. The agent ID `best_agent`
   is reserved because it is a report key.

## Base-case result

Running `python main.py --csv` produces:

| Agent | Packages | Total distance | Average distance |
| --- | --- | --- | --- |
| A1 | 2 | 121.21 | 60.61 |
| A2 | 2 | 79.21 | 39.60 |
| A3 | 1 | 14.14 | 14.14 |

The best agent is **A3** under the assumptions above. A1 delivers P1 and P4,
A2 delivers P2 and P5, and A3 delivers P3.

For example, A3 travels from `(95, 30)` to W3 at `(100, 25)`, then to `(105, 20)`.
Each leg is `sqrt(50)`, giving about `14.14` distance units in total.

The report numbers printed in the PDF do not follow from its coordinates under
these routing rules. They are treated as an example of the report structure,
not expected values to copy. The provided ZIP contains input cases, not an
official set of expected outputs.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover the hand-calculated base result, all ten additional inputs,
both input formats, nearest-agent choice, continuous movement, ties, idle agents,
an empty day, invalid input, repeatable results, and actual command-line output
files. Every supplied case is checked for matching input and delivered counts.

Verified on Python 3.12: all 21 test methods passed, including CLI runs for all
11 supplied inputs. These are local checks against the assumptions above, not
results from the company's private evaluator.

## Optional bonus and limits

`--csv` exports the top performer using Python's built-in `csv` module.
Random delays, an ASCII route map, and agents joining mid-day are not implemented.
There is no timing model in this version, so results stay repeatable.

For P packages and A agents, assignment takes O(P * A) time and the delivery loop
takes O(P). That is sufficient for the small datasets supplied with this task.
