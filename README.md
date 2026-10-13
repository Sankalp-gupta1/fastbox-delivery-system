# FastBox Delivery Simulator

An interactive delivery-assignment simulator built from the original Python take-home assignment.

The project assigns every package to the nearest delivery agent, simulates the agent's movement, calculates the total distance travelled, and finds the most efficient agent.

The repository contains two parts:

1. **Python reference implementation** — the original assignment logic and automated tests.
2. **Interactive web simulator** — a visual browser version for recruiters and reviewers.

## What the project does

For every package, the simulator knows:

- which warehouse contains the package,
- where each delivery agent starts,
- where the customer destination is.

It then:

1. finds the agent closest to the package's warehouse,
2. assigns the package to that agent,
3. simulates the route,
4. moves the agent to the package destination,
5. starts that agent's next trip from the last destination,
6. calculates every agent's total distance,
7. calculates average distance per delivered package,
8. selects the best agent.

## Live web simulator

The production simulator is live on Vercel:

**https://fastbox-delivery-simulator.vercel.app/**

No login, API key or database is required.

The web version includes:

- built-in sample data,
- JSON upload,
- editable JSON input,
- route visualization,
- warehouse, agent and destination markers,
- package-by-package delivery log,
- agent performance table,
- best-agent calculation,
- downloadable `report.json`.

No API key, database or login is required.

## Main assignment rules

### 1. Nearest-agent assignment

A package is assigned to the agent whose **starting location** is nearest to that package's warehouse.

Distance is calculated using Euclidean distance:

```text
distance = sqrt((x2 - x1)^2 + (y2 - y1)^2)
```

### 2. Assignment happens before delivery movement

All packages are assigned first.

An agent moving during the simulation does not change which packages were originally assigned to that agent.

### 3. The next trip starts from the last destination

After an agent delivers a package, its position becomes that delivery destination.

For the next package, the route is:

```text
last destination
      ↓
warehouse
      ↓
new destination
```

### 4. Ties are deterministic

If two agents are the same distance from a warehouse, the alphabetically smaller agent ID wins.

Example:

```text
A1 vs A2 at the same distance → A1
```

### 5. Efficiency

```text
efficiency = total distance / packages delivered
```

A smaller value is better.

If two agents have exactly the same unrounded efficiency:

1. the agent with more deliveries wins,
2. if still tied, alphabetical agent ID wins.

## Base-case result

Running the original base case gives:

| Agent | Packages delivered | Total distance | Average distance |
|---|---:|---:|---:|
| A1 | 2 | 121.21 | 60.61 |
| A2 | 2 | 79.21 | 39.60 |
| A3 | 1 | 14.14 | 14.14 |

**Best agent: A3**

The ranking uses full-precision calculations. Values are rounded only when displayed or saved.

## Project structure

```text
fastbox-delivery-system/
│
├── main.py
├── base_case.json
├── report.json
├── delivery_log.json
├── best_agent.csv
│
├── test_cases/
├── tests/
│   └── test_delivery.py
│
├── web/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── base_case.json
│
└── README.md
```

## Run the Python version

You need Python 3.9 or newer.

### Step 1 — clone the repository

```bash
git clone https://github.com/Sankalp-gupta1/fastbox-delivery-system.git
cd fastbox-delivery-system
```

### Step 2 — run the base case

```bash
python main.py
```

This creates:

```text
report.json
delivery_log.json
```

### Step 3 — also create the CSV

```bash
python main.py --csv
```

This additionally creates:

```text
best_agent.csv
```

### Run another supplied test case

```bash
python main.py test_cases/test_case_1.json --output-dir output/case_1 --csv
```

## Run the web simulator locally

The browser version has no build step.

From the repository root:

```bash
cd web
python -m http.server 8000
```

Open:

```text
http://localhost:8000
```

You can now edit the JSON in the page or upload another JSON file.

## Input formats

The project supports both formats used by the assignment material.

### Dictionary style

```json
{
  "warehouses": {
    "W1": [0, 0]
  },
  "agents": {
    "A1": [5, 5]
  },
  "packages": [
    {
      "id": "P1",
      "warehouse": "W1",
      "destination": [10, 10]
    }
  ]
}
```

### List style

```json
{
  "warehouses": [
    {"id": "W1", "location": [0, 0]}
  ],
  "agents": [
    {"id": "A1", "location": [5, 5]}
  ],
  "packages": [
    {
      "id": "P1",
      "warehouse_id": "W1",
      "destination": [10, 10]
    }
  ]
}
```

## Validation

The Python implementation checks for:

- missing required fields,
- invalid coordinates,
- duplicate IDs,
- duplicate package IDs,
- unknown warehouses,
- packages with no agents,
- conflicting warehouse fields,
- invalid or non-finite numbers.

The browser simulator also performs input validation before a run.

## Automated tests

Run:

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- the hand-calculated base result,
- all 10 supplied numbered cases,
- both supported input formats,
- nearest-agent assignment,
- tie handling,
- agent movement,
- idle agents,
- empty package lists,
- invalid input,
- output file generation.

The original Python implementation was verified with all 21 test methods passing.

## Technology

### Reference implementation

- Python
- built-in `json`
- built-in `csv`
- built-in `math`
- `unittest`

### Interactive demo

- HTML
- CSS
- Vanilla JavaScript
- SVG route visualization
- Vercel

## Scope and limitations

This is a deterministic assignment simulator.

It does **not** claim to model real road networks.

The current model does not include:

- traffic,
- road restrictions,
- package capacity,
- delivery deadlines,
- vehicle types,
- return-to-depot trips,
- dynamic reassignment after agents move.

Coordinates are generic 2D points, not guaranteed to represent kilometres.

## Author

**Sankalp Gupta**

- GitHub: https://github.com/Sankalp-gupta1
- LinkedIn: https://www.linkedin.com/in/sankalp-gupta-rishi-8617302b0/
