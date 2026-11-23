#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv


def rle(values):
    """
    Run Length Encoding no formato ECLIPSE/OPM.

    Exemplo:
    [1,1,1,0,0,1] -> ['3*1', '2*0', '1*1']
    """

    if len(values) == 0:
        return []

    result = []

    current = values[0]
    count = 1

    for value in values[1:]:

        if value == current:
            count += 1

        else:
            result.append(f"{count}*{current}")
            current = value
            count = 1

    result.append(f"{count}*{current}")

    return result


def write_actnum(csv_file, output_file, tokens_per_line=12):

    values = []
    with open(csv_file, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)

        if reader.fieldnames is None or "value" not in reader.fieldnames:
            raise ValueError(f"O arquivo CSV deve conter uma coluna 'value': {csv_file}")

        for row_number, row in enumerate(reader, start=2):
            try:
                values.append(int(row["value"]))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Valor inválido na linha {row_number} da coluna 'value': "
                    f"{row.get('value')!r}"
                ) from error

    encoded = rle(values)

    with open(output_file, "w", encoding="utf-8") as f:

        f.write("ACTNUM\n")

        for i, token in enumerate(encoded):

            f.write(token)

            if (i + 1) % tokens_per_line == 0:
                f.write("\n")
            else:
                f.write(" ")

        f.write("\n/\n")

    print(f"Arquivo gerado: {output_file}")
    print(f"Número de células: {len(values)}")
    print(f"Número de blocos compactados: {len(encoded)}")


if __name__ == "__main__":
    from pathlib import Path

    app_dir = Path(__file__).resolve().parent
    write_actnum(
        csv_file=app_dir / "reservatorio_mask.csv",
        output_file=app_dir / "ACTNUM.inc"
    )