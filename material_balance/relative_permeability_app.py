"""Corey relative-permeability curves with OPM/Eclipse table export."""

from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


DEFAULTS = {
    'swc': '0.20',
    'sorw': '0.20',
    'krw_end': '0.30',
    'krow_end': '1.00',
    'nw': '2.0',
    'now': '2.0',
    'sgc': '0.05',
    'sorg': '0.15',
    'krg_end': '0.80',
    'krog_end': '1.00',
    'ng': '2.0',
    'nog': '2.0',
    'points': '51',
}


def _validate_saturations(connate: float, residual_oil: float, label: str) -> None:
    if not 0 <= connate < 1:
        raise ValueError(f'{label} connate/critical saturation must be in [0, 1).')
    if not 0 <= residual_oil < 1:
        raise ValueError(f'{label} residual oil saturation must be in [0, 1).')
    if connate + residual_oil >= 1:
        raise ValueError(f'{label} connate and residual oil saturations must sum to less than 1.')


def _corey_pair(
    saturation: np.ndarray,
    connate: float,
    residual_oil: float,
    first_endpoint: float,
    second_endpoint: float,
    first_exponent: float,
    second_exponent: float,
) -> tuple[np.ndarray, np.ndarray]:
    effective = np.clip(
        (saturation - connate) / (1.0 - connate - residual_oil), 0.0, 1.0
    )
    first_curve = first_endpoint * effective**first_exponent
    second_curve = second_endpoint * (1.0 - effective)**second_exponent
    return first_curve, second_curve


def generate_corey_curves(parameters: dict[str, float]) -> dict[str, np.ndarray]:
    """Generate water-oil and gas-oil Corey curves on normalized saturation grids."""
    if any(not math.isfinite(value) for value in parameters.values()):
        raise ValueError('All Corey parameters must be finite numbers.')

    swc = parameters['swc']
    sorw = parameters['sorw']
    sgc = parameters['sgc']
    sorg = parameters['sorg']
    _validate_saturations(swc, sorw, 'Water-oil')
    _validate_saturations(sgc, sorg, 'Gas-oil')

    point_count = int(parameters['points'])
    if not 2 <= point_count <= 1001:
        raise ValueError('Number of saturation points must be between 2 and 1001.')

    for key in ('krw_end', 'krow_end', 'krg_end', 'krog_end'):
        if not 0 <= parameters[key] <= 1:
            raise ValueError(f'{key} must be between 0 and 1.')
    for key in ('nw', 'now', 'ng', 'nog'):
        if parameters[key] <= 0:
            raise ValueError(f'{key} must be greater than zero.')

    sw = np.linspace(0.0, 1.0, point_count)
    sg = np.linspace(0.0, 1.0, point_count)
    krw, krow = _corey_pair(
        sw, swc, sorw, parameters['krw_end'], parameters['krow_end'],
        parameters['nw'], parameters['now'],
    )
    krg, krog = _corey_pair(
        sg, sgc, sorg, parameters['krg_end'], parameters['krog_end'],
        parameters['ng'], parameters['nog'],
    )
    return {'sw': sw, 'krw': krw, 'krow': krow, 'sg': sg, 'krg': krg, 'krog': krog}


def format_opm_tables(curves: dict[str, np.ndarray], table_selection: str = 'Both') -> str:
    """Format Corey curves as OPM/Eclipse SWOF and/or SGOF keyword tables."""
    if table_selection not in {'SWOF', 'SGOF', 'Both'}:
        raise ValueError("Table selection must be 'SWOF', 'SGOF', or 'Both'.")

    blocks: list[str] = []
    if table_selection in {'SWOF', 'Both'}:
        lines = ['SWOF', '-- SW KRW KROW PCOW']
        lines.extend(
            f'{sw:.8f} {krw:.8f} {krow:.8f} 0.0'
            for sw, krw, krow in zip(curves['sw'], curves['krw'], curves['krow'])
        )
        lines.append('/')
        blocks.append('\n'.join(lines))
    if table_selection in {'SGOF', 'Both'}:
        lines = ['SGOF', '-- SG KRG KROG PCGO']
        lines.extend(
            f'{sg:.8f} {krg:.8f} {krog:.8f} 0.0'
            for sg, krg, krog in zip(curves['sg'], curves['krg'], curves['krog'])
        )
        lines.append('/')
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + '\n'


class RelativePermeabilityApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Relative Permeability | Corey Correlations')
        self.root.geometry('1120x780')
        self.root.minsize(900, 650)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.entries: dict[str, ttk.Entry] = {}
        self.curves: dict[str, np.ndarray] | None = None
        self.selected_plot = tk.StringVar(value='Water-oil')
        self.table_selection = tk.StringVar(value='Both')
        self._build_window()
        self._generate_curves(show_errors=False)

    def _build_window(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        inputs = ttk.LabelFrame(outer, text='Corey parameters', padding=10)
        inputs.grid(row=0, column=0, sticky=tk.EW)
        inputs.columnconfigure((0, 1, 2, 3), weight=1, uniform='parameter-columns')
        self._add_parameter_group(
            inputs, 'Water-oil (SWOF)', 0,
            [('Connate water, Swc', 'swc'), ('Residual oil, Sorw', 'sorw'),
             ('Endpoint krw', 'krw_end'), ('Endpoint krow', 'krow_end'),
             ('Water exponent, nw', 'nw'), ('Oil exponent, now', 'now')],
        )
        self._add_parameter_group(
            inputs, 'Gas-oil (SGOF)', 2,
            [('Critical gas, Sgc', 'sgc'), ('Residual oil, Sorg', 'sorg'),
             ('Endpoint krg', 'krg_end'), ('Endpoint krog', 'krog_end'),
             ('Gas exponent, ng', 'ng'), ('Oil exponent, nog', 'nog')],
        )

        controls = ttk.Frame(inputs)
        controls.grid(row=0, column=4, rowspan=5, padx=(16, 4), sticky=tk.NS)
        ttk.Label(controls, text='Saturation points').pack(anchor=tk.W, pady=(2, 4))
        self._add_entry(controls, 'points', width=12)
        ttk.Button(controls, text='Generate curves', command=self.generate_curves).pack(
            fill=tk.X, pady=(12, 5)
        )
        ttk.Label(controls, text='OPM tables').pack(anchor=tk.W, pady=(8, 4))
        ttk.Combobox(
            controls, textvariable=self.table_selection,
            values=('Both', 'SWOF', 'SGOF'), state='readonly', width=10,
        ).pack(fill=tk.X)
        self.export_button = ttk.Button(
            controls, text='Export OPM file', command=self.export_opm, state=tk.DISABLED
        )
        self.export_button.pack(fill=tk.X, pady=(6, 0))

        plot_frame = ttk.LabelFrame(outer, text='Relative permeability curves', padding=8)
        plot_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(12, 0))
        plot_frame.rowconfigure(1, weight=1)
        plot_frame.columnconfigure(0, weight=1)

        plot_controls = ttk.Frame(plot_frame)
        plot_controls.grid(row=0, column=0, sticky=tk.W, padx=4, pady=(0, 4))
        ttk.Radiobutton(
            plot_controls, text='Water-oil', value='Water-oil',
            variable=self.selected_plot, command=self._update_plot,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(
            plot_controls, text='Gas-oil', value='Gas-oil',
            variable=self.selected_plot, command=self._update_plot,
        ).pack(side=tk.LEFT)

        self.figure, self.axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky=tk.NSEW)
        self.status = tk.StringVar(value='Ready')
        ttk.Label(outer, textvariable=self.status, anchor=tk.W).grid(
            row=2, column=0, sticky=tk.EW, pady=(7, 0)
        )

    def _add_parameter_group(
        self,
        parent: ttk.LabelFrame,
        title: str,
        start_column: int,
        fields: list[tuple[str, str]],
    ) -> None:
        group = ttk.LabelFrame(parent, text=title, padding=8)
        group.grid(row=0, column=start_column, columnspan=2, rowspan=5, padx=4, sticky=tk.NSEW)
        group.columnconfigure((0, 1), weight=1)
        for index, (label, key) in enumerate(fields):
            row = index // 2
            column = index % 2
            ttk.Label(group, text=label).grid(
                row=row * 2, column=column, padx=5, pady=(4, 1), sticky=tk.W
            )
            self._add_entry(group, key, row=row * 2 + 1, column=column)

    def _add_entry(
        self,
        parent: tk.Misc,
        key: str,
        width: int = 13,
        row: int | None = None,
        column: int = 0,
    ) -> None:
        entry = ttk.Entry(parent, width=width)
        entry.insert(0, DEFAULTS[key])
        if row is None:
            entry.pack(anchor=tk.W)
        else:
            entry.grid(row=row, column=column, padx=5, pady=(0, 4), sticky=tk.EW)
        self.entries[key] = entry

    def _read_parameters(self) -> dict[str, float]:
        try:
            parameters = {key: float(entry.get()) for key, entry in self.entries.items()}
        except ValueError as error:
            raise ValueError('All Corey parameters must be valid numbers.') from error
        point_value = parameters['points']
        if not point_value.is_integer():
            raise ValueError('Saturation points must be an integer.')
        parameters['points'] = int(point_value)
        return parameters

    def _generate_curves(self, show_errors: bool = True) -> bool:
        try:
            self.curves = generate_corey_curves(self._read_parameters())
        except (KeyError, ValueError) as error:
            self.curves = None
            self.export_button.configure(state=tk.DISABLED)
            if show_errors:
                messagebox.showerror('Invalid Corey parameters', str(error), parent=self.root)
            self.status.set(str(error))
            return False
        self._update_plot()
        self.export_button.configure(state=tk.NORMAL)
        self.status.set(f"Generated {len(self.curves['sw'])} points per table.")
        return True

    def generate_curves(self) -> None:
        self._generate_curves()

    def _update_plot(self) -> None:
        if self.curves is None:
            return
        self.axis.clear()
        if self.selected_plot.get() == 'Water-oil':
            self.axis.plot(self.curves['sw'], self.curves['krw'], label='krw', color='#168aad', linewidth=2.2)
            self.axis.plot(self.curves['sw'], self.curves['krow'], label='krow', color='#e76f51', linewidth=2.2)
            self.axis.set_xlabel('Water saturation, Sw')
            self.axis.set_title('Corey water-oil relative permeability')
        else:
            self.axis.plot(self.curves['sg'], self.curves['krg'], label='krg', color='#168aad', linewidth=2.2)
            self.axis.plot(self.curves['sg'], self.curves['krog'], label='krog', color='#e76f51', linewidth=2.2)
            self.axis.set_xlabel('Gas saturation, Sg')
            self.axis.set_title('Corey gas-oil relative permeability')
        self.axis.set_ylabel('Relative permeability')
        self.axis.set_xlim(0, 1)
        self.axis.set_ylim(bottom=0)
        self.axis.grid(True, alpha=0.3)
        self.axis.legend(loc='best')
        self.canvas.draw_idle()

    def export_opm(self) -> None:
        if self.curves is None and not self._generate_curves():
            return
        output_path = filedialog.asksaveasfilename(
            parent=self.root,
            title='Export relative permeability tables',
            defaultextension='.txt',
            filetypes=[('OPM/Eclipse keyword files', '*.txt *.inc'), ('All files', '*.*')],
            initialfile='relative_permeability_corey.txt',
        )
        if not output_path:
            return
        try:
            text = format_opm_tables(self.curves, self.table_selection.get())
            Path(output_path).write_text(text, encoding='utf-8')
        except (OSError, ValueError) as error:
            messagebox.showerror('Export failed', str(error), parent=self.root)
            return
        self.status.set(f'Exported {self.table_selection.get()} table(s): {output_path}')
        messagebox.showinfo('Export complete', f'OPM tables saved to:\n{output_path}', parent=self.root)

    def close(self) -> None:
        plt.close(self.figure)
        self.root.quit()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    RelativePermeabilityApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
