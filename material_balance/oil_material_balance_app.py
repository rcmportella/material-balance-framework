"""File-driven desktop app for oil-reservoir material-balance analysis.

Run from the project root with::

    python -m material_balance.oil_material_balance_app
"""

from __future__ import annotations

import csv
import math
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from material_balance.input_reader import InputReader
from material_balance.oil_reservoir import OilReservoir
from material_balance.units import UnitConverter, UnitSystem


def calculate_oil_material_balance(
    pvt_file: str,
    production_file: str,
    unit_system: UnitSystem,
    initial_pressure: float,
    reservoir_temperature: float,
    m: float,
    aquifer_influx: bool = False,
    cw: float = 43e-6,
    cf: float = 14.223e-6,
    swi: float = 0.2,
) -> tuple[Any, Any, Any, dict[str, float]]:
    """Load data and calculate STOIIP using reservoir properties entered in the GUI."""
    pvt = InputReader.read_pvt_from_file(pvt_file, unit_system)
    production = InputReader.read_production_from_csv(
        production_file, unit_system, reservoir_type='oil'
    )
    reservoir = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=initial_pressure,
        reservoir_temperature=reservoir_temperature,
        m=m,
        aquifer_influx=aquifer_influx,
        unit_system=unit_system,
        cw=cw,
        cf=cf,
        swi=swi,
    )
    stoiip_values, statistics = reservoir.calculate_STOIIP_from_production_data(production)
    return reservoir, production, stoiip_values, statistics


def material_balance_plot_data(reservoir: Any) -> tuple[list[float], list[float]]:
    """Return finite (Et, F) points, with F in the configured volume units."""
    converter = UnitConverter()
    x_values = []
    f_values = []
    for eo, eg, efw, withdrawal in zip(
        reservoir.Eo_values, reservoir.Eg_values, reservoir.Efw_values, reservoir.F_values
    ):
        if not all(math.isfinite(float(value)) for value in (eo, eg, efw, withdrawal)):
            continue
        x_values.append(float(eo) + reservoir.m * float(eg) + float(efw))
        f_metric = converter.reservoir_volume_from_metric(withdrawal, reservoir.unit_system)
        f_values.append(float(f_metric))
    return x_values, f_values


def export_analysis_csv(
    filepath: str,
    production: Any,
    reservoir: Any,
    stoiip_values: Any,
) -> None:
    """Write analysis results in the unit system selected in the GUI."""
    unit_system = reservoir.unit_system
    converter = UnitConverter()
    if unit_system == UnitSystem.FIELD:
        pressure_unit = 'psia'
        oil_unit = 'STB'
        gas_unit = 'SCF'
        reservoir_volume_unit = 'rb'
    else:
        pressure_unit = 'kgf_cm2'
        oil_unit = 'm3_std'
        gas_unit = 'm3_std'
        reservoir_volume_unit = 'm3'

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as output_file:
        writer = csv.writer(output_file)
        writer.writerow([
            'time_days', f'pressure_{pressure_unit}', f'Np_{oil_unit}', f'Gp_{gas_unit}',
            f'Wp_{oil_unit}', 'Eo', 'Eg', 'mEg', 'Eo_plus_mEg', 'Efw', 'Et',
            f'F_{reservoir_volume_unit}', f'STOIIP_{oil_unit}',
        ])
        for index, stoiip in enumerate(stoiip_values):
            pressure = converter.pressure_from_metric(production.pressure[index], unit_system)
            oil_production = converter.oil_volume_from_metric(production.Np[index], unit_system)
            gas_production = converter.gas_volume_from_metric(production.Gp[index], unit_system)
            water_production = converter.oil_volume_from_metric(production.Wp[index], unit_system)
            withdrawal = converter.reservoir_volume_from_metric(reservoir.F_values[index], unit_system)
            stoiip_output = converter.oil_volume_from_metric(stoiip, unit_system)
            writer.writerow([
                production.time[index], pressure, oil_production, gas_production,
                water_production, reservoir.Eo_values[index],
                reservoir.Eg_values[index],
                reservoir.m * reservoir.Eg_values[index],
                reservoir.Eo_values[index] + reservoir.m * reservoir.Eg_values[index],
                reservoir.Efw_values[index], reservoir.Et_values[index],
                withdrawal, stoiip_output,
            ])


