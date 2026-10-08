"""Launch the petroleum engineering desktop applications from one window."""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Application:
    key: str
    name: str
    category: str
    command: tuple[str, ...]


def get_applications(project_root: Path = PROJECT_ROOT) -> tuple[Application, ...]:
    python = sys.executable
    examples = project_root / 'examples'
    return (
        Application(
            'oil_balance', 'Oil Material Balance', 'Reservoir & PVT',
            (python, '-m', 'material_balance.oil_material_balance_app'),
        ),
        Application(
            'gas_pz', 'Gas P/Z Analysis', 'Reservoir & PVT',
            (python, '-m', 'material_balance.gas_pz_app'),
        ),
        Application(
            'pvt_table', 'PVT Table Generator', 'Reservoir & PVT',
            (python, '-m', 'material_balance.PVT_table'),
        ),
        Application(
            'relative_permeability', 'Relative Permeability (Corey)', 'Reservoir & PVT',
            (python, '-m', 'material_balance.relative_permeability_app'),
        ),
        Application(
            'production_decline', 'Production Decline', 'Well Production',
            (python, str(examples / 'extrapola_producao_pocos.py')),
        ),
        Application(
            'well_production', 'Well Production Viewer', 'Well Production',
            (python, str(examples / 'plota_producao_pocos.py')),
        ),
    )


class ApplicationLauncher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Petroleum Engineering Workbench')
        self.root.geometry('860x480')
        self.root.minsize(720, 400)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

        self.applications = get_applications()
        self.processes: dict[str, subprocess.Popen[bytes]] = {}
        self.status_vars: dict[str, tk.StringVar] = {}
        self.launch_buttons: dict[str, ttk.Button] = {}
        self.closing = False

        self._configure_style()
        self._build_window()
        self.root.after(500, self._refresh_processes)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.configure('WorkbenchTitle.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('WorkbenchNote.TLabel', foreground='#596b68')
        style.configure('Application.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('Status.TLabel', foreground='#596b68')
        style.configure('ToolGroup.TLabelframe', padding=10)
        style.configure('ToolGroup.TLabelframe.Label', font=('Segoe UI', 10, 'bold'))

    def _build_window(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure((0, 1), weight=1, uniform='tool-groups')
        container.rowconfigure(1, weight=1)

        ttk.Label(
            container, text='Petroleum Engineering Workbench',
            style='WorkbenchTitle.TLabel',
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        groups: dict[str, list[Application]] = {}
        for application in self.applications:
            groups.setdefault(application.category, []).append(application)

        for column, category in enumerate(('Reservoir & PVT', 'Well Production')):
            group = ttk.LabelFrame(
                container, text=category, style='ToolGroup.TLabelframe'
            )
            group.grid(
                row=1, column=column, sticky=tk.NSEW,
                padx=(0, 8) if column == 0 else (8, 0), pady=(18, 12),
            )
            group.columnconfigure(0, weight=1)
            for row, application in enumerate(groups.get(category, [])):
                self._add_application_row(group, application, row)

        ttk.Separator(container).grid(row=2, column=0, columnspan=2, sticky=tk.EW)
        ttk.Label(
            container,
            text='Closing the workbench closes applications launched from it.',
            style='WorkbenchNote.TLabel',
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    def _add_application_row(
        self, parent: ttk.LabelFrame, application: Application, row: int
    ) -> None:
        grid_row = row * 2
        row_frame = ttk.Frame(parent, padding=(4, 9))
        row_frame.grid(row=grid_row, column=0, sticky=tk.EW)
        row_frame.columnconfigure(0, weight=1)

        ttk.Label(row_frame, text=application.name, style='Application.TLabel').grid(
            row=0, column=0, sticky=tk.W
        )
        status = tk.StringVar(value='Ready')
        self.status_vars[application.key] = status
        ttk.Label(row_frame, textvariable=status, style='Status.TLabel').grid(
            row=1, column=0, sticky=tk.W, pady=(3, 0)
        )
        button = ttk.Button(
            row_frame, text='Open', command=lambda app=application: self.launch(app)
        )
        button.grid(row=0, column=1, rowspan=2, padx=(12, 2))
        self.launch_buttons[application.key] = button

        ttk.Separator(parent).grid(row=grid_row + 1, column=0, sticky=tk.EW)

    def launch(self, application: Application) -> None:
        process = self.processes.get(application.key)
        if process is not None and process.poll() is None:
            self.status_vars[application.key].set('Already running')
            return

        try:
            process = subprocess.Popen(
                application.command,
                cwd=PROJECT_ROOT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except OSError as error:
            messagebox.showerror(
                'Could not open application',
                f'{application.name}\n\n{error}',
                parent=self.root,
            )
            return

        self.processes[application.key] = process
        self.status_vars[application.key].set('Running')
        self.launch_buttons[application.key].configure(state=tk.DISABLED)

    def _refresh_processes(self) -> None:
        if self.closing:
            return
        for application in self.applications:
            process = self.processes.get(application.key)
            if process is None:
                continue
            exit_code = process.poll()
            if exit_code is None:
                continue
            self.status_vars[application.key].set(
                'Closed' if exit_code == 0 else f'Exited ({exit_code})'
            )
            self.launch_buttons[application.key].configure(state=tk.NORMAL)
            del self.processes[application.key]
        self.root.after(500, self._refresh_processes)

    def close(self) -> None:
        self.closing = True
        for process in self.processes.values():
            if process.poll() is None:
                process.terminate()
        for process in self.processes.values():
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ApplicationLauncher(root)
    root.mainloop()


if __name__ == '__main__':
    main()