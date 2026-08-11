"""
Example: Extrapolate well production decline from an Excel workbook.

The workbook is expected to contain at least the following columns:
- Poço
- Categoria
- Classe
- Fluido
- Operação
- Zona
- Início Produção
- Qg (M m3/dia)
- Qo (m3/dia)
- Qw (m3/dia)
- Di
- b

The script reads the workbook and applies decline extrapolation where
q(t) follows the hyperbolic model q = qi / (1 + b * Di * t)^(1/b), with
automatic fallback to the exponential model q(t) = qi * exp(-Di * t) when b = 0.
Time t is expressed in years. It then plots:
- flow rate versus time,
- cumulative produced volume until the production threshold is reached,
- or a combined curve for all wells of a selected fluid.

For gas wells, the extrapolation stops when the flow is lower than 2 thousand m3/day
(in the workbook units this corresponds to 2.0).
For oil wells, it stops when the flow is lower than 1 m3/day.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover - runtime guard
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

if TYPE_CHECKING:
    import tkinter

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "matplotlib is required to plot the results. Install dependencies with "
        "'pip install -r requirements.txt'."
    ) from exc

try:
    from openpyxl import Workbook, load_workbook
except ImportError as exc:  # pragma: no cover - import guard for runtime use
    raise SystemExit(
        "openpyxl is required to read Excel files. Install dependencies with "
        "'pip install -r requirements.txt'."
    ) from exc


COLUMN_ALIASES = {
    "Poço": ("poco", "poço", "well", "wellname", "nomepoco"),
    "Categoria": ("categoria",),
    "Classe": ("classe",),
    "Fluido": ("fluido",),
    "Operação": ("operacao", "operacão"),
    "Zona": ("zona",),
    "Início Produção": ("inicioproducao", "inicioproducao", "inicio_producao", "inicio", "startdate"),
    "Qg": ("qg", "qgmm3dia", "qgmm3d", "qgm3dia", "qgm3d"),
    "Qo": ("qo", "qom3dia", "qom3d"),
    "Qw": ("qw", "qwm3dia", "qwm3d"),
    "Di": ("di", "di1ano", "diano", "declini", "declinio"),
    "b": ("b",),
}


EXTRAPOLATION_END_DATE: datetime = datetime(2052, 12, 31)


def normalize_header(value: object) -> str:
    """Normalize workbook headers to a comparable form."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    replacements = str.maketrans({
        "á": "a",
        "à": "a",
        "â": "a",
        "ã": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁰": "0",
    })
    text = text.translate(replacements)
    return "".join(ch for ch in text if ch.isalnum())


def ask_workbook_path() -> Path:
    """Ask the user for the workbook path at application startup."""
    if tk is not None and filedialog is not None:
        root = tk.Tk()
        root.withdraw()
        default_dir = str(Path(__file__).resolve().parent.parent)
        selected = filedialog.askopenfilename(
            title="Select Excel workbook",
            filetypes=[("Excel files", "*.xlsx *.xlsm *.xls")],
            initialdir=default_dir,
        )
        root.destroy()

        if selected:
            return Path(selected)

    for candidate in [
        Path(__file__).resolve().parent.parent / "SMC_Reservas.xlsx",
        Path(__file__).resolve().parent.parent / "SMC_Reservas.xlsm",
    ]:
        if candidate.exists():
            return candidate

    while True:
        typed_path = input("Enter the workbook path (.xlsx/.xlsm/.xls): ").strip().strip('"')
        if not typed_path:
            print("Path cannot be empty. Try again.")
            continue

        candidate = Path(typed_path)
        if candidate.exists() and candidate.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            return candidate

        print("Invalid workbook path. Try again.")