class OilMaterialBalanceApp:
    """Tkinter interface for calculating oil material balance from input files."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Oil Material Balance")
        self.root.minsize(1000, 600)
        self.analysis: tuple[Any, Any, Any, dict[str, float]] | None = None
        self.path_vars: dict[str, tk.StringVar] = {}

        self._build_inputs()
        self._build_results()
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def _build_inputs(self) -> None:
        inputs = ttk.LabelFrame(self.root, text="Input files")
        inputs.pack(fill=tk.X, padx=12, pady=(12, 6))
        filetypes = {
            'PVT data': [('PVT data', '*.xlsx *.xlsm *.csv'), ('All files', '*.*')],
            'Production history': [('CSV files', '*.csv'), ('All files', '*.*')],
        }
        self.path_vars = {label: tk.StringVar() for label in filetypes}

        for row, (label, filters) in enumerate(filetypes.items()):
            ttk.Label(inputs, text=label).grid(row=row, column=0, padx=8, pady=6, sticky=tk.W)
            ttk.Entry(inputs, textvariable=self.path_vars[label]).grid(
                row=row, column=1, padx=8, pady=6, sticky=tk.EW
            )
            ttk.Button(
                inputs,
                text="Browse...",
                command=lambda name=label, kinds=filters: self._browse(name, kinds),
            ).grid(row=row, column=2, padx=8, pady=6)

        inputs.columnconfigure(1, weight=1)

        reservoir = ttk.LabelFrame(self.root, text="Reservoir inputs")
        reservoir.pack(fill=tk.X, padx=12, pady=6)
        self.unit_var = tk.StringVar(value='METRIC')
        self.pressure_label = tk.StringVar()
        self.temperature_label = tk.StringVar()
        self.initial_pressure_var = tk.StringVar(value='')
        self.reservoir_temperature_var = tk.StringVar(value='25')
        self.gas_cap_ratio_var = tk.StringVar(value='0')
        self.aquifer_influx_var = tk.BooleanVar(value=False)
        self.cw_var = tk.StringVar(value='4.3e-05')
        self.cf_var = tk.StringVar(value='1.4223e-05')
        self.swi_var = tk.StringVar(value='0.2')

        ttk.Label(reservoir, text="Unit system").grid(
            row=0, column=0, padx=8, pady=6, sticky=tk.W
        )
        unit_selector = ttk.Combobox(
            reservoir, textvariable=self.unit_var, values=('METRIC', 'FIELD'),
            state='readonly', width=12,
        )
        unit_selector.grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)
        unit_selector.bind('<<ComboboxSelected>>', self._update_input_unit_labels)

        ttk.Label(reservoir, textvariable=self.pressure_label).grid(
            row=1, column=0, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.initial_pressure_var, width=16).grid(
            row=1, column=1, padx=8, pady=6, sticky=tk.W
        )
        ttk.Label(reservoir, textvariable=self.temperature_label).grid(
            row=1, column=2, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.reservoir_temperature_var, width=16).grid(
            row=1, column=3, padx=8, pady=6, sticky=tk.W
        )
        ttk.Label(reservoir, text="Gas-cap ratio, m").grid(
            row=2, column=0, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.gas_cap_ratio_var, width=16).grid(
            row=2, column=1, padx=8, pady=6, sticky=tk.W
        )
        ttk.Checkbutton(
            reservoir,
            text='Aquifer influx flag (We history is not supplied)',
            variable=self.aquifer_influx_var,
        ).grid(row=2, column=2, columnspan=2, padx=8, pady=6, sticky=tk.W)
        ttk.Label(reservoir, text='cw (1/(kgf/cm²))').grid(
            row=3, column=0, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.cw_var, width=16).grid(
            row=3, column=1, padx=8, pady=6, sticky=tk.W
        )
        ttk.Label(reservoir, text='cf (1/(kgf/cm²))').grid(
            row=3, column=2, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.cf_var, width=16).grid(
            row=3, column=3, padx=8, pady=6, sticky=tk.W
        )
        ttk.Label(reservoir, text='Swi (fraction)').grid(
            row=4, column=0, padx=8, pady=6, sticky=tk.W
        )
        ttk.Entry(reservoir, textvariable=self.swi_var, width=16).grid(
            row=4, column=1, padx=8, pady=6, sticky=tk.W
        )
        self._update_input_unit_labels()

        actions = ttk.Frame(self.root)
        actions.pack(fill=tk.X, padx=12, pady=(2, 8))
        ttk.Button(actions, text="Calculate STOIIP", command=self.calculate).pack(side=tk.LEFT, padx=4)
        self.export_button = ttk.Button(actions, text="Export CSV", command=self.export, state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT, padx=4)

    def _update_input_unit_labels(self, _event: Any = None) -> None:
        if self.unit_var.get() == 'FIELD':
            self.pressure_label.set('Initial pressure (psia)')
            self.temperature_label.set('Reservoir temperature (°F)')
        else:
            self.pressure_label.set('Initial pressure (kgf/cm²)')
            self.temperature_label.set('Reservoir temperature (°C)')

    def _build_results(self) -> None:
        results = ttk.LabelFrame(self.root, text="Results")
        results.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.summary = tk.StringVar(value="Select the PVT and production files, then enter reservoir properties.")
        ttk.Label(results, textvariable=self.summary).pack(anchor=tk.W, padx=8, pady=8)

        views = ttk.Notebook(results)
        views.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        table_frame = ttk.Frame(views)
        plot_frame = ttk.Frame(views)
        views.add(table_frame, text='STOIIP results')
        views.add(plot_frame, text='F vs Et')

        columns = ('time', 'pressure', 'F', 'Eo', 'Eg', 'mEg', 'Efw', 'Et', 'stoiip')
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        self.table.heading('time', text='Time (days)')
        for column in ('pressure', 'F', 'Eo', 'Eg', 'mEg', 'Efw', 'Et', 'stoiip'):
            self.table.heading(column, text=column)
        for column, width in {
            'time': 95, 'pressure': 115, 'F': 125, 'Eo': 100, 'Eg': 100,
            'mEg': 100, 'Efw': 100, 'Et': 100, 'stoiip': 135,
        }.items():
            self.table.column(column, width=width, anchor=tk.E, stretch=False)
        horizontal_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.table.xview)
        self.table.configure(xscrollcommand=horizontal_scroll.set)
        self.table.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
        horizontal_scroll.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.figure, self.axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
        self.plot_canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _browse(self, label: str, filetypes: list[tuple[str, str]]) -> None:
        filepath = filedialog.askopenfilename(parent=self.root, filetypes=filetypes)
        if filepath:
            self.path_vars[label].set(filepath)

    def close(self) -> None:
        plt.close(self.figure)
        self.root.quit()
        self.root.destroy()

    def calculate(self) -> None:
        paths = {label: variable.get().strip() for label, variable in self.path_vars.items()}
        if not all(paths.values()):
            messagebox.showerror("Missing input", "Select both input files.", parent=self.root)
            return

        try:
            self.analysis = calculate_oil_material_balance(
                pvt_file=paths['PVT data'],
                production_file=paths['Production history'],
                unit_system=UnitSystem[self.unit_var.get()],
                initial_pressure=float(self.initial_pressure_var.get()),
                reservoir_temperature=float(self.reservoir_temperature_var.get()),
                m=float(self.gas_cap_ratio_var.get()),
                aquifer_influx=self.aquifer_influx_var.get(),
                cw=float(self.cw_var.get()),
                cf=float(self.cf_var.get()),
                swi=float(self.swi_var.get()),
            )
        except Exception as error:
            messagebox.showerror("Calculation failed", str(error), parent=self.root)
            return

        reservoir, production, stoiip_values, statistics = self.analysis
        unit_system = reservoir.unit_system
        converter = UnitConverter()
        if unit_system == UnitSystem.FIELD:
            pressure_unit, oil_unit = 'psia', 'STB'
            mean = converter.oil_volume_from_metric(statistics['mean'], unit_system)
            median = converter.oil_volume_from_metric(statistics['median'], unit_system)
            f_unit = 'rb'
        else:
            pressure_unit, oil_unit = 'kgf/cm²', 'm³ std'
            mean, median = statistics['mean'], statistics['median']
            f_unit = 'm³'
        self.summary.set(
            f"Mean: {mean:,.3g} {oil_unit}    "
            f"Median: {median:,.3g} {oil_unit}    "
            f"Valid points: {statistics['count']} of {len(stoiip_values)}"
        )
        self.table.delete(*self.table.get_children())
        for index, stoiip in enumerate(stoiip_values):
            pressure = converter.pressure_from_metric(production.pressure[index], unit_system)
            withdrawal = converter.reservoir_volume_from_metric(
                reservoir.F_values[index], unit_system
            )
            oil_in_place = converter.oil_volume_from_metric(stoiip, unit_system)
            values = (
                production.time[index], pressure, withdrawal,
                reservoir.Eo_values[index], reservoir.Eg_values[index],
                reservoir.m * reservoir.Eg_values[index], reservoir.Efw_values[index],
                reservoir.Et_values[index], oil_in_place,
            )
            self.table.insert('', tk.END, values=(
                *(f'{float(value):,.5g}' if math.isfinite(float(value)) else 'Unavailable'
                  for value in values),
            ))
        self.table.heading('pressure', text=f'Pressure ({pressure_unit})')
        self.table.heading('F', text=f'F ({f_unit})')
        for column in ('Eo', 'Eg', 'mEg', 'Efw', 'Et'):
            self.table.heading(column, text=column)
        self.table.heading('stoiip', text=f'STOIIP ({oil_unit})')
        self._update_material_balance_plot(reservoir)
        self.export_button.configure(state=tk.NORMAL)

    def _update_material_balance_plot(self, reservoir: Any) -> None:
        x_values, f_values = material_balance_plot_data(reservoir)
        f_unit = 'rb' if reservoir.unit_system == UnitSystem.FIELD else 'm³'
        self.axis.clear()
        self.axis.set_title(f'Material Balance: F vs Et (m = {reservoir.m:g})')
        self.axis.set_xlabel('Et = Eo + mEg + Efw (dimensionless)')
        self.axis.set_ylabel(f'Underground withdrawal, F ({f_unit})')
        self.axis.grid(True, alpha=0.3)
        if x_values:
            self.axis.scatter(x_values, f_values, s=42, color='#197278', alpha=0.85)
        else:
            self.axis.text(
                0.5, 0.5, 'No valid calculation points',
                horizontalalignment='center', verticalalignment='center',
                transform=self.axis.transAxes,
            )
        self.plot_canvas.draw_idle()

    def export(self) -> None:
        if self.analysis is None:
            return
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export material-balance results",
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')],
            initialfile='oil_material_balance_results.csv',
        )
        if not filepath:
            return
        try:
            reservoir, production, stoiip_values, _ = self.analysis
            export_analysis_csv(filepath, production, reservoir, stoiip_values)
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self.root)
            return
        messagebox.showinfo("Export complete", f"Results exported to:\n{filepath}", parent=self.root)


def main() -> None:
    root = tk.Tk()
    OilMaterialBalanceApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()