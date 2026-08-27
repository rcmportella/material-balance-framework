"""Graphical PVT table generator for oil and gas properties.

Run from the project root with::

    python material_balance/PVT_table.py

The calculations reuse the correlations implemented in ``pvt_properties.py``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Make direct execution from the material_balance directory behave like
# execution from the project root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from material_balance.pvt_properties import CorrelationsPVT


APP_TITLE = "Tabela PVT - Bo, Bg, Rs e Z"


def calculate_pvt_table(
    temperature_c: float,
    pressure_min: float,
    pressure_max: float,
    bubble_point_pressure: float,
    API: float,
    gamma_g: float,
    point_count: int = 25,
) -> dict[str, np.ndarray]:
    """Calculate pressure-dependent PVT properties at a fixed temperature."""
    if temperature_c <= -273.15:
        raise ValueError("A temperatura deve ser maior que -273,15 °C.")
    if pressure_min <= 0 or pressure_max <= 0 or bubble_point_pressure <= 0:
        raise ValueError("As pressões devem ser maiores que zero.")
    if pressure_max <= pressure_min:
        raise ValueError("A pressão máxima deve ser maior que a pressão mínima.")
    if API <= 0 or API > 100 or gamma_g <= 0:
        raise ValueError("API deve estar entre 0 e 100, e gamma_g deve ser maior que zero.")
    if point_count < 2 or point_count > 1000:
        raise ValueError("O número de pontos deve estar entre 2 e 1000.")

    pressures = np.linspace(pressure_min, pressure_max, point_count)
    if not pressure_min <= bubble_point_pressure <= pressure_max:
        raise ValueError("A pressão de bolha deve estar entre a pressão mínima e máxima.")
    if pressure_min < bubble_point_pressure < pressure_max:
        pressures = np.sort(np.append(pressures, bubble_point_pressure))
    point_count = len(pressures)
    temperature_k = temperature_c + 273.15
    oil_properties = CorrelationsPVT.vasquez_beggs_oil_pvt(
        pressures, temperature_c, bubble_point_pressure, gamma_g, API
    )
    rs_values = oil_properties["Rs"]
    bo_values = oil_properties["Bo"]
    co_values = oil_properties["co"]
    z_values = np.empty(point_count)
    bg_values = np.empty(point_count)
    mu_g_values = np.empty(point_count)
    mu_o_values = np.empty(point_count)

    for index, pressure in enumerate(pressures):
        z = CorrelationsPVT.gas_z_factor_hall_yarborough(
            pressure, temperature_k, gamma_g
        )
        bg = CorrelationsPVT.gas_Bg(pressure, temperature_k, z)
        mu_g = CorrelationsPVT.gas_viscosity_lee_gonzalez_eakin(
            pressure, temperature_k, gamma_g, z
        )
        mu_o = CorrelationsPVT.oil_viscosity_beggs_robinson(
            API, temperature_c, rs_values[index]
        )
        z_values[index] = z
        bg_values[index] = bg
        mu_g_values[index] = mu_g
        mu_o_values[index] = mu_o

    return {
        "pressure": pressures,
        "Bo": bo_values,
        "Bg": bg_values,
        "Rs": rs_values,
        "Z": z_values,
        "co": co_values,
        "mu_g": mu_g_values,
        "mu_o": mu_o_values,
    }


# Unit conversion factors from this module's metric convention to OPM/Eclipse field units.
_KGF_CM2_TO_PSIA = 14.2233
_BG_M3M3_TO_RB_PER_MSCF = 178.107
_RS_M3M3_TO_MSCF_PER_STB = 0.0056146

# Conversion factors between the internal calculation units (kgf/cm2, m3/m3, C)
# and the two unit systems offered in the UI. METRIC displays pressure in bar and
# volumes in m3; FIELD displays pressure in psia, oil volume in bbl (STB) and gas
# volume in scf. API, gamma_g and viscosities (cP) are dimensionless/unaffected.
_BAR_TO_KGFCM2 = 1 / 0.980665
_KGFCM2_TO_BAR = 0.980665
_PSIA_TO_KGFCM2 = 0.0703069
_BG_M3M3_TO_RB_PER_SCF = 0.0283168 / 0.158987
_RS_M3M3_TO_SCF_PER_STB = 1 / 0.178107

UNIT_LABELS: dict[str, dict[str, str]] = {
    "METRIC": {"pressure": "bar", "temperature": "°C", "Bo": "m³/m³", "Bg": "m³/m³", "Rs": "m³/m³", "co": "1/bar"},
    "FIELD": {"pressure": "psia", "temperature": "°F", "Bo": "rb/stb", "Bg": "rb/scf", "Rs": "scf/stb", "co": "1/psi"},
}


def pressure_to_internal(value: float, unit_system: str) -> float:
    """Convert a pressure entered in the UI's unit system to kgf/cm2."""
    if unit_system == "FIELD":
        return value * _PSIA_TO_KGFCM2
    return value * _BAR_TO_KGFCM2