def parse_date(value: object) -> datetime:
    """Convert cell values to a datetime object."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Empty date")
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Unsupported date value: {value!r}") from exc
    raise ValueError(f"Unsupported date value: {value!r}")


def next_month_start(value: datetime) -> datetime:
    """Return the first day of the month following the provided date."""
    if value.month == 12:
        return datetime(value.year + 1, 1, 1)
    return datetime(value.year, value.month + 1, 1)


def month_starts_between(start_date: datetime, end_date: datetime) -> list[datetime]:
    """Build a list of month starts on/after start_date and up to end_date."""
    month_start = datetime(start_date.year, start_date.month, 1)
    if month_start < start_date:
        month_start = next_month_start(start_date)

    dates: list[datetime] = []
    current = month_start
    while current <= end_date:
        dates.append(current)
        current = next_month_start(current)
    return dates


def format_export_date(value: object) -> str:
    """Format date values for exported spreadsheets as dd/mm/yyyy."""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def classify_fluid(value: object) -> str:
    """Classify the fluid as gas, oil or other."""
    text = str(value or "").strip().lower()
    if "gas" in text or "gás" in text:
        return "gas"
    if "oleo" in text or "oil" in text or "óleo" in text:
        return "oil"
    return "other"


def category_class_priority(categoria: str, classe: str) -> int:
    """Return the priority rank for extrapolation selection (lower is better)."""
    categoria_norm = normalize_header(categoria)
    classe_norm = normalize_header(classe)

    if categoria_norm == "p1" and classe_norm == "pdp":
        return 0
    if categoria_norm == "p1" and classe_norm == "pdnp":
        return 1
    if categoria_norm == "p1" and classe_norm == "pud":
        return 2
    if categoria_norm == "p2":
        return 3
    if categoria_norm == "p3":
        return 4
    return 5


def read_workbook(filepath: Path, sheet_name: str | None = None) -> dict[str, dict[str, Any]]:
    """Read the well metadata workbook and group the data by well name."""
    workbook = load_workbook(filepath, data_only=True, read_only=True)
    try:
        worksheet = workbook[sheet_name] if sheet_name else workbook[workbook.sheetnames[0]]
        rows = list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not rows:
        raise ValueError("The workbook is empty.")

    header_row = rows[0]
    normalized_headers = [normalize_header(cell) for cell in header_row]
    column_map: dict[str, int] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            try:
                idx = normalized_headers.index(alias)
            except ValueError:
                continue
            column_map[canonical] = idx
            break

    required_columns = {"Poço", "Início Produção", "Qg", "Qo", "Di", "b", "Fluido"}
    missing = [name for name in required_columns if name not in column_map]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    wells: dict[str, dict[str, Any]] = {}
    for row in rows[1:]:
        if not row or not any(value is not None and str(value).strip() != "" for value in row):
            continue

        well_name = str(row[column_map["Poço"]]).strip() if column_map["Poço"] < len(row) else ""
        if not well_name:
            continue

        try:
            start_date = parse_date(row[column_map["Início Produção"]])
            qg = float(row[column_map["Qg"]])
            qo = float(row[column_map["Qo"]])
            qw = float(row[column_map["Qw"]]) if "Qw" in column_map and row[column_map["Qw"]] is not None else 0.0
            di = float(row[column_map["Di"]])
            b = float(row[column_map["b"]])
        except (TypeError, ValueError):
            continue

        fluid = classify_fluid(row[column_map["Fluido"]] if column_map["Fluido"] < len(row) else "")
        if fluid not in {"gas", "oil"}:
            continue

        qi = qg if fluid == "gas" else qo

        unique_key = well_name
        duplicate_index = 2
        while unique_key in wells:
            unique_key = f"{well_name}__{duplicate_index}"
            duplicate_index += 1

        wells[unique_key] = {
            "name": well_name,
            "categoria": str(row[column_map.get("Categoria", 0)] or "") if "Categoria" in column_map else "",
            "classe": str(row[column_map.get("Classe", 0)] or "") if "Classe" in column_map else "",
            "fluido": fluid,
            "operacao": str(row[column_map.get("Operação", 0)] or "") if "Operação" in column_map else "",
            "zona": str(row[column_map.get("Zona", 0)] or "") if "Zona" in column_map else "",
            "start_date": start_date,
            "qg": qg,
            "qo": qo,
            "qw": qw,
            "qi": qi,
            "di": di,
            "b": b,
        }

    if not wells:
        raise ValueError("No gas or oil wells were found in the workbook.")

    return resolve_duplicate_well_rows(wells)


def decline_rate(qi: float, di: float, b: float, t_years: np.ndarray | float) -> np.ndarray:
    """Return decline rate using hyperbolic model and exponential fallback when b is zero."""
    t_array = np.asarray(t_years, dtype=float)

    if np.isclose(b, 0.0):
        return qi * np.exp(-di * t_array)

    denominator = 1.0 + b * di * t_array
    result = np.zeros_like(t_array, dtype=float)
    valid = denominator > 0.0
    if np.any(valid):
        result[valid] = qi / np.power(denominator[valid], 1.0 / b)
    return result


def build_decline_series(well: dict[str, Any], threshold: float) -> dict[str, np.ndarray]:
    """Build the decline curve and cumulative volume for a well."""
    if all(key in well for key in ("resolved_dates", "resolved_q", "resolved_cum")):
        return {
            "dates": np.array(well["resolved_dates"], dtype=object),
            "t_years": np.array(well.get("resolved_t_years", []), dtype=float),
            "q": np.array(well["resolved_q"], dtype=float),
            "cum": np.array(well["resolved_cum"], dtype=float),
        }

    qi = float(well["qi"])
    di = float(well["di"])
    b = float(well.get("b", 0.0))
    start_date = well["start_date"]

    if qi <= 0 or qi <= threshold:
        return {
            "dates": np.array([start_date], dtype=object),
            "t_years": np.array([0.0]),
            "q": np.array([0.0]),
            "cum": np.array([0.0]),
        }

    if EXTRAPOLATION_END_DATE is not None:
        max_date = EXTRAPOLATION_END_DATE
    else:
        max_years = 50.0
        max_date = start_date + timedelta(days=max_years * 365.25)

    date_points: list[datetime] = [start_date]
    t_points: list[float] = [0.0]
    q_points: list[float] = [qi]
    cumulative_points: list[float] = [0.0]

    for current_date in month_starts_between(start_date, max_date):
        if current_date <= start_date:
            continue

        t_years = (current_date - start_date).days / 365.25
        q_value = float(decline_rate(qi, di, b, t_years))
        if q_value <= threshold:
            break

        previous_date = date_points[-1]
        previous_q = q_points[-1]
        dt_days = (current_date - previous_date).days
        cumulative_value = cumulative_points[-1] + 0.5 * (previous_q + q_value) * dt_days

        date_points.append(current_date)
        t_points.append(t_years)
        q_points.append(float(q_value))
        cumulative_points.append(float(cumulative_value))

    dates = np.array(date_points, dtype=object)
    t_years = np.array(t_points, dtype=float)
    q_values = np.array(q_points, dtype=float)
    cumulative = np.array(cumulative_points, dtype=float)

    return {
        "dates": dates,
        "t_years": t_years,
        "q": q_values,
        "cum": cumulative,
    }


def resolve_duplicate_well_rows(wells: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Resolve duplicate well rows (same visible name and fluid) into a single effective series."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    grouped_by_name: dict[str, list[dict[str, Any]]] = {}
    for well in wells.values():
        well_name = str(well["name"])
        fluid = str(well["fluido"])
        grouped.setdefault((well_name, fluid), []).append(well)
        grouped_by_name.setdefault(well_name, []).append(well)

    resolved: dict[str, dict[str, Any]] = {}
    for (well_name, fluid), rows in grouped.items():
        # A row represents a production interval that must be truncated when a
        # newer row for the same well starts, even if fluid changes.
        name_rows = grouped_by_name.get(well_name, rows)
        sorted_starts = sorted({row["start_date"] for row in name_rows})
        next_start_by_row: list[datetime | None] = []
        for row in rows:
            next_start = next(
                (start for start in sorted_starts if start > row["start_date"]),
                None,
            )
            next_start_by_row.append(next_start)

        threshold = get_threshold(fluid)
        ranks = [category_class_priority(str(row.get("categoria", "")), str(row.get("classe", ""))) for row in rows]
        series_list = [build_decline_series(row, threshold) for row in rows]
        effective_end_dates: list[datetime] = []
        for series, next_start in zip(series_list, next_start_by_row):
            series_end = series["dates"][-1]
            if next_start is None:
                effective_end_dates.append(series_end)
            else:
                effective_end_dates.append(min(series_end, next_start))

        min_start = min(row["start_date"] for row in rows)
        max_end = max(effective_end_dates)
        common_dates = month_starts_between(min_start, max_end)
        if not common_dates:
            common_dates = [min_start]
        elif common_dates[0] != min_start:
            common_dates = [min_start] + common_dates
        if not common_dates:
            continue

        selected_q: list[float] = []
        selected_categoria: list[str] = []
        selected_classe: list[str] = []
        selected_zona: list[str] = []

        for date_value in common_dates:
            best_q = 0.0
            best_idx: int | None = None

            for idx, row in enumerate(rows):
                start_date = row["start_date"]
                if date_value < start_date:
                    continue

                next_start = next_start_by_row[idx]
                if next_start is not None and date_value >= next_start:
                    # This interval is closed when the next change starts.
                    continue

                t_years = (date_value - start_date).days / 365.25
                q_value = float(decline_rate(float(row["qi"]), float(row["di"]), float(row.get("b", 0.0)), t_years))
                if q_value <= threshold:
                    q_value = 0.0

                if q_value > best_q + 1e-12:
                    best_q = q_value
                    best_idx = idx
                elif abs(q_value - best_q) <= 1e-12 and q_value > 0.0 and best_idx is not None:
                    if ranks[idx] < ranks[best_idx]:
                        best_idx = idx

            selected_q.append(float(best_q))
            if best_idx is None:
                selected_categoria.append("")
                selected_classe.append("")
                selected_zona.append("")
            else:
                selected_categoria.append(str(rows[best_idx].get("categoria", "")))
                selected_classe.append(str(rows[best_idx].get("classe", "")))
                selected_zona.append(str(rows[best_idx].get("zona", "")))

        cumulative_points: list[float] = [0.0]
        for i in range(1, len(common_dates)):
            dt_days = (common_dates[i] - common_dates[i - 1]).days
            # Use left-point integration for resolved duplicate series so step
            # changes (for example, shut-in to re-open) do not create phantom
            # production before the effective change date.
            cumulative_value = cumulative_points[-1] + selected_q[i - 1] * dt_days
            cumulative_points.append(float(cumulative_value))

        min_rank_index = min(range(len(rows)), key=lambda index: ranks[index])
        representative = rows[min_rank_index]
        all_categories = " | ".join(
            sorted({str(row.get("categoria", "")).strip() for row in rows if str(row.get("categoria", "")).strip()})
        )
        all_classes = " | ".join(
            sorted({str(row.get("classe", "")).strip() for row in rows if str(row.get("classe", "")).strip()})
        )

        t_years_points = np.array(
            [((date_value - common_dates[0]).days / 365.25) for date_value in common_dates],
            dtype=float,
        )
        resolved_well = {
            **representative,
            "categoria": all_categories or str(representative.get("categoria", "")),
            "classe": all_classes or str(representative.get("classe", "")),
            "start_date": common_dates[0],
            "qi": float(selected_q[0]) if selected_q else float(representative.get("qi", 0.0)),
            "resolved_dates": common_dates,
            "resolved_t_years": t_years_points.tolist(),
            "resolved_q": selected_q,
            "resolved_cum": cumulative_points,
            "resolved_categoria": selected_categoria,
            "resolved_classe": selected_classe,
            "resolved_zona": selected_zona,
        }

        key = well_name
        if key in resolved:
            key = f"{well_name}__{fluid}"
        resolved[key] = resolved_well

    return resolved


def get_threshold(fluid: str) -> float:
    """Return the production threshold by fluid in the same units as the workbook values."""
    return 2.0 if fluid == "gas" else 1.0


def qi_source_label(fluid: str) -> str:
    """Return the source column name used as qi for the given fluid."""
    return "Qg (M m3/dia)" if fluid == "gas" else "Qo (m3/dia)"


def fluid_label(fluid: str) -> str:
    """Return a user-friendly fluid label for exports."""
    return "Gás" if fluid == "gas" else "Óleo"


def combine_text_field(wells: list[dict[str, Any]], field: str) -> str:
    """Combine unique text values from a field across wells."""
    return " | ".join(
        sorted({str(well.get(field, "")).strip() for well in wells if str(well.get(field, "")).strip()})
    )


def category_bucket(value: object) -> str:
    """Normalize category values to P1, P2, P3 buckets."""
    text = normalize_header(value)
    if text == "p1":
        return "P1"
    if text == "p2":
        return "P2"
    if text == "p3":
        return "P3"
    return ""


def build_category_cumulative_series(
    wells: list[dict[str, Any]],
    fluid: str,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Build cumulative production series by category (P1/P2/P3) for a fluid."""
    fluid_wells = [well for well in wells if str(well.get("fluido", "")) == fluid]
    if not fluid_wells:
        return np.array([], dtype=object), {"P1": np.array([]), "P2": np.array([]), "P3": np.array([])}

    series_list = [build_decline_series(well, get_threshold(fluid)) for well in fluid_wells]
    min_start = min(well["start_date"] for well in fluid_wells)
    max_end = max(series["dates"][-1] for series in series_list)

    common_dates = month_starts_between(min_start, max_end)
    if not common_dates:
        common_dates = [min_start]
    if common_dates[0] != min_start:
        common_dates = [min_start] + common_dates

    common_dates_array = np.array(common_dates, dtype=object)

    category_cumulative_sum: dict[str, np.ndarray] = {
        "P1": np.zeros(len(common_dates_array), dtype=float),
        "P2": np.zeros(len(common_dates_array), dtype=float),
        "P3": np.zeros(len(common_dates_array), dtype=float),
    }

    for well, series in zip(fluid_wells, series_list):
        dates = np.array(series["dates"], dtype=object)
        cumulative = np.array(series["cum"], dtype=float)
        if len(dates) == 0:
            continue

        resolved_category = list(well.get("resolved_categoria", []))

        # Partition each well cumulative increment to the active category at the
        # beginning of the interval [i-1, i].
        per_bucket_cum: dict[str, np.ndarray] = {
            "P1": np.zeros(len(dates), dtype=float),
            "P2": np.zeros(len(dates), dtype=float),
            "P3": np.zeros(len(dates), dtype=float),
        }

        for i in range(1, len(dates)):
            for bucket in ("P1", "P2", "P3"):
                per_bucket_cum[bucket][i] = per_bucket_cum[bucket][i - 1]

            delta_cum = float(cumulative[i] - cumulative[i - 1])
            category_value = resolved_category[i - 1] if (i - 1) < len(resolved_category) else well.get("categoria", "")
            bucket = category_bucket(category_value)
            if bucket:
                per_bucket_cum[bucket][i] += delta_cum

        offsets = np.array([(date_value - well["start_date"]).days for date_value in dates], dtype=float)
        common_offsets = np.array([(date_value - well["start_date"]).days for date_value in common_dates_array], dtype=float)

        for bucket in ("P1", "P2", "P3"):
            bucket_cum = per_bucket_cum[bucket]
            interpolated = np.interp(
                common_offsets,
                offsets,
                bucket_cum,
                left=0.0,
                right=float(bucket_cum[-1]),
            )
            category_cumulative_sum[bucket] += interpolated

    return common_dates_array, category_cumulative_sum


