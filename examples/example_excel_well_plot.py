"""
Example: Plot well production and injection history from an Excel workbook.

The workbook is expected to have:
- Column B: date
- Column C: well name
- Columns D to I: Qgm, Qwm, Qom, Qclm, Qwim, Qgim

The script lists the wells found in the workbook and lets the user choose one
interactively before plotting the time series.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError as exc:  # pragma: no cover - import guard for runtime use
    raise SystemExit(
        "openpyxl is required to read Excel files. Install dependencies with "
        "'pip install -r requirements.txt'."
    ) from exc


VARIABLES = [
    ("Qgm", "Gas production"),
    ("Qwm", "Water production"),
    ("Qom", "Oil production"),
    ("Qclm", "Condensate production"),
    ("Qwim", "Water injection"),
    ("Qgim", "Gas injection"),
]


def find_workbook_path() -> Path:
    """Return the default workbook path or the first matching Excel file."""
    script_dir = Path(__file__).resolve().parent.parent
    default_path = script_dir / "SMC_RicardoPortella.xlsx"
    if default_path.exists():
        return default_path

    matches = sorted(script_dir.glob("SMC_RicardoPortella*.xls*"))
    if not matches:
        raise FileNotFoundError(
            "Could not find SMC_RicardoPortella.xlsx in the repository root."
        )
    return matches[0]


def normalize_well_name(value: object) -> str:
    """Convert workbook cell values to a clean well name string."""
    if value is None:
        return ""
    return str(value).strip()


def parse_date(value: object) -> datetime:
    """Validate and normalize date values from the workbook."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, str):
        for parser in (datetime.fromisoformat,):
            try:
                return parser(value)
            except ValueError:
                continue
    raise ValueError(f"Unsupported date value: {value!r}")


def read_workbook(filepath: Path, sheet_name: str | None = None) -> dict[str, dict[str, list]]:
    """Read the workbook and group rows by well name."""
    workbook = load_workbook(filepath, data_only=True, read_only=True)
    worksheet = workbook[sheet_name] if sheet_name else workbook[workbook.sheetnames[0]]

    wells: dict[str, dict[str, list]] = defaultdict(lambda: {"date": [], **{key: [] for key, _ in VARIABLES}})

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        if len(row) < 9:
            continue

        date_value = row[1]
        well_name = normalize_well_name(row[2])
        if not date_value or not well_name:
            continue

        try:
            date = parse_date(date_value)
        except ValueError:
            continue

        well_bucket = wells[well_name]
        well_bucket["date"].append(date)

        for index, (variable_name, _) in enumerate(VARIABLES, start=3):
            value = row[index]
            if value is None or value == "":
                well_bucket[variable_name].append(None)
            else:
                well_bucket[variable_name].append(float(value))

    if not wells:
        raise ValueError("No wells were found in the workbook.")

    return wells


def choose_well(wells: dict[str, dict[str, list]]) -> str:
    """Prompt the user to select a well from the available list."""
    well_names = sorted(wells)
    print("Available wells:")
    for index, well_name in enumerate(well_names, start=1):
        print(f"  {index}. {well_name}")

    if len(well_names) == 1:
        print(f"Only one well found, selecting {well_names[0]} automatically.\n")
        return well_names[0]

    while True:
        selection = input("Choose a well by number or name: ").strip()
        if not selection:
            continue

        if selection.isdigit():
            index = int(selection)
            if 1 <= index <= len(well_names):
                return well_names[index - 1]

        if selection in wells:
            return selection

        matches = [well_name for well_name in well_names if selection.lower() in well_name.lower()]
        if len(matches) == 1:
            return matches[0]

        print("Invalid selection. Try again.")


def plot_well_history(well_name: str, well_data: dict[str, list]) -> None:
    """Plot the selected well time series on a single chart with two y-axes."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.dates import DateFormatter, YearLocator
    except ImportError as exc:  # pragma: no cover - import guard for runtime use
        raise SystemExit(
            "matplotlib is required to plot the workbook data. Install dependencies "
            "with 'pip install -r requirements.txt'."
        ) from exc

    dates = well_data["date"]
    paired_series = sorted(zip(dates, *[well_data[var] for var, _ in VARIABLES]), key=lambda item: item[0])

    if not paired_series:
        raise ValueError(f"No data available for well {well_name!r}.")

    sorted_dates = [item[0] for item in paired_series]
    gas_series = {
        "Qgm": [item[1] for item in paired_series],
        "Qgim": [item[6] for item in paired_series],
    }
    other_series = {
        "Qwm": [item[2] for item in paired_series],
        "Qom": [item[3] for item in paired_series],
        "Qclm": [item[4] for item in paired_series],
        "Qwim": [item[5] for item in paired_series],
    }

    fig, axis_left = plt.subplots(figsize=(14, 7))
    axis_right = axis_left.twinx()

    gas_colors = {"Qgm": "red", "Qgim": "orange"}
    other_colors = {
        "Qwm": "blue",
        "Qom": "black",
        "Qclm": "violet",
        "Qwim": "lightblue",
    }

    for variable_name, values in gas_series.items():
        axis_left.plot(
            sorted_dates,
            values,
            marker="o",
            linewidth=1.6,
            color=gas_colors[variable_name],
            label=variable_name,
        )

    for variable_name, values in other_series.items():
        axis_right.plot(
            sorted_dates,
            values,
            marker="o",
            linewidth=1.6,
            linestyle="--",
            color=other_colors[variable_name],
            label=variable_name,
        )

    axis_left.set_ylabel("Qg / Qgi")
    axis_right.set_ylabel("Other rates")
    axis_left.set_ylim(bottom=0)
    axis_right.set_ylim(bottom=0)
    axis_left.grid(True, alpha=0.3)

    axis_left.xaxis.set_major_locator(YearLocator())
    axis_left.xaxis.set_major_formatter(DateFormatter("%Y"))
    axis_left.set_xlabel("Year")

    left_handles, left_labels = axis_left.get_legend_handles_labels()
    right_handles, right_labels = axis_right.get_legend_handles_labels()
    axis_left.legend(left_handles + right_handles, left_labels + right_labels, loc="upper left", ncol=2)

    fig.suptitle(f"Well history: {well_name}", fontsize=14)
    fig.tight_layout()
    plt.show()


def main() -> None:
    workbook_path = find_workbook_path()
    print(f"Reading workbook: {workbook_path}")

    wells = read_workbook(workbook_path)
    selected_well = choose_well(wells)
    print(f"Plotting well: {selected_well}")

    plot_well_history(selected_well, wells[selected_well])


if __name__ == "__main__":
    main()