def temperature_to_internal(value: float, unit_system: str) -> float:
    """Convert a temperature entered in the UI's unit system to °C."""
    if unit_system == "FIELD":
        return (value - 32) * 5 / 9
    return value


def pressure_from_internal(value: np.ndarray | float, unit_system: str) -> np.ndarray | float:
    """Convert a pressure from kgf/cm2 to the UI's unit system."""
    if unit_system == "FIELD":
        return value * _KGF_CM2_TO_PSIA
    return value * _KGFCM2_TO_BAR


def convert_results_for_display(results: dict[str, np.ndarray], unit_system: str) -> dict[str, np.ndarray]:
    """Convert calculated results (always in metric/kgf-cm2) to the selected unit system.

    Bo, Z, mu_g and mu_o are dimensionless ratios or already in cP, so their
    numerical value does not change between unit systems.
    """
    if unit_system == "FIELD":
        bg = results["Bg"] * _BG_M3M3_TO_RB_PER_SCF
        rs = results["Rs"] * _RS_M3M3_TO_SCF_PER_STB
        co = results["co"] * _PSIA_TO_KGFCM2
    else:
        bg = results["Bg"]
        rs = results["Rs"]
        co = results["co"] / _KGFCM2_TO_BAR

    return {
        "pressure": pressure_from_internal(results["pressure"], unit_system),
        "Bo": results["Bo"],
        "Bg": bg,
        "Rs": rs,
        "Z": results["Z"],
        "co": co,
        "mu_g": results["mu_g"],
        "mu_o": results["mu_o"],
    }


def build_opm_pvt_text(
    results: dict[str, np.ndarray], bubble_point_pressure: float, unit_system: str = "FIELD"
) -> str:
    """Format calculated PVT results as OPM/Eclipse ``PVDG`` and ``PVTO`` keywords.

    ``bubble_point_pressure`` must be given in internal metric units (kgf/cm2),
    matching ``results["pressure"]``. Output columns follow OPM's own METRIC
    (pressure in bar, Bg/Rs in m3/m3) or FIELD (pressure in psia, Bg in rb per
    Mscf, Rs in Mscf per stb) unit conventions. Viscosity is always in cP.

    Pressures at or below the bubble point become saturated ``PVTO`` rows
    (each with its own Rs, matching the natural Rs(P) curve). Pressures above
    the bubble point are appended as undersaturated continuation rows under
    the last (highest Rs) saturated row, as required by the format.
    """
    pressure = results["pressure"]
    if unit_system == "METRIC":
        pressure_display = pressure * _KGFCM2_TO_BAR
        bg_display = results["Bg"]
        rs_display = results["Rs"]
        pressure_unit, bg_unit, rs_unit = "bar", "sm3/sm3", "sm3/sm3"
        pressure_fmt, bg_fmt, rs_fmt = "{:.4f}", "{:.6f}", "{:.4f}"
    else:
        pressure_display = pressure * _KGF_CM2_TO_PSIA
        bg_display = results["Bg"] * _BG_M3M3_TO_RB_PER_MSCF
        rs_display = results["Rs"] * _RS_M3M3_TO_MSCF_PER_STB
        pressure_unit, bg_unit, rs_unit = "psia", "rb per Mscf", "Mscf per stb"
        pressure_fmt, bg_fmt, rs_fmt = "{:.3f}", "{:.6f}", "{:.4f}"

    lines = [
        "PVDG",
        f"-- Column 1: gas phase pressure ({pressure_unit})",
        f"-- Column 2: gas formation volume factor ({bg_unit})",
        "-- Column 3: gas viscosity (cP)",
    ]
    for p, bg, mu_g in zip(pressure_display, bg_display, results["mu_g"]):
        lines.append(f"{pressure_fmt.format(p)}\t{bg_fmt.format(bg)}\t{mu_g:.6f}")
    lines.append("/")
    lines.append("")
    lines.extend([
        "PVTO",
        f"-- Column 1: dissolved gas-oil ratio ({rs_unit})",
        f"-- Column 2: bubble point pressure ({pressure_unit})",
        "-- Column 3: oil FVF for saturated oil (rb per stb)",
        "-- Column 4: oil viscosity for saturated oil (cP)",
    ])

    saturated_indices = np.nonzero(pressure <= bubble_point_pressure)[0]
    undersaturated_indices = np.nonzero(pressure > bubble_point_pressure)[0]

    for index in saturated_indices:
        row = (
            f"{rs_fmt.format(rs_display[index])}\t"
            f"{pressure_fmt.format(pressure_display[index])}\t"
            f"{results['Bo'][index]:.4f}\t"
            f"{results['mu_o'][index]:.4f}"
        )
        is_last_saturated = index == saturated_indices[-1]
        lines.append(row if is_last_saturated and undersaturated_indices.size else row + " /")

    for index in undersaturated_indices:
        row = (
            f"\t{pressure_fmt.format(pressure_display[index])}\t"
            f"{results['Bo'][index]:.4f}\t"
            f"{results['mu_o'][index]:.4f}"
        )
        if index == undersaturated_indices[-1]:
            row += " /"
        lines.append(row)

    return "\n".join(lines) + "\n"


