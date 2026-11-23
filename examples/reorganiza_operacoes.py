"""Reorganiza o "Início Produção" das operações de poços respeitando um limite
anual de operações.

Regras:
- Operações "Produzindo" não são modificadas nem contam para o limite.
- "Perfuração" tem limite anual próprio; as demais operações compartilham outro.
- Prioridade: data de início original (mais cedo primeiro); empate pela Classe
  (PDNP, PUD, 5PRB, 6POS). Operações podem ser antecipadas se houver vaga, mas
  nunca para antes do ano inicial (padrão 2027, isto é, 01/01/2027).
- Dentro de cada ano as operações são espalhadas uniformemente pelos meses
  (sempre no dia 1), mantendo a ordem de prioridade.
- Só a coluna "Início Produção" da primeira aba é alterada; fórmulas, demais
  abas e formatação são preservadas.
"""
from __future__ import annotations

import datetime as dt
import os
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, ttk

from openpyxl import load_workbook

CLASS_PRIORITY = {'PDNP': 0, 'PUD': 1, '5PRB': 2, '6POS': 3}
DRILLING = 'perfuracao'
FIXED = 'produzindo'


def norm(value) -> str:
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode()
    return ' '.join(text.lower().split())


def find_columns(ws) -> dict[str, int]:
    wanted = {'inicio producao': 'start', 'operacao': 'op', 'classe': 'cls'}
    cols = {}
    for cell in ws[1]:
        key = wanted.get(norm(cell.value))
        if key:
            cols[key] = cell.column
    missing = set(wanted.values()) - set(cols)
    if missing:
        raise ValueError('Colunas ausentes na primeira linha: Início Produção, Operação e/ou Classe.')
    return cols


def spread_months(count: int) -> list[int]:
    return [1 + (i * 12) // count for i in range(count)]


def reschedule(ws, cols, limit_other: int, limit_drilling: int, start_year: int = 2027) -> dict:
    """Atualiza ws e devolve estatísticas."""
    groups: dict[str, list] = {'drilling': [], 'other': []}
    for row in range(2, ws.max_row + 1):
        start = ws.cell(row, cols['start']).value
        op = norm(ws.cell(row, cols['op']).value)
        if not isinstance(start, (dt.datetime, dt.date)) or not op or op == FIXED:
            continue
        cls = CLASS_PRIORITY.get(norm(ws.cell(row, cols['cls']).value).upper(), len(CLASS_PRIORITY))
        key = 'drilling' if op == DRILLING else 'other'
        groups[key].append((start, cls, row))

    all_items = groups['drilling'] + groups['other']
    if not all_items:
        raise ValueError('Nenhuma operação a reorganizar foi encontrada.')

    changed = 0
    per_year: dict[tuple[str, int], int] = {}
    for key, limit in (('drilling', limit_drilling), ('other', limit_other)):
        items = sorted(groups[key], key=lambda it: (it[0], it[1], it[2]))
        year = start_year
        for i in range(0, len(items), limit):
            chunk = items[i:i + limit]
            months = spread_months(len(chunk))
            for (start, _, row), month in zip(chunk, months):
                cell = ws.cell(row, cols['start'])
                new = start.replace(year=year, month=month, day=1)
                if new != start:
                    changed += 1
                cell.value = new
            per_year[(key, year)] = len(chunk)
            year += 1
    return {'total': len(all_items), 'changed': changed, 'per_year': per_year}


def run(input_path: str, output_path: str, limit_other: int, limit_drilling: int,
        start_year: int = 2027) -> dict:
    if limit_other < 1 or limit_drilling < 1:
        raise ValueError('Os limites anuais devem ser inteiros maiores que zero.')
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError('Escolha um arquivo de saída diferente do de entrada.')
    wb = load_workbook(input_path)
    ws = wb.worksheets[0]
    stats = reschedule(ws, find_columns(ws), limit_other, limit_drilling, start_year)
    wb.save(output_path)
    return stats


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Reorganização de Operações por Ano')
        self.resizable(False, False)
        self.in_var = tk.StringVar()
        self.out_var = tk.StringVar()
        self.other_var = tk.StringVar(value='12')
        self.drill_var = tk.StringVar(value='4')
        self.year_var = tk.StringVar(value='2027')

        frm = ttk.Frame(self, padding=12)
        frm.grid()
        ttk.Label(frm, text='Arquivo de entrada:').grid(row=0, column=0, sticky='w')
        ttk.Entry(frm, textvariable=self.in_var, width=60).grid(row=0, column=1, padx=6, pady=3)
        ttk.Button(frm, text='Procurar...', command=self.pick_input).grid(row=0, column=2)
        ttk.Label(frm, text='Arquivo de saída:').grid(row=1, column=0, sticky='w')
        ttk.Entry(frm, textvariable=self.out_var, width=60).grid(row=1, column=1, padx=6, pady=3)
        ttk.Button(frm, text='Salvar como...', command=self.pick_output).grid(row=1, column=2)
        ttk.Label(frm, text='Operações por ano (exceto Perfuração):').grid(row=2, column=0, sticky='w')
        ttk.Spinbox(frm, from_=1, to=1000, textvariable=self.other_var, width=8).grid(row=2, column=1, sticky='w', padx=6, pady=3)
        ttk.Label(frm, text='Perfurações por ano:').grid(row=3, column=0, sticky='w')
        ttk.Spinbox(frm, from_=1, to=1000, textvariable=self.drill_var, width=8).grid(row=3, column=1, sticky='w', padx=6, pady=3)
        ttk.Label(frm, text='Ano inicial:').grid(row=4, column=0, sticky='w')
        ttk.Spinbox(frm, from_=2000, to=2100, textvariable=self.year_var, width=8).grid(row=4, column=1, sticky='w', padx=6, pady=3)
        ttk.Button(frm, text='Reorganizar', command=self.execute).grid(row=5, column=1, pady=8, sticky='e')

    def pick_input(self):
        path = filedialog.askopenfilename(filetypes=[('Excel', '*.xlsx *.xlsm')])
        if path:
            self.in_var.set(path)
            if not self.out_var.get():
                base, ext = os.path.splitext(path)
                self.out_var.set(f'{base}_reorganizado{ext}')

    def pick_output(self):
        path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel', '*.xlsx')])
        if path:
            self.out_var.set(path)

    def execute(self):
        try:
            stats = run(self.in_var.get().strip(), self.out_var.get().strip(),
                        int(self.other_var.get()), int(self.drill_var.get()),
                        int(self.year_var.get()))
        except PermissionError:
            messagebox.showerror('Erro', 'Sem permissão para ler/gravar o arquivo. Feche-o no Excel e tente novamente.')
            return
        except Exception as exc:
            messagebox.showerror('Erro', str(exc))
            return
        years = sorted({y for _, y in stats['per_year']})
        messagebox.showinfo(
            'Concluído',
            f"{stats['total']} operações reorganizadas ({stats['changed']} datas alteradas).\n"
            f"Anos utilizados: {years[0]}–{years[-1]}.\nArquivo salvo em:\n{self.out_var.get()}")


if __name__ == '__main__':
    App().mainloop()

