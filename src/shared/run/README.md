# Benchmark Dashboard System

## Overview

This system runs benchmarks comparing different strategies (GeoMIP, KGeoMIP, QNodes, KQNodes) across network datasets and generates an interactive HTML dashboard.

## File Structure

```
src/shared/
├── run/
│   ├── benchmark.py    # Main runner: executes all strategies, saves CSVs
│   └── dashboard.py     # Generates interactive HTML dashboard
├── output/
│   ├── N{i}{A|B}-
│   │   ├── GeoMIP.csv
│   │   ├── K2GeoMIP.csv, K3GeoMIP.csv, K4GeoMIP.csv, K5GeoMIP.csv
│   │   ├── QNodes.csv
│   │   └── K2QNodes.csv, K3QNodes.csv, K4QNodes.csv, K5QNodes.csv
│   └── benchmark_dashboard.html  # Interactive dashboard
├── casos.py             # Configuration (networks, paths)
└── input/               # Input CSV files (N5.csv, N10.csv)
```

## Running Benchmarks

### 1. Run all benchmarks and generate dashboard

```bash
cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
uv run python src/shared/run/benchmark.py
```

This will:
- Run all strategies (GeoMIP, K2-K5GeoMIP, QNodes, K2-K5QNodes) on all configured networks
- Save results to `src/shared/output/N{i}{A|B}-{Strategy}.csv`
- Generate `benchmark_dashboard.html`

### 2. Run benchmarks for specific networks

```bash
uv run python src/shared/run/benchmark.py --networks N5B N10A
```

### 3. Generate dashboard only (from existing CSVs)

```bash
uv run python src/shared/run/dashboard.py
```

### 4. Generate dashboard for specific networks

```bash
uv run python src/shared/run/dashboard.py --networks N5B N10A
```

## Output Format

Each CSV file contains:
```
index,loss,time,partition
1,0.0,0.0023,
2,0.125,0.0015,
...
```

- **index**: Instance identifier
- **loss**: Strategy loss value
- **time**: Execution time in seconds
- **partition**: Formatted partition string (often empty in benchmark outputs)

## Adding New Networks

1. Add TPM file to `src/.samples/` (e.g., `N15A.csv`)
2. Add input CSV to `src/shared/input/` (e.g., `N15.csv`) with columns: index, state, conditions, purview, mechanism
3. Update `NETWORK_CONFIGS` in both `benchmark.py` and `dashboard.py`:

```python
NETWORK_CONFIGS = {
    "N5B": {"n": 5, "tpm": "N5B.csv"},
    "N10A": {"n": 10, "tpm": "N10A.csv"},
    "N15A": {"n": 15, "tpm": "N15A.csv"},  # Add new network
}
```

4. Run benchmarks:
```bash
uv run python src/shared/run/benchmark.py --networks N5B N10A N15A
uv run python src/shared/run/dashboard.py --networks N5B N10A N15A
```

## Dashboard Sections

1. **Section 1: Execution Time** - Line plots showing time per instance (GeoMIP vs QNodes)
2. **Section 2: Loss Correlation** - Scatter plots comparing strategy pairs:
   - QNodes vs GeoMIP
   - QNodes vs K2QNodes
   - GeoMIP vs K2GeoMIP
   - K3QNodes vs K3GeoMIP
   - K4QNodes vs K4GeoMIP
   - K5QNodes vs K5GeoMIP
3. **Section 3: Boxplots** - Execution time distributions per network size

## Troubleshooting

- **Import errors**: Ensure all dependencies installed via `uv run`
- **Missing CSVs**: Run `benchmark.py` first to generate data
- **Stale dashboard**: Hard refresh browser (Cmd+Shift+R on Mac) or use incognito

## Strategy Naming

| Strategy | Description                    |
| -------- | ------------------------------ |
| GeoMIP   | Geometric MIP (k=2 equivalent) |
| K2GeoMIP | KGeoMIP with k=2               |
| K3GeoMIP | KGeoMIP with k=3               |
| K4GeoMIP | KGeoMIP with k=4               |
| K5GeoMIP | KGeoMIP with k=5               |
| QNodes   | Q-Nodes baseline               |
| K2QNodes | KQNodes with k=2               |
| K3QNodes | KQNodes with k=3               |
| K4QNodes | KQNodes with k=4               |
| K5QNodes | KQNodes with k=5               |