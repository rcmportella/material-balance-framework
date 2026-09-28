"""GUI for estimating gas initially in place with the p/Z versus Gp method.

Run from the project root with::

    python -m material_balance.gas_pz_app
"""

from __future__ import annotations

import csv
import math
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Support both direct-file execution from VS Code and package execution.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from material_balance.pvt_properties import CorrelationsPVT


APP_TITLE = "Gas In-Place Estimate | p/Z vs Gp"


@dataclass(frozen=True)
class ProductionHistory:
    """Production observations in metric units."""

    time: np.ndarray
    Gp: np.ndarray
    pressure: np.ndarray


@dataclass(frozen=True)
class PZAnalysis:
    """Calculated Z factors, p/Z regression and GIIP estimate."""

    history: ProductionHistory
    z_factor: np.ndarray
    pz: np.ndarray
    slope: float
    intercept: float
    giip: float
    r_squared: float


def read_production_csv(filepath: str | Path) -> ProductionHistory:
    """Read a CSV with time, cumulative gas Gp and average reservoir pressure."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Production CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        sample = csv_file.read(4096)
        csv_file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(csv_file, dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError("CSV must have a header row: time,Gp,pressure")
        columns = {name.strip().lower(): name for name in reader.fieldnames if name}
        required = ("time", "gp", "pressure")
        missing = [name for name in required if name not in columns]
        if missing:
            raise ValueError(
                "CSV is missing required column(s): " + ", ".join(missing)
            )

        observations: list[tuple[float, float, float]] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                values = tuple(
                    float((row[columns[name]] or "").strip().replace(",", "."))
                    for name in required
                )
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid or empty numeric value on CSV row {row_number}.") from error
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"Non-finite numeric value on CSV row {row_number}.")
            observations.append(values)

    if len(observations) < 2:
        raise ValueError("At least two production/pressure observations are required.")

    values = np.asarray(observations, dtype=float)
    time, gp, pressure = values.T
    if np.any(np.diff(time) <= 0):
        raise ValueError("Time values must be strictly increasing.")
    if np.any(gp < 0) or not np.isclose(gp[0], 0.0, atol=1e-9):
        raise ValueError("Gp must be nonnegative and the first row must have Gp = 0.")
    if np.any(np.diff(gp) < 0):
        raise ValueError("Cumulative gas production (Gp) must not decrease.")
    if np.any(pressure <= 0):
        raise ValueError("Average reservoir pressure must be greater than zero.")
    if np.unique(gp).size < 2:
        raise ValueError("Gp must contain at least two distinct values.")

    return ProductionHistory(time=time, Gp=gp, pressure=pressure)


def calculate_pz_analysis(
    history: ProductionHistory,
    temperature_c: float,
    gas_specific_gravity: float,
) -> PZAnalysis:
    """Calculate Hall-Yarborough Z factors and the p/Z regression x-intercept."""
    if not math.isfinite(temperature_c) or temperature_c <= -273.15:
        raise ValueError("Reservoir temperature must be greater than -273.15 °C.")
    if not math.isfinite(gas_specific_gravity) or gas_specific_gravity <= 0:
        raise ValueError("Gas specific gravity must be greater than zero.")

    temperature_k = temperature_c + 273.15
    z_factor = np.asarray(
        [
            CorrelationsPVT.gas_z_factor_hall_yarborough(
                float(pressure), temperature_k, gas_specific_gravity
            )
            for pressure in history.pressure
        ],
        dtype=float,
    )
    if not np.all(np.isfinite(z_factor)) or np.any(z_factor <= 0):
        raise ValueError("The Z-factor correlation returned invalid values for this input.")

    pz = history.pressure / z_factor
    slope, intercept = np.polyfit(history.Gp, pz, 1)
    if not math.isfinite(float(slope)) or slope >= 0:
        raise ValueError("The fitted p/Z trend must decline as Gp increases to estimate GIIP.")

    giip = float(-intercept / slope)
    if not math.isfinite(giip) or giip <= 0:
        raise ValueError("The fitted p/Z line does not have a positive GIIP x-intercept.")

    residual_sum = float(np.sum((pz - (slope * history.Gp + intercept)) ** 2))
    total_sum = float(np.sum((pz - np.mean(pz)) ** 2))
    r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else 1.0

    return PZAnalysis(
        history=history,
        z_factor=z_factor,
        pz=pz,
        slope=float(slope),
        intercept=float(intercept),
        giip=giip,
        r_squared=r_squared,
    )


def estimate_gp_at_pressure(
    analysis: PZAnalysis,
    final_pressure: float,
    temperature_c: float,
    gas_specific_gravity: float,
) -> float:
    """Estimate cumulative gas production at a target reservoir pressure."""
    if not math.isfinite(final_pressure) or final_pressure <= 0:
        raise ValueError("Final reservoir pressure must be greater than zero.")
    if final_pressure > analysis.history.pressure[0]:
        raise ValueError("Final pressure must not exceed the initial reservoir pressure.")

    final_z = CorrelationsPVT.gas_z_factor_hall_yarborough(
        final_pressure, temperature_c + 273.15, gas_specific_gravity
    )
    if not math.isfinite(final_z) or final_z <= 0:
        raise ValueError("The Z-factor correlation returned an invalid value at final pressure.")

    final_pz = final_pressure / final_z
    estimated_gp = (final_pz - analysis.intercept) / analysis.slope
    if not math.isfinite(estimated_gp) or estimated_gp < 0:
        raise ValueError("The fitted p/Z line gives a negative production estimate at this pressure.")
    return float(estimated_gp)


class GasPZApp:
    """Tkinter interface for the metric gas p/Z material-balance method."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(860, 640)
        self._set_readable_fonts()
        self.csv_path = tk.StringVar()
        self.temperature = tk.StringVar(value="104")
        self.gas_gravity = tk.StringVar(value="0.65")
        self.final_pressure = tk.StringVar()
        self.estimate_text = tk.StringVar(value="GIIP: waiting for calculation")
        self.fit_text = tk.StringVar(value="")
        self.final_gp_text = tk.StringVar(value="Enter final pressure to estimate Gp")

        self._build_controls()
        self._build_plot()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _set_readable_fonts() -> None:
        font_sizes = {
            "TkDefaultFont": 13,
            "TkTextFont": 13,
            "TkMenuFont": 13,
            "TkHeadingFont": 14,
            "TkFixedFont": 12,
        }
        for font_name, size in font_sizes.items():
            try:
                tkfont.nametofont(font_name).configure(size=size)
            except tk.TclError:
                continue

    def _build_controls(self) -> None:
        controls = ttk.LabelFrame(self.root, text="Input data | Metric units")
        controls.pack(fill=tk.X, padx=12, pady=(12, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Production CSV").grid(
            row=0, column=0, padx=8, pady=8, sticky=tk.W
        )
        ttk.Entry(controls, textvariable=self.csv_path).grid(
            row=0, column=1, padx=8, pady=8, sticky=tk.EW
        )
        ttk.Button(controls, text="Browse...", command=self._browse_csv).grid(
            row=0, column=2, padx=8, pady=8
        )

        ttk.Label(controls, text="Reservoir temperature (°C)").grid(
            row=1, column=0, padx=8, pady=8, sticky=tk.W
        )
        ttk.Entry(controls, textvariable=self.temperature, width=14).grid(
            row=1, column=1, padx=8, pady=8, sticky=tk.W
        )
        ttk.Label(controls, text="Gas specific gravity (air = 1)").grid(
            row=1, column=2, padx=8, pady=8, sticky=tk.W
        )
        ttk.Entry(controls, textvariable=self.gas_gravity, width=12).grid(
            row=1, column=3, padx=8, pady=8, sticky=tk.W
        )

        ttk.Label(controls, text="Final reservoir pressure (kgf/cm²)").grid(
            row=2, column=0, padx=8, pady=(2, 10), sticky=tk.W
        )
        ttk.Entry(controls, textvariable=self.final_pressure, width=14).grid(
            row=2, column=1, padx=8, pady=(2, 10), sticky=tk.W
        )
        ttk.Button(controls, text="Calculate GIIP", command=self.calculate).grid(
            row=2, column=3, padx=8, pady=(2, 10), sticky=tk.E
        )

        result_bar = ttk.Frame(self.root)
        result_bar.pack(fill=tk.X, padx=16, pady=(4, 8))
        ttk.Label(result_bar, textvariable=self.estimate_text, font=("Segoe UI", 21, "bold")).pack(
            side=tk.LEFT
        )
        result_details = ttk.Frame(result_bar)
        result_details.pack(side=tk.RIGHT)
        ttk.Label(result_details, textvariable=self.final_gp_text).pack(anchor=tk.E)
        ttk.Label(result_details, textvariable=self.fit_text).pack(anchor=tk.E)

    def _build_plot(self) -> None:
        self.figure, self.axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.axis.set_xlabel("Cumulative gas produced, Gp (m³)", fontsize=13)
        self.axis.set_ylabel("p/Z (kgf/cm²)", fontsize=13)
        self.axis.set_title("Gas material balance", fontsize=15)
        self.axis.tick_params(axis="both", labelsize=12)
        self.axis.grid(True, alpha=0.3)
        self.canvas.draw_idle()

    def _browse_csv(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Select production history CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=str(Path(self.csv_path.get()).parent) if self.csv_path.get() else None,
        )
        if selected:
            self.csv_path.set(selected)

    def calculate(self) -> None:
        try:
            path = self.csv_path.get().strip()
            if not path:
                raise ValueError("Select a production CSV file.")
            temperature_c = float(self.temperature.get().strip().replace(",", "."))
            gas_gravity = float(self.gas_gravity.get().strip().replace(",", "."))
            history = read_production_csv(path)
            result = calculate_pz_analysis(history, temperature_c, gas_gravity)
            final_pressure_text = self.final_pressure.get().strip()
            final_gp = None
            if final_pressure_text:
                final_pressure = float(final_pressure_text.replace(",", "."))
                final_gp = estimate_gp_at_pressure(
                    result, final_pressure, temperature_c, gas_gravity
                )
        except (OSError, ValueError, OverflowError, ZeroDivisionError) as error:
            messagebox.showerror("Unable to calculate GIIP", str(error), parent=self.root)
            return

        self.estimate_text.set(f"Estimated GIIP: {result.giip:,.0f} m³")
        self.fit_text.set(f"R² = {result.r_squared:.4f}  |  {len(history.Gp)} observations")
        if final_gp is None:
            self.final_gp_text.set("Enter final pressure to estimate Gp")
        else:
            self.final_gp_text.set(f"Estimated Gp at final pressure: {final_gp:,.0f} m³")
        self.axis.clear()
        self.axis.scatter(history.Gp, result.pz, color="#197278", s=48, label="Calculated p/Z")
        line_gp = np.linspace(0.0, result.giip, 150)
        self.axis.plot(
            line_gp,
            result.slope * line_gp + result.intercept,
            color="#b34d3c",
            linewidth=2,
            label="Linear regression",
        )
        self.axis.scatter([result.giip], [0.0], color="#b34d3c", marker="x", s=70, label="GIIP x-intercept")
        self.axis.axhline(0.0, color="#555555", linewidth=0.8)
        if final_gp is not None:
            final_pressure = float(self.final_pressure.get().strip().replace(",", "."))
            final_z = CorrelationsPVT.gas_z_factor_hall_yarborough(
                final_pressure, temperature_c + 273.15, gas_gravity
            )
            self.axis.scatter(
                [final_gp],
                [final_pressure / final_z],
                color="#d08c18",
                marker="D",
                s=58,
                label="Final-pressure estimate",
                zorder=3,
            )
        self.axis.set_xlabel("Cumulative gas produced, Gp (m³)", fontsize=13)
        self.axis.set_ylabel("p/Z (kgf/cm²)", fontsize=13)
        self.axis.set_title("p/Z vs cumulative gas produced", fontsize=15)
        self.axis.tick_params(axis="both", labelsize=12)
        self.axis.grid(True, alpha=0.3)
        self.axis.legend(loc="best", fontsize=12)
        self.canvas.draw_idle()

    def _on_close(self) -> None:
        plt.close(self.figure)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    GasPZApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()