def build_combined_series(wells: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate the decline rates for all wells of a given fluid on a common time grid."""
    if not wells:
        return np.array([], dtype=object), np.array([], dtype=float)

    series_list = [build_decline_series(well, get_threshold(well["fluido"])) for well in wells]
    min_start = min(well["start_date"] for well in wells)
    max_end = max(series["dates"][-1] for series in series_list)

    common_dates = month_starts_between(min_start, max_end)
    if not common_dates:
        common_dates = [min_start]

    common_dates_array = np.array(common_dates, dtype=object)
    summed_values = np.zeros(len(common_dates_array), dtype=float)

    for well, series in zip(wells, series_list):
        thresholds = get_threshold(well["fluido"])
        offset_days = np.array([(date_value - well["start_date"]).days for date_value in common_dates_array], dtype=float)
        valid_mask = offset_days >= 0.0
        if not np.any(valid_mask):
            continue

        t_years = offset_days[valid_mask] / 365.25
        q_values = decline_rate(float(well["qi"]), float(well["di"]), float(well.get("b", 0.0)), t_years)
        q_values = np.where(q_values > thresholds, q_values, 0.0)
        summed_values[valid_mask] += q_values

    return common_dates_array, summed_values


def build_combined_cumulative_series(wells: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate cumulative volume for all wells by calendar date on a common time grid."""
    if not wells:
        return np.array([], dtype=object), np.array([], dtype=float)

    series_list = [build_decline_series(well, get_threshold(well["fluido"])) for well in wells]
    min_start = min(well["start_date"] for well in wells)
    max_end = max(series["dates"][-1] for series in series_list)

    common_dates = month_starts_between(min_start, max_end)
    if not common_dates:
        common_dates = [min_start]

    common_dates_array = np.array(common_dates, dtype=object)
    summed_values = np.zeros(len(common_dates_array), dtype=float)

    for well, series in zip(wells, series_list):
        offsets = np.array([(date_value - well["start_date"]).days for date_value in series["dates"]], dtype=float)
        cumulative = np.array(series["cum"], dtype=float)
        if len(offsets) == 0:
            continue

        common_offsets = np.array([(date_value - well["start_date"]).days for date_value in common_dates_array], dtype=float)
        interpolated = np.interp(
            common_offsets,
            offsets,
            cumulative,
            left=0.0,
            right=float(cumulative[-1]),
        )
        summed_values += interpolated

    return common_dates_array, summed_values


def group_wells_by_name_and_fluid(wells: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Group well rows by visible well name and fluid."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for well in wells:
        key = (str(well["name"]), str(well["fluido"]))
        grouped.setdefault(key, []).append(well)
    return grouped


def combine_zone_labels(wells: list[dict[str, Any]]) -> str:
    """Combine zone values for grouped well rows."""
    zones = sorted({str(well.get("zona", "")).strip() for well in wells if str(well.get("zona", "")).strip()})
    return " | ".join(zones)


def detect_simultaneous_zone_production(wells: list[dict[str, Any]]) -> list[str]:
    """Detect overlapping production periods for different zones of the same well."""
    grouped_by_name: dict[str, list[dict[str, Any]]] = {}
    for well in wells:
        grouped_by_name.setdefault(str(well["name"]), []).append(well)

    warnings: list[str] = []
    for well_name, rows in grouped_by_name.items():
        if len(rows) < 2:
            continue

        intervals: list[tuple[datetime, datetime, str]] = []
        for row in rows:
            zone = str(row.get("zona", "")).strip() or "(sem zona)"
            series = build_decline_series(row, get_threshold(str(row["fluido"])))
            start = row["start_date"]
            end = series["dates"][-1]
            intervals.append((start, end, zone))

        for i in range(len(intervals)):
            start_i, end_i, zone_i = intervals[i]
            fluid_i = str(rows[i].get("fluido", ""))
            for j in range(i + 1, len(intervals)):
                start_j, end_j, zone_j = intervals[j]
                fluid_j = str(rows[j].get("fluido", ""))
                if fluid_i != fluid_j:
                    continue
                if zone_i == zone_j:
                    continue

                has_overlap = start_i <= end_j and start_j <= end_i
                if has_overlap:
                    overlap_start = max(start_i, start_j).strftime("%d/%m/%Y")
                    overlap_end = min(end_i, end_j).strftime("%d/%m/%Y")
                    warnings.append(
                        f"Poço {well_name}: sobreposição entre zonas {zone_i} e {zone_j} "
                        f"de {overlap_start} até {overlap_end}."
                    )

    return warnings


class ProductionDeclineApp:
    """Simple Tkinter-based GUI for plotting the decline extrapolation."""

    def __init__(self, master: tkinter.Tk, workbook_path: Path):
        self.master = master
        self.workbook_path = workbook_path
        self.wells = read_workbook(workbook_path)
        self.zone_overlap_warnings = detect_simultaneous_zone_production(list(self.wells.values()))
        self.well_names = sorted({well["name"] for well in self.wells.values()})
        self.well_names = ["Todos os poços"] + self.well_names

        self.selected_well = tk.StringVar(value=self.well_names[0])
        self.selected_fluid = tk.StringVar(value="Gás")
        self.selected_plot = tk.StringVar(value="Vazão")

        self.master.title("Extrapolação de produção de poços")
        self.master.geometry("1100x700")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()

        if self.zone_overlap_warnings:
            warning_lines = "\n".join(self.zone_overlap_warnings[:10])
            if len(self.zone_overlap_warnings) > 10:
                warning_lines += f"\n... e mais {len(self.zone_overlap_warnings) - 10} ocorrência(s)."

            warning_message = (
                "Foram detectadas sobreposições de produção simultânea em zonas diferentes:\n\n"
                f"{warning_lines}"
            )
            if messagebox is not None:
                messagebox.showwarning("Aviso de consistência física", warning_message)
            else:
                print(warning_message)

        self.refresh_plot()

    def on_close(self) -> None:
        """Ensure Tk and Matplotlib resources are released on window close."""
        try:
            if hasattr(self, "figure"):
                plt.close(self.figure)
        finally:
            self.master.quit()
            self.master.destroy()

    def create_widgets(self) -> None:
        controls = ttk.Frame(self.master, padding=10)
        controls.pack(fill="x")

        ttk.Label(controls, text="Poço").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        well_combo = ttk.Combobox(
            controls,
            textvariable=self.selected_well,
            values=self.well_names,
            state="readonly",
            width=25,
        )
        well_combo.grid(row=0, column=1, padx=5, pady=5)
        self.selected_well.trace_add("write", lambda *_: self.refresh_plot())

        ttk.Label(controls, text="Fluido").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        fluid_combo = ttk.Combobox(
            controls,
            textvariable=self.selected_fluid,
            values=["Gás", "Óleo"],
            state="readonly",
            width=15,
        )
        fluid_combo.grid(row=0, column=3, padx=5, pady=5)
        self.selected_fluid.trace_add("write", lambda *_: self.refresh_plot())

        ttk.Label(controls, text="Gráfico").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        plot_combo = ttk.Combobox(
            controls,
            textvariable=self.selected_plot,
            values=["Vazão", "Volume acumulado"],
            state="readonly",
            width=20,
        )
        plot_combo.grid(row=0, column=5, padx=5, pady=5)
        self.selected_plot.trace_add("write", lambda *_: self.refresh_plot())

        export_button = ttk.Button(controls, text="Exportar resultados", command=self.export_results)
        export_button.grid(row=0, column=6, padx=10, pady=5)

        self.figure, self.axes = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.master)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def get_selected_fluid(self) -> str | None:
        selected_fluid = self.selected_fluid.get().lower()
        if selected_fluid in {"gás", "gas"}:
            return "gas"
        if selected_fluid in {"óleo", "oleo", "oil"}:
            return "oil"
        return None

    def get_filtered_wells(self) -> list[dict[str, Any]]:
        fluid_filter = self.get_selected_fluid()
        if fluid_filter is None:
            return []

        selected_name = self.selected_well.get()
        if selected_name == "Todos os poços":
            return [well for well in self.wells.values() if well["fluido"] == fluid_filter]

        matched_wells = [well for well in self.wells.values() if well["name"] == selected_name]
        if not matched_wells:
            return []

        return [well for well in matched_wells if well["fluido"] == fluid_filter]

    def show_message(self, message: str) -> None:
        self.axes.clear()
        self.axes.text(0.5, 0.5, message, ha="center", va="center")
        self.axes.set_axis_off()
        self.canvas.draw()

    def refresh_plot(self) -> None:
        fluid_filter = self.get_selected_fluid()
        if fluid_filter is None:
            self.show_message("Selecione um fluido válido: gás ou óleo.")
            return

        wells = self.get_filtered_wells()
        selected_name = self.selected_well.get()
        if selected_name != "Todos os poços":
            wells_with_same_name = [well for well in self.wells.values() if well["name"] == selected_name]
            if not wells_with_same_name:
                self.show_message("Poço não encontrado.")
                return

            if not any(well["fluido"] == fluid_filter for well in wells_with_same_name):
                self.show_message(
                    f"O poço '{selected_name}' não possui o fluido selecionado ({'gás' if fluid_filter == 'gas' else 'óleo'})."
                )
                return

        if not wells:
            self.show_message("Nenhum poço encontrado para a seleção.")
            return

        self.axes.clear()
        plot_type = self.selected_plot.get()
        if plot_type == "Vazão":
            self.plot_flow(wells, fluid_filter)
        else:
            self.plot_cumulative(wells, fluid_filter)

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_flow(self, wells: list[dict[str, Any]], fluid_filter: str) -> None:
        if self.selected_well.get() == "Todos os poços":
            dates, values = build_combined_series(wells)
            self.axes.plot(dates, values, linewidth=2.0, color="tab:blue")
            self.axes.set_title("Vazão consolidada por fluido")
            self.axes.set_ylabel("Vazão (Mm3/dia)" if fluid_filter == "gas" else "Vazão (m3/dia)")
            self.axes.set_xlabel("Data")
            self.axes.grid(True, alpha=0.3)
            return

        for well in wells:
            series = build_decline_series(well, get_threshold(well["fluido"]))
            self.axes.plot(series["dates"], series["q"], marker="o", linewidth=1.8, label=well["name"])

        self.axes.set_title("Vazão prevista por poço")
        self.axes.set_ylabel("Vazão (Mm3/dia)" if fluid_filter == "gas" else "Vazão (m3/dia)")
        self.axes.set_xlabel("Data")
        self.axes.grid(True, alpha=0.3)
        if len(wells) > 1:
            self.axes.legend(loc="best")

    def export_results(self) -> None:
        """Export well-level and fluid-concatenated flow/cumulative data to Excel."""
        if filedialog is None:
            self.show_message("Dialog de arquivo não disponível neste ambiente.")
            return

        default_name = "extrapolacao_producao_pocos.xlsx"
        default_dir = self.workbook_path.parent if self.workbook_path.exists() else Path.cwd()
        target = filedialog.asksaveasfilename(
            title="Salvar resultados da extrapolação",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialdir=str(default_dir),
            initialfile=default_name,
        )
        if not target:
            return

        target_path = Path(target)
        try:
            workbook = Workbook()
            default_sheet = workbook.active
            workbook.remove(default_sheet)

            wells_sorted = sorted(self.wells.values(), key=lambda item: item["name"])
            self._add_well_flow_sheet(workbook, wells_sorted)
            self._add_well_cumulative_sheet(workbook, wells_sorted)
            self._add_fluid_flow_sheet(workbook, wells_sorted)
            self._add_fluid_cumulative_sheet(workbook, wells_sorted)
            self._add_category_cumulative_sheet(workbook, wells_sorted)

            workbook.save(target_path)
        except Exception as exc:  # pragma: no cover - runtime guard
            error_message = f"Falha ao exportar resultados: {exc}"
            if messagebox is not None:
                messagebox.showerror("Erro na exportação", error_message)
            else:
                self.show_message(error_message)
            return

        success_message = f"Arquivo exportado com sucesso:\n{target_path}"
        if messagebox is not None:
            messagebox.showinfo("Exportação concluída", success_message)
        else:
            self.show_message(success_message)

    def _add_well_flow_sheet(self, workbook: Workbook, wells: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet("vazao_pocos")
        sheet.append(["Data", "Poço", "Fluido", "Categoria", "Classe", "Origem Qi", "Qi utilizado", "Zona", "Vazão"])

        for well in wells:
            series = build_decline_series(well, get_threshold(well["fluido"]))
            qi_source = qi_source_label(str(well["fluido"]))
            qi_used = float(well["qi"])
            category_series = list(well.get("resolved_categoria", []))
            class_series = list(well.get("resolved_classe", []))
            zone_series = list(well.get("resolved_zona", []))
            for idx, (date_value, q_value) in enumerate(zip(series["dates"], series["q"])):
                categoria = category_series[idx] if idx < len(category_series) else str(well.get("categoria", ""))
                classe = class_series[idx] if idx < len(class_series) else str(well.get("classe", ""))
                zona = zone_series[idx] if idx < len(zone_series) else str(well.get("zona", ""))
                sheet.append([
                    format_export_date(date_value),
                    well["name"],
                    fluid_label(str(well["fluido"])),
                    categoria,
                    classe,
                    qi_source,
                    qi_used,
                    zona,
                    float(q_value),
                ])

    def _add_well_cumulative_sheet(self, workbook: Workbook, wells: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet("acumulada_pocos")
        sheet.append([
            "Data",
            "Poço",
            "Fluido",
            "Categoria",
            "Classe",
            "Origem Qi",
            "Qi utilizado",
            "Volume acumulado",
        ])

        grouped = group_wells_by_name_and_fluid(wells)
        for (well_name, fluid), grouped_wells in sorted(grouped.items()):
            dates, values = build_combined_cumulative_series(grouped_wells)
            qi_source = qi_source_label(fluid)
            qi_used = float(sum(float(well["qi"]) for well in grouped_wells))
            categorias = combine_text_field(grouped_wells, "categoria")
            classes = combine_text_field(grouped_wells, "classe")
            for date_value, cum_value in zip(dates, values):
                sheet.append([
                    format_export_date(date_value),
                    well_name,
                    fluid_label(fluid),
                    categorias,
                    classes,
                    qi_source,
                    qi_used,
                    float(cum_value),
                ])

    def _add_fluid_flow_sheet(self, workbook: Workbook, wells: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet("vazao_conc_fluido")
        sheet.append(["Data", "Fluido", "Categoria", "Classe", "Origem Qi", "Qi utilizado", "Vazão concatenada"])

        for fluid in ("gas", "oil"):
            fluid_wells = [well for well in wells if well["fluido"] == fluid]
            if not fluid_wells:
                continue

            dates, values = build_combined_series(fluid_wells)
            categorias = combine_text_field(fluid_wells, "categoria")
            classes = combine_text_field(fluid_wells, "classe")
            qi_source = qi_source_label(fluid)
            qi_used = float(sum(float(well["qi"]) for well in fluid_wells))
            for date_value, q_value in zip(dates, values):
                sheet.append([
                    format_export_date(date_value),
                    fluid_label(fluid),
                    categorias,
                    classes,
                    qi_source,
                    qi_used,
                    float(q_value),
                ])

    def _add_fluid_cumulative_sheet(self, workbook: Workbook, wells: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet("acum_conc_fluido")
        sheet.append(["Data", "Fluido", "Categoria", "Classe", "Origem Qi", "Qi utilizado", "Acumulada concatenada"])

        for fluid in ("gas", "oil"):
            fluid_wells = [well for well in wells if well["fluido"] == fluid]
            if not fluid_wells:
                continue

            dates, values = build_combined_cumulative_series(fluid_wells)
            categorias = combine_text_field(fluid_wells, "categoria")
            classes = combine_text_field(fluid_wells, "classe")
            qi_source = qi_source_label(fluid)
            qi_used = float(sum(float(well["qi"]) for well in fluid_wells))
            for date_value, cum_value in zip(dates, values):
                sheet.append([
                    format_export_date(date_value),
                    fluid_label(fluid),
                    categorias,
                    classes,
                    qi_source,
                    qi_used,
                    float(cum_value),
                ])

    def _add_category_cumulative_sheet(self, workbook: Workbook, wells: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet("acum_conc_categoria")
        sheet.append(["Data", "Fluido", "Acumulada P1", "Acumulada P2", "Acumulada P3"])

        for fluid in ("gas", "oil"):
            dates, category_series = build_category_cumulative_series(wells, fluid)
            if len(dates) == 0:
                continue

            values_p1 = category_series.get("P1", np.zeros(len(dates), dtype=float))
            values_p2 = category_series.get("P2", np.zeros(len(dates), dtype=float))
            values_p3 = category_series.get("P3", np.zeros(len(dates), dtype=float))

            for idx, date_value in enumerate(dates):
                p1 = float(values_p1[idx]) if idx < len(values_p1) else 0.0
                p2 = float(values_p2[idx]) if idx < len(values_p2) else 0.0
                p3 = float(values_p3[idx]) if idx < len(values_p3) else 0.0
                sheet.append([
                    format_export_date(date_value),
                    fluid_label(fluid),
                    p1,
                    p2,
                    p3,
                ])

    def plot_cumulative(self, wells: list[dict[str, Any]], fluid_filter: str) -> None:
        if self.selected_well.get() == "Todos os poços":
            dates, values = build_combined_cumulative_series(wells)
            self.axes.plot(dates, values, linewidth=2.0, color="tab:green")
            self.axes.set_title("Volume acumulado consolidado")
            self.axes.set_ylabel("Volume acumulado (m3)" if fluid_filter == "oil" else "Volume acumulado (Mm3)")
            self.axes.set_xlabel("Data")
            self.axes.grid(True, alpha=0.3)
            return

        grouped = group_wells_by_name_and_fluid(wells)
        for (well_name, _), grouped_wells in sorted(grouped.items()):
            dates, values = build_combined_cumulative_series(grouped_wells)
            self.axes.plot(dates, values, marker="o", linewidth=1.8, label=well_name)

        self.axes.set_title("Volume produzido acumulado")
        self.axes.set_ylabel("Volume acumulado (m3)" if fluid_filter == "oil" else "Volume acumulado (Mm3)")
        self.axes.set_xlabel("Data")
        self.axes.grid(True, alpha=0.3)
        if len(wells) > 1:
            self.axes.legend(loc="best")


def run_gui(workbook_path: Path | None = None) -> None:
    """Launch the Tkinter-based GUI."""
    if tk is None or ttk is None:
        raise SystemExit("Tkinter is not available in this environment.")

    if workbook_path is None:
        workbook_path = ask_workbook_path()

    root = tk.Tk()
    app = ProductionDeclineApp(root, workbook_path)
    root.mainloop()


def main() -> None:
    path: Path | None = None
    headless = False

    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--headless":
            headless = True
        elif arg in {"-h", "--help"}:
            print("Usage: python examples/extrapola_producao_pocos.py [--headless] [workbook_path]")
            return
        else:
            candidate = Path(arg).expanduser()
            if candidate.exists():
                path = candidate
            else:
                print(f"Workbook not found: {candidate}")
                return

    if headless:
        if path is None:
            path = ask_workbook_path()
        wells = read_workbook(path)
        warnings = detect_simultaneous_zone_production(list(wells.values()))
        for warning in warnings:
            print(f"WARNING: {warning}")
        print(f"Loaded {len(wells)} wells from {path}")
        for name, well in sorted(wells.items()):
            series = build_decline_series(well, get_threshold(well["fluido"]))
            print(
                f"{name}: fluid={well['fluido']}, Qi={well['qi']}, Di={well['di']}, b={well.get('b', 0.0)}, "
                f"end_date={series['dates'][-1].date()}"
            )
        return

    run_gui(path)


if __name__ == "__main__":
    main()
