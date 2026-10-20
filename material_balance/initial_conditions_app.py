"""Initial reservoir pressure and temperature from formation depth."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FIELDS = {
    'Furado (FU)': 'FU',
    'São Miguel dos Campos (SMC)': 'SMC',
    'Cidade de São Miguel dos Campos (CSMC)': 'CSMC',
}


def initial_pressure_kgf_cm2(field: str, depth_m: float) -> float:
    """Original reservoir pressure (kgf/cm2) for a field code and depth (m)."""
    if field == 'FU':
        return 0.106 * depth_m - 8.21
    if field in ('SMC', 'CSMC'):
        if depth_m < 900:
            return 0.097 * depth_m + 5.9
        return 0.112 * depth_m - 7.6
    raise ValueError(f'Unknown field: {field}')


def initial_temperature_c(field: str, depth_m: float) -> float:
    """Original reservoir temperature (degC) for a field code and depth (m)."""
    if field == 'FU':
        t_f = 0.0590 * depth_m + 69.7
    elif field in ('SMC', 'CSMC'):
        t_f = 0.0582 * depth_m + 82
    else:
        raise ValueError(f'Unknown field: {field}')
    return (t_f - 32) * 5 / 9


class InitialConditionsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title('Initial Pressure and Temperature')
        root.resizable(False, False)

        self.field_var = tk.StringVar(value=next(iter(FIELDS)))
        self.zone_var = tk.StringVar()
        self.depth_var = tk.StringVar()
        self.pressure_var = tk.StringVar(value='-')
        self.temperature_var = tk.StringVar(value='-')
        self.error_var = tk.StringVar()

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text='Field:').grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            frame, textvariable=self.field_var, values=list(FIELDS),
            state='readonly', width=38,
        ).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=4)

        ttk.Label(frame, text='Production zone:').grid(row=1, column=0, sticky=tk.W, pady=4)
        zone = ttk.Entry(frame, textvariable=self.zone_var, width=22)
        zone.grid(row=1, column=1, sticky=tk.W, pady=4)
        zone.configure(
            validate='key',
            validatecommand=(root.register(lambda v: len(v) <= 20), '%P'),
        )
        ttk.Label(frame, text='(record only)').grid(row=1, column=2, sticky=tk.W, padx=6)

        ttk.Label(frame, text='Formation depth (m):').grid(row=2, column=0, sticky=tk.W, pady=4)
        depth = ttk.Entry(frame, textvariable=self.depth_var, width=22)
        depth.grid(row=2, column=1, sticky=tk.W, pady=4)
        depth.bind('<Return>', lambda _e: self.calculate())

        ttk.Button(frame, text='Calculate', command=self.calculate).grid(
            row=3, column=0, columnspan=3, pady=10
        )

        ttk.Label(frame, text='Pressure (kgf/cm²):').grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Label(frame, textvariable=self.pressure_var, font=('Segoe UI', 10, 'bold')).grid(
            row=4, column=1, sticky=tk.W
        )
        ttk.Label(frame, text='Temperature (°C):').grid(row=5, column=0, sticky=tk.W, pady=2)
        ttk.Label(frame, textvariable=self.temperature_var, font=('Segoe UI', 10, 'bold')).grid(
            row=5, column=1, sticky=tk.W
        )
        ttk.Label(frame, textvariable=self.error_var, foreground='#b00020').grid(
            row=6, column=0, columnspan=3, sticky=tk.W, pady=(8, 0)
        )
        depth.focus_set()

    def calculate(self) -> None:
        try:
            depth_m = float(self.depth_var.get().replace(',', '.'))
            if depth_m <= 0:
                raise ValueError
        except ValueError:
            self.error_var.set('Enter a valid positive depth in meters.')
            self.pressure_var.set('-')
            self.temperature_var.set('-')
            return
        self.error_var.set('')
        code = FIELDS[self.field_var.get()]
        self.pressure_var.set(f'{initial_pressure_kgf_cm2(code, depth_m):.2f}')
        self.temperature_var.set(f'{initial_temperature_c(code, depth_m):.1f}')


def main() -> None:
    root = tk.Tk()
    InitialConditionsApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
