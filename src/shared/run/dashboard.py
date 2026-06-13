"""
Benchmark Dashboard - Three vertical sections:
1. Execution time per instance (grouped by network size)
2. Loss correlation (QNodes vs others, grouped by network size and K)
3. Boxplots of execution time (grouped by network size)

Usage:
    uv run python src/shared/run_dashboard.py
"""

import argparse
import csv
import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.shared.casos import OUTPUT_DIR

NETWORKS = ["N5B", "N10A", "N15A", "N20A", "N21A", "N22A", "N23A"]

STRATEGIES_ALL = [
    "GeoMIP",
    "K2GeoMIP",
    "K3GeoMIP",
    "K4GeoMIP",
    "K5GeoMIP",
    "QNodes",
    "K2QNodes",
    "K3QNodes",
    "K4QNodes",
    "K5QNodes",
]

STRATEGY_COLORS = {
    "GeoMIP": "blue",
    "K2GeoMIP": "green",
    "K3GeoMIP": "darkgreen",
    "K4GeoMIP": "mediumseagreen",
    "K5GeoMIP": "lime",
    "QNodes": "red",
    "K2QNodes": "crimson",
    "K3QNodes": "darkred",
    "K4QNodes": "salmon",
    "K5QNodes": "orange",
}

STRATEGY_SYMBOLS = {
    "GeoMIP": "circle",
    "K2GeoMIP": "square",
    "K3GeoMIP": "diamond",
    "K4GeoMIP": "triangle-up",
    "K5GeoMIP": "triangle-down",
    "QNodes": "circle-open",
    "K2QNodes": "square-open",
    "K3QNodes": "diamond-open",
    "K4QNodes": "triangle-up-open",
    "K5QNodes": "triangle-down-open",
}


def load_csv_data(network: str, strategy: str) -> list[dict]:
    filepath = f"{OUTPUT_DIR}/{network}-{strategy}.csv"
    if not os.path.exists(filepath):
        return []
    data = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(
                {
                    "index": row["index"],
                    "loss": float(row["loss"]) if row["loss"] else 0.0,
                    "time": float(row["time"]) if row["time"] else 0.0,
                }
            )
    return data


def get_network_size(network: str) -> str:
    return "N" + network[1:-1]


CORRELATION_PAIRS = [
    ("QNodes", "GeoMIP"),
    ("QNodes", "K2QNodes"),
    ("GeoMIP", "K2GeoMIP"),
    ("K3QNodes", "K3GeoMIP"),
    ("K4QNodes", "K4GeoMIP"),
    ("K5QNodes", "K5GeoMIP"),
]


def create_dashboard(networks: list[str], output_path: str) -> None:
    all_data = {net: {} for net in networks}
    for net in networks:
        for strat in STRATEGIES_ALL:
            all_data[net][strat] = load_csv_data(net, strat)

    network_sizes = list(set(get_network_size(n) for n in networks))
    network_sizes.sort(key=lambda x: int(x[1:]))

    networks_by_size = {size: [] for size in network_sizes}
    for net in networks:
        size = get_network_size(net)
        networks_by_size[size].append(net)

    # === SECTION 1: Execution Time Line Plots ===
    n_rows_section1 = len(network_sizes)
    max_cols_section1 = max(len(nets) for nets in networks_by_size.values())

    fig_section1 = make_subplots(
        rows=n_rows_section1,
        cols=max_cols_section1,
        subplot_titles=[f"{size}" for size in network_sizes],
        vertical_spacing=0.1,
        horizontal_spacing=0.08,
    )

    for row_idx, size in enumerate(network_sizes, start=1):
        for col_idx, net in enumerate(networks_by_size[size], start=1):
            for strat in ["GeoMIP", "QNodes"]:
                data = all_data[net].get(strat, [])
                if not data:
                    continue
                indices = [d["index"] for d in data]
                times = [d["time"] for d in data]
                fig_section1.add_trace(
                    go.Scatter(
                        x=indices,
                        y=times,
                        mode="lines+markers",
                        name=strat,
                        line=dict(color=STRATEGY_COLORS[strat], width=1.5),
                        marker=dict(symbol=STRATEGY_SYMBOLS[strat], size=5),
                        showlegend=(row_idx == 1 and col_idx == 1),
                        legendgroup=strat,
                    ),
                    row=row_idx,
                    col=col_idx,
                )

    for row_idx in range(1, n_rows_section1 + 1):
        fig_section1.update_xaxes(title="Instance", row=row_idx, col=1)
        fig_section1.update_yaxes(
            title="Time (s)", row=row_idx, col=1, tickformat=".4f"
        )

    fig_section1.update_layout(
        title=dict(text="Section 1: Execution Time per Instance", font=dict(size=18)),
        height=300 * n_rows_section1,
        width=1200,
    )

    # === SECTION 2: Loss Correlation (specific pairs) ===
    n_cols_section2 = len(CORRELATION_PAIRS)

    fig_section2 = make_subplots(
        rows=n_rows_section1,
        cols=n_cols_section2,
        subplot_titles=[
            f"{size} - {x} vs {y}"
            for size in network_sizes
            for x, y in CORRELATION_PAIRS
        ],
        vertical_spacing=0.1,
        horizontal_spacing=0.025,
    )

    for row_idx, size in enumerate(network_sizes, start=1):
        for col_idx, (x_strat, y_strat) in enumerate(CORRELATION_PAIRS, start=1):
            for net in networks_by_size[size]:
                x_data = all_data[net].get(x_strat, [])
                y_data = all_data[net].get(y_strat, [])

                if not x_data or not y_data:
                    continue

                x_losses = {d["index"]: d["loss"] for d in x_data}
                x_vals = []
                y_vals = []
                indices = []

                for d in y_data:
                    if d["index"] in x_losses:
                        x_vals.append(x_losses[d["index"]])
                        y_vals.append(d["loss"])
                        indices.append(d["index"])

                if not x_vals:
                    continue

                fig_section2.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="markers",
                        name=net,
                        marker=dict(
                            color=STRATEGY_COLORS[y_strat],
                            symbol=STRATEGY_SYMBOLS[y_strat],
                            size=7,
                            line=dict(width=0.5, color="white"),
                        ),
                        showlegend=(row_idx == 1 and col_idx == 1),
                        legendgroup=f"{size}_{x_strat}_{y_strat}",
                        text=indices,
                        hovertemplate=f"Idx:%{{text}}<br>{x_strat}:%{{x:.4f}}<br>{y_strat}:%{{y:.4f}}<extra></extra>",
                    ),
                    row=row_idx,
                    col=col_idx,
                )

            # Diagonal reference line
            all_x = []
            all_y = []
            for d in x_data:
                if d["loss"] >= 0:
                    all_x.append(d["loss"])
            for d in y_data:
                if d["loss"] >= 0:
                    all_y.append(d["loss"])
            if all_x and all_y:
                min_val = min(all_x + all_y)
                max_val = max(all_x + all_y)
                fig_section2.add_trace(
                    go.Scatter(
                        x=[min_val, max_val],
                        y=[min_val, max_val],
                        mode="lines",
                        line=dict(color="gray", width=1, dash="dot"),
                        showlegend=False,
                        hoverinfo="skip",
                    ),
                    row=row_idx,
                    col=col_idx,
                )

    for row_idx in range(1, n_rows_section1 + 1):
        for col_idx in range(1, n_cols_section2 + 1):
            pair = CORRELATION_PAIRS[col_idx - 1]
            fig_section2.update_xaxes(
                title=pair[0], row=row_idx, col=col_idx, tickformat=".3f"
            )
            fig_section2.update_yaxes(
                title=pair[1], row=row_idx, col=col_idx, tickformat=".3f"
            )

    fig_section2.update_layout(
        title=dict(
            text="Section 2: Loss Correlation (X vs Y per Network)", font=dict(size=18)
        ),
        height=350 * n_rows_section1,
        width=220 * n_cols_section2,
    )

    # === SECTION 3: Boxplots of Execution Time grouped by network size ===
    n_cols_section3 = 1

    fig_section3 = make_subplots(
        rows=n_rows_section1,
        cols=n_cols_section3,
        subplot_titles=[f"{size} - Time Distribution" for size in network_sizes],
        vertical_spacing=0.1,
    )

    for row_idx, size in enumerate(network_sizes, start=1):
        for strat in STRATEGIES_ALL:
            times = []
            for net in networks_by_size[size]:
                data = all_data[net].get(strat, [])
                times.extend([d["time"] for d in data if d["time"] > 0])

            if not times:
                continue

            fig_section3.add_trace(
                go.Box(
                    y=times,
                    name=strat,
                    marker_color=STRATEGY_COLORS[strat],
                    boxmean=True,
                    showlegend=(row_idx == 1),
                    legendgroup=strat,
                ),
                row=row_idx,
                col=1,
            )

    fig_section3.update_yaxes(title="Time (s)", tickformat=".4f", row=1, col=1)

    fig_section3.update_layout(
        title=dict(
            text="Section 3: Execution Time Distribution (Boxplots)", font=dict(size=18)
        ),
        height=350 * n_rows_section1,
        width=800,
        showlegend=True,
        legend=dict(title="Strategy", yanchor="top", y=0.99, xanchor="right", x=1.2),
    )

    # Save all sections to single HTML with tabs
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ text-align: center; color: #333; }}
        .tab {{ overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; }}
        .tab button {{ background-color: inherit; border: none; outline: none; cursor: pointer; padding: 14px 16px; font-size: 16px; }}
        .tab button:hover {{ background-color: #ddd; }}
        .tab button.active {{ background-color: #ccc; }}
        .tabcontent {{ display: none; padding: 20px; border: 1px solid #ccc; border-top: none; }}
    </style>
</head>
<body>
    <h1>Benchmark Dashboard</h1>

    <div class="tab">
        <button class="tablinks" onclick="openTab(event, 'Section1')">Section 1: Execution Time</button>
        <button class="tablinks" onclick="openTab(event, 'Section2')">Section 2: Loss Correlation</button>
        <button class="tablinks" onclick="openTab(event, 'Section3')">Section 3: Time Boxplots</button>
    </div>

    <div id="Section1" class="tabcontent">
        {section1}
    </div>

    <div id="Section2" class="tabcontent">
        {section2}
    </div>

    <div id="Section3" class="tabcontent">
        {section3}
    </div>

    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }}
        document.getElementById("Section1").style.display = "block";
    </script>
</body>
</html>
    """

    section1_html = fig_section1.to_html(full_html=False, include_plotlyjs=False)
    section2_html = fig_section2.to_html(full_html=False, include_plotlyjs=False)
    section3_html = fig_section3.to_html(full_html=False, include_plotlyjs=False)

    final_html = html_template.format(
        section1=section1_html, section2=section2_html, section3=section3_html
    )

    with open(output_path, "w") as f:
        f.write(final_html)

    print(f"Dashboard saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark Dashboard Generator")
    parser.add_argument(
        "--networks",
        nargs="+",
        default=["N5B", "N10A"],
        help="Networks to include (default: N5B N10A)",
    )
    parser.add_argument(
        "--output",
        default="src/shared/output/benchmark_dashboard.html",
        help="Output HTML path",
    )

    args = parser.parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    create_dashboard(args.networks, args.output)


if __name__ == "__main__":
    main()
