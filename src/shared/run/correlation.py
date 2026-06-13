"""
Correlation plot: QNodes vs other strategies loss values.
X-axis = QNodes loss, Y-axis = GEO/K2GEO/K3GEO/K4GEO/K5GEO/K2QN/K3QN/K4QN/K5QN
"""

import csv
import json
import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.shared.casos import OUTPUT_DIR

NETWORKS = ["N5B", "N10A"]

STRATEGIES = [
    ("GEO", "GeometricSIA"),
    ("K2GEO", "KGeoMIP k=2"),
    ("K3GEO", "KGeoMIP k=3"),
    ("K4GEO", "KGeoMIP k=4"),
    ("K5GEO", "KGeoMIP k=5"),
    ("K2QN", "KQNodes k=2"),
    ("K3QN", "KQNodes k=3"),
    ("K4QN", "KQNodes k=4"),
    ("K5QN", "KQNodes k=5"),
]

STRATEGY_COLORS = {
    "GEO": "blue",
    "K2GEO": "green",
    "K3GEO": "darkgreen",
    "K4GEO": "lightgreen",
    "K5GEO": "lime",
    "K2QN": "red",
    "K3QN": "darkred",
    "K4QN": "salmon",
    "K5QN": "orange",
}

MARKER_SYMBOLS = {
    "GEO": "circle",
    "K2GEO": "square",
    "K3GEO": "diamond",
    "K4GEO": "triangle-up",
    "K5GEO": "triangle-down",
    "K2QN": "circle-open",
    "K3QN": "square-open",
    "K4QN": "diamond-open",
    "K5QN": "triangle-up-open",
}


def load_losses(network: str, strategy_suffix: str) -> dict[str, float]:
    """Load index->loss mapping from CSV."""
    filepath = f"{OUTPUT_DIR}/{network}-{strategy_suffix}.csv"
    if not os.path.exists(filepath):
        return {}

    losses = {}
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            losses[row["index"]] = float(row["loss"])
    return losses


def generate_correlation_html(networks: list[str], output_path: str) -> None:
    """Generate correlation plot HTML."""

    # Load all data
    all_data = {}
    for net in networks:
        all_data[net] = {}
        # QNodes baseline
        all_data[net]["QN"] = load_losses(net, "QN")
        # GEO
        all_data[net]["GEO"] = load_losses(net, "GEO")
        # K*GEO
        for k in [2, 3, 4, 5]:
            all_data[net][f"K{k}GEO"] = load_losses(net, f"K{k}GEO")
        # K*QN
        for k in [2, 3, 4, 5]:
            all_data[net][f"K{k}QN"] = load_losses(net, f"K{k}QN")

    n_cols = len(networks)
    n_rows = 1

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[f"{net} - Loss Correlation (QNodes vs Others)" for net in networks],
        horizontal_spacing=0.12,
        vertical_spacing=0.2
    )

    for col_idx, net in enumerate(networks, start=1):
        qn_losses = all_data[net]["QN"]

        for strat, label in STRATEGIES:
            strat_losses = all_data[net].get(strat, {})

            # Build x, y arrays aligned by index
            x_vals = []
            y_vals = []
            indices = []

            for idx, qn_loss in qn_losses.items():
                if idx in strat_losses:
                    x_vals.append(qn_loss)
                    y_vals.append(strat_losses[idx])
                    indices.append(idx)

            if not x_vals:
                continue

            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='markers',
                    name=label,
                    marker=dict(
                        color=STRATEGY_COLORS[strat],
                        symbol=MARKER_SYMBOLS[strat],
                        size=8,
                        line=dict(width=1, color="white")
                    ),
                    showlegend=(col_idx == 1),
                    legendgroup=strat,
                    text=indices,
                    hovertemplate=f"Index: %{{text}}<br>QNodes: %{{x:.4f}}<br>{label}: %{{y:.4f}}<extra></extra>"
                ),
                row=1, col=col_idx
            )

        # Add diagonal reference line (perfect correlation)
        all_x = list(all_data[net]["QN"].values())
        all_y = []
        for strat, _ in STRATEGIES:
            all_y.extend(list(all_data[net].get(strat, {}).values()))
        if all_x and all_y:
            min_val = min(all_x)
            max_val = max(all_x)
            fig.add_trace(
                go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    line=dict(color='gray', width=1, dash='dot'),
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=1, col=col_idx
            )

    # Update layout
    fig.update_layout(
        title=dict(text="Loss Correlation: QNodes vs All Strategies", font=dict(size=20)),
        legend=dict(
            title="Strategy",
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=1.02,
            font=dict(size=10)
        ),
        hovermode='closest',
        template='plotly_white',
        height=500,
        width=400 * n_cols
    )

    # Update axes
    for col_idx in range(1, n_cols + 1):
        fig.update_xaxes(title="QNodes Loss", row=1, col=col_idx)
        fig.update_yaxes(title="Strategy Loss", row=1, col=col_idx)

    fig.write_html(output_path)
    print(f"Correlation plot saved to {output_path}")


if __name__ == "__main__":
    generate_correlation_html(NETWORKS, f"{OUTPUT_DIR}/loss_correlation.html")