class PVTTableApp:
    """Tkinter interface for creating, plotting and exporting a PVT table."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(980, 680)
        self.results: dict[str, np.ndarray] | None = None
        self.display_results: dict[str, np.ndarray] | None = None
        self.input_values: dict[str, float | int] = {}
        self.unit_system = tk.StringVar(value="METRIC")
        self.unit_system_at_calc = "METRIC"

        self._build_controls()
        self._build_plot_area()
        self._build_status_bar()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Release the matplotlib figure and destroy the window so the process can exit."""
        plt.close(self.figure)
        self.root.quit()
        self.root.destroy()

    def _build_controls(self) -> None:
        controls = ttk.LabelFrame(self.root, text="Dados de entrada")
        controls.pack(fill=tk.X, padx=12, pady=(12, 6))

        self._unit_dependent_fields = {
            "temperature": ("Temperatura", "temperature"),
            "pressure_min": ("Pressão mínima", "pressure"),
            "pressure_max": ("Pressão máxima", "pressure"),
            "bubble_point_pressure": ("Pressão de bolha", "pressure"),
        }
        fields = [
            (self._unit_dependent_fields["temperature"][0], "temperature", "82"),
            (self._unit_dependent_fields["pressure_min"][0], "pressure_min", "70"),
            (self._unit_dependent_fields["pressure_max"][0], "pressure_max", "210"),
            (self._unit_dependent_fields["bubble_point_pressure"][0], "bubble_point_pressure", "140"),
            ("Grau API do óleo", "API", "35"),
            ("Densidade relativa do gás (gamma_g)", "gamma_g", "0.65"),
            ("Número de pontos", "point_count", "25"),
        ]
        self.entries: dict[str, ttk.Entry] = {}
        self.field_labels: dict[str, ttk.Label] = {}
        for column, (label, key, default) in enumerate(fields):
            row = column // 3
            grid_column = column % 3
            label_widget = ttk.Label(controls, text=label)
            label_widget.grid(
                row=row * 2, column=grid_column, padx=8, pady=(8, 2), sticky=tk.W
            )
            if key in self._unit_dependent_fields:
                self.field_labels[key] = label_widget
            entry = ttk.Entry(controls, width=18)
            entry.insert(0, default)
            entry.grid(row=row * 2 + 1, column=grid_column, padx=8, pady=(0, 8), sticky=tk.W)
            self.entries[key] = entry

        actions = ttk.Frame(controls)
        actions.grid(row=0, column=3, rowspan=6, padx=18, pady=8, sticky=tk.NS)
        ttk.Button(actions, text="Calcular / atualizar", command=self.calculate).pack(fill=tk.X, pady=2)
        self.export_button = ttk.Button(
            actions, text="Exportar para Excel", command=self.export_excel, state=tk.DISABLED
        )
        self.export_button.pack(fill=tk.X, pady=2)
        self.export_opm_button = ttk.Button(
            actions, text="Exportar para OPM", command=self.export_opm, state=tk.DISABLED
        )
        self.export_opm_button.pack(fill=tk.X, pady=2)

        units_frame = ttk.LabelFrame(controls, text="Sistema de unidades")
        units_frame.grid(row=6, column=0, columnspan=2, padx=8, pady=(0, 8), sticky=tk.W)
        ttk.Radiobutton(
            units_frame, text="METRIC (bar, m³)", value="METRIC",
            variable=self.unit_system, command=self._on_unit_system_change,
        ).pack(side=tk.LEFT, padx=6, pady=4)
        ttk.Radiobutton(
            units_frame, text="FIELD (psia, bbl, scf)", value="FIELD",
            variable=self.unit_system, command=self._on_unit_system_change,
        ).pack(side=tk.LEFT, padx=6, pady=4)
        ttk.Label(
            controls,
            text="As viscosidades são sempre expressas em cP. Densidades (API, gamma_g) não são afetadas.",
        ).grid(row=6, column=2, columnspan=2, padx=8, pady=(0, 8), sticky=tk.W)
        self._on_unit_system_change()

    def _on_unit_system_change(self) -> None:
        unit_system = self.unit_system.get()
        for key, (base_label, unit_type) in self._unit_dependent_fields.items():
            unit = UNIT_LABELS[unit_system][unit_type]
            self.field_labels[key].configure(text=f"{base_label} ({unit})")

    def _build_plot_area(self) -> None:
        self.figure, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
        self.axes = axes.ravel()
        self.axes[-1].set_visible(False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self._clear_plots()

    def _build_status_bar(self) -> None:
        self.status = tk.StringVar(value="Informe os dados e clique em Calcular / atualizar.")
        ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W).pack(
            fill=tk.X, padx=12, pady=(0, 12)
        )

    def _clear_plots(self) -> None:
        pressure_unit = UNIT_LABELS[self.unit_system_at_calc]["pressure"]
        titles = [
            ("Bo", f"Bo ({UNIT_LABELS[self.unit_system_at_calc]['Bo']})"),
            ("Bg", f"Bg ({UNIT_LABELS[self.unit_system_at_calc]['Bg']})"),
            ("Rs", f"Rs ({UNIT_LABELS[self.unit_system_at_calc]['Rs']})"),
            ("mu_g", "Viscosidade do gás (cP)"),
            ("mu_o", "Viscosidade do óleo (cP)"),
        ]
        for axis, (title, ylabel) in zip(self.axes, titles):
            axis.clear()
            axis.set_title(f"Pressão x {title}")
            axis.set_xlabel(f"Pressão ({pressure_unit})")
            axis.set_ylabel(ylabel)
            axis.grid(True, alpha=0.3)
        self.canvas.draw_idle()

    def _read_inputs(self) -> dict[str, float | int]:
        values: dict[str, float | int] = {}
        for key, entry in self.entries.items():
            text = entry.get().strip().replace(",", ".")
            if not text:
                raise ValueError("Todos os campos devem ser preenchidos.")
            try:
                values[key] = int(text) if key == "point_count" else float(text)
            except ValueError as error:
                raise ValueError(f"Valor inválido no campo '{key}'.") from error
        return values

    def calculate(self) -> None:
        try:
            values = self._read_inputs()
            unit_system = self.unit_system.get()
            self.results = calculate_pvt_table(
                temperature_c=temperature_to_internal(float(values["temperature"]), unit_system),
                pressure_min=pressure_to_internal(float(values["pressure_min"]), unit_system),
                pressure_max=pressure_to_internal(float(values["pressure_max"]), unit_system),
                bubble_point_pressure=pressure_to_internal(
                    float(values["bubble_point_pressure"]), unit_system
                ),
                API=float(values["API"]),
                gamma_g=float(values["gamma_g"]),
                point_count=int(values["point_count"]),
            )
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            messagebox.showerror("Dados inválidos", str(error), parent=self.root)
            return

        self.input_values = values
        self.unit_system_at_calc = unit_system
        self.display_results = convert_results_for_display(self.results, unit_system)
        self._update_plots()
        self.export_button.configure(state=tk.NORMAL)
        self.export_opm_button.configure(state=tk.NORMAL)
        self.status.set(f"Tabela criada com {len(self.results['pressure'])} pontos. Z foi armazenado internamente.")

    def _update_plots(self) -> None:
        assert self.display_results is not None
        pressure_unit = UNIT_LABELS[self.unit_system_at_calc]["pressure"]
        pressure = self.display_results["pressure"]
        keys = ("Bo", "Bg", "Rs", "mu_g", "mu_o")
        colors = ("#b34d3c", "#197278", "#d08c18", "#5b3a8e", "#c2185b")
        for axis, key, color in zip(self.axes, keys, colors):
            axis.clear()
            axis.plot(pressure, self.display_results[key], color=color, linewidth=2)
            axis.axvline(
                float(self.input_values["bubble_point_pressure"]),
                color="#555555",
                linestyle="--",
                linewidth=1,
                label="Pbolha",
            )
            axis.set_title(f"Pressão x {key}")
            axis.set_xlabel(f"Pressão ({pressure_unit})")
            unit = UNIT_LABELS[self.unit_system_at_calc].get(key, "cP")
            axis.set_ylabel(f"{key} ({unit})")
            axis.grid(True, alpha=0.3)
            axis.legend(loc="best")
        self.canvas.draw_idle()

    def export_excel(self) -> None:
        if self.display_results is None:
            return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
        except ImportError:
            messagebox.showerror(
                "Dependência ausente",
                "Instale openpyxl com: pip install openpyxl",
                parent=self.root,
            )
            return

        output_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar tabela PVT",
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
            initialfile="pvt_table.xlsx",
        )
        if not output_path:
            return

        units = UNIT_LABELS[self.unit_system_at_calc]
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "PVT"
        headers = [
            f"Pressão ({units['pressure']})",
            f"Bo ({units['Bo']})",
            f"Bg ({units['Bg']})",
            f"Rs ({units['Rs']})",
            "Z",
            f"co ({units['co']})",
            "mu_g (cP)",
            "mu_o (cP)",
        ]
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in zip(*(self.display_results[key] for key in ("pressure", "Bo", "Bg", "Rs", "Z", "co", "mu_g", "mu_o"))):
            sheet.append([float(value) for value in row])
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 22

        parameters = workbook.create_sheet("Parâmetros")
        parameters.append(["Parâmetro", "Valor"])
        parameters["A1"].font = Font(bold=True)
        parameter_labels = {
            "temperature": f"Temperatura ({units['temperature']})",
            "pressure_min": f"Pressão mínima ({units['pressure']})",
            "pressure_max": f"Pressão máxima ({units['pressure']})",
            "bubble_point_pressure": f"Pressão de bolha ({units['pressure']})",
            "API": "Grau API do óleo",
            "gamma_g": "Densidade relativa do gás",
            "point_count": "Número de pontos",
        }
        for key, label in parameter_labels.items():
            parameters.append([label, self.input_values[key]])
        parameters.append(["Sistema de unidades", self.unit_system_at_calc])
        parameters.column_dimensions["A"].width = 34
        parameters.column_dimensions["B"].width = 18

        try:
            workbook.save(Path(output_path))
        except OSError as error:
            messagebox.showerror("Erro ao exportar", str(error), parent=self.root)
            return
        self.status.set(f"Arquivo exportado: {output_path}")
        messagebox.showinfo("Exportação concluída", "A tabela PVT foi exportada com sucesso.", parent=self.root)

    def export_opm(self) -> None:
        if self.results is None:
            return

        output_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar para OPM",
            defaultextension=".txt",
            filetypes=[("Palavras-chave OPM/Eclipse", "*.txt"), ("Todos os arquivos", "*.*")],
            initialfile="pvt_opm.txt",
        )
        if not output_path:
            return

        text = build_opm_pvt_text(
            self.results,
            pressure_to_internal(float(self.input_values["bubble_point_pressure"]), self.unit_system_at_calc),
            self.unit_system_at_calc,
        )
        try:
            Path(output_path).write_text(text, encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Erro ao exportar", str(error), parent=self.root)
            return
        self.status.set(f"Arquivo OPM exportado ({self.unit_system_at_calc}): {output_path}")
        messagebox.showinfo(
            "Exportação concluída",
            f"As tabelas PVDG e PVTO foram exportadas com sucesso em unidades {self.unit_system_at_calc}.",
            parent=self.root,
        )


def main() -> None:
    root = tk.Tk()
    PVTTableApp(root)
    root.mainloop()
    # Some matplotlib/Tk backends leave lingering non-daemon threads alive after
    # mainloop returns, which keeps the terminal attached to the process. Force
    # the interpreter to exit once the window has been closed.
    os._exit(0)


if __name__ == "__main__":
    main()
