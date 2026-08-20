"""
Professional graph generator for EduAI reports.

Creates publication-quality PNG charts for embedding in the PDF report:
1. Student-wise performance
2. Pass vs fail distribution
3. Rubric-wise average performance
4. Performance trend over time
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


# EduAI visual palette
NAVY = "#172554"
BLUE = "#2563EB"
TEAL = "#0F766E"
GREEN = "#16A34A"
RED = "#DC2626"
AMBER = "#D97706"
PURPLE = "#7C3AED"
SLATE = "#475569"
LIGHT_GRID = "#E2E8F0"
WHITE = "#FFFFFF"


def _base_figure(figsize=(10, 5.6)):
    fig, ax = plt.subplots(figsize=figsize, dpi=180)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LIGHT_GRID)
    ax.spines["bottom"].set_color(LIGHT_GRID)

    ax.grid(axis="y", color=LIGHT_GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)

    return fig, ax


def _finish(fig, path):
    fig.tight_layout(pad=1.5)
    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight",
        facecolor=WHITE,
        edgecolor="none",
    )
    plt.close(fig)


def _short_name(name, max_len=18):
    name = str(name)
    return name if len(name) <= max_len else name[: max_len - 1] + "…"


def generate_graphs(analytics: dict, output_dir: str, prefix: str = "report"):
    """
    Generate professional graphs from the analytics dictionary.

    Returns:
        dict[str, str]: graph name -> PNG file path
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    # ---------------------------------------------------------
    # 1. Student-wise Performance
    # ---------------------------------------------------------
    students = analytics.get("student_breakdown", []) or []

    if students:
        names = [_short_name(s.get("student_name", s.get("student_id", "Student"))) for s in students]
        percentages = [
            float(s.get("percentage", 0) or 0)
            for s in students
        ]

        fig, ax = _base_figure((10.5, 5.8))

        bars = ax.bar(
            range(len(names)),
            percentages,
            width=0.62,
            color=BLUE,
            edgecolor=WHITE,
            linewidth=0.8,
            zorder=3,
        )

        ax.axhline(
            40,
            color=RED,
            linestyle="--",
            linewidth=1.5,
            label="Pass threshold (40%)",
            zorder=4,
        )

        ax.set_title(
            "Student-wise Performance",
            fontsize=16,
            fontweight="bold",
            color=NAVY,
            pad=16,
        )
        ax.set_ylabel("Score (%)", fontsize=10, color=SLATE)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=25, ha="right", fontsize=9)
        ax.set_ylim(0, max(100, max(percentages, default=0) + 12))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.tick_params(axis="y", labelsize=9, colors=SLATE)
        ax.tick_params(axis="x", colors=SLATE)

        for bar, value in zip(bars, percentages):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 2,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color=NAVY,
            )

        ax.legend(
            loc="upper right",
            frameon=False,
            fontsize=9,
        )

        path = os.path.join(output_dir, f"{prefix}_student_bar.png")
        _finish(fig, path)
        paths["student_bar"] = path

    # ---------------------------------------------------------
    # 2. Pass vs Fail Distribution
    # ---------------------------------------------------------
    if students:
        pass_count = sum(
            1 for s in students
            if bool(s.get("pass_status", False))
        )
        fail_count = len(students) - pass_count

        fig, ax = plt.subplots(figsize=(7, 5.8), dpi=180)
        fig.patch.set_facecolor(WHITE)
        ax.set_facecolor(WHITE)

        counts = [pass_count, fail_count]
        labels = ["Pass", "Fail"]

        # If all students are in one category, keep the chart
        # visually meaningful rather than rendering a misleading blank slice.
        if sum(counts) == 0:
            counts = [1]
            labels = ["No evaluated students"]

        colors = [GREEN, RED][:len(counts)]

        wedges, _, autotexts = ax.pie(
            counts,
            labels=labels,
            colors=colors,
            startangle=90,
            counterclock=False,
            autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
            pctdistance=0.68,
            wedgeprops={
                "width": 0.42,
                "edgecolor": WHITE,
                "linewidth": 2,
            },
            textprops={
                "fontsize": 10,
                "color": NAVY,
            },
        )

        for text in autotexts:
            text.set_fontweight("bold")
            text.set_color(WHITE)

        ax.text(
            0,
            0,
            f"{len(students)}\nStudents",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=NAVY,
        )

        ax.set_title(
            "Pass vs Fail Distribution",
            fontsize=16,
            fontweight="bold",
            color=NAVY,
            pad=16,
        )

        path = os.path.join(output_dir, f"{prefix}_pass_fail_pie.png")
        _finish(fig, path)
        paths["pass_fail_pie"] = path

    # ---------------------------------------------------------
    # 3. Rubric-wise Average Performance
    # ---------------------------------------------------------
    rubric = analytics.get("rubric_analysis", {}) or {}

    if rubric:
        items = sorted(
            rubric.items(),
            key=lambda item: float(item[1] or 0),
            reverse=True,
        )

        criteria = [_short_name(k, 26) for k, _ in items]
        values = [float(v or 0) for _, v in items]

        fig, ax = _base_figure((9.5, max(5.2, 1.0 + len(criteria) * 0.65)))

        y_positions = range(len(criteria))
        bars = ax.barh(
            list(y_positions),
            values,
            color=TEAL,
            height=0.55,
            edgecolor=WHITE,
            linewidth=0.8,
            zorder=3,
        )

        ax.set_yticks(list(y_positions))
        ax.set_yticklabels(criteria, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Average score (%)", fontsize=10, color=SLATE)
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.tick_params(axis="x", labelsize=9, colors=SLATE)
        ax.tick_params(axis="y", colors=SLATE)

        ax.set_title(
            "Rubric-wise Average Performance",
            fontsize=16,
            fontweight="bold",
            color=NAVY,
            pad=16,
            loc="left",
        )

        for bar, value in zip(bars, values):
            ax.text(
                min(value + 1.5, 96),
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=NAVY,
            )

        path = os.path.join(output_dir, f"{prefix}_rubric_bar.png")
        _finish(fig, path)
        paths["rubric_bar"] = path

    # ---------------------------------------------------------
    # 4. Performance Trend
    # ---------------------------------------------------------
    trend = analytics.get("trend") or {}

    # Prefer the explicit trend mapping. If it is unavailable,
    # derive it from evaluation_history.
    if not trend:
        history = analytics.get("evaluation_history", []) or []
        for item in history:
            date_value = item.get("evaluation_date")
            avg_value = item.get("average_percentage")
            if date_value is not None and avg_value is not None:
                trend[str(date_value)] = float(avg_value or 0)

    if trend:
        trend_items = list(trend.items())

        def sort_key(item):
            raw = str(item[0])
            try:
                return datetime.fromisoformat(raw)
            except ValueError:
                return raw

        trend_items.sort(key=sort_key)

        dates = [str(k) for k, _ in trend_items]
        values = [float(v or 0) for _, v in trend_items]

        fig, ax = _base_figure((10, 5.6))

        ax.plot(
            range(len(dates)),
            values,
            color=AMBER,
            linewidth=2.8,
            marker="o",
            markersize=7,
            markerfacecolor=WHITE,
            markeredgewidth=2,
            markeredgecolor=AMBER,
            zorder=4,
        )

        ax.fill_between(
            range(len(dates)),
            values,
            0,
            color=AMBER,
            alpha=0.08,
        )

        ax.set_title(
            "Performance Trend Over Time",
            fontsize=16,
            fontweight="bold",
            color=NAVY,
            pad=16,
        )
        ax.set_ylabel("Average percentage (%)", fontsize=10, color=SLATE)
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=20, ha="right", fontsize=9)
        ax.set_ylim(
            max(0, min(values, default=0) - 10),
            min(100, max(values, default=100) + 10),
        )
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.tick_params(axis="y", labelsize=9, colors=SLATE)
        ax.tick_params(axis="x", colors=SLATE)

        for index, value in enumerate(values):
            ax.annotate(
                f"{value:.1f}%",
                (index, value),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="bold",
                color=NAVY,
            )

        path = os.path.join(output_dir, f"{prefix}_trend_line.png")
        _finish(fig, path)
        paths["trend_line"] = path

    return paths