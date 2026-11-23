"""
Gera ACTNUM para FLOW / OPM / Eclipse
a partir de uma máscara já existente (MASK.png).

A máscara foi gerada externamente: pixels brancos (> 127)
representam a região ativa; pixels pretos, a região inativa.
A máscara deve ter as mesmas dimensões (e o mesmo sistema de
coordenadas em pixels) do mapa usado para definir a malha.

Saídas:
  ACTNUM.INC
  POLYGON.png
"""

import os

import cv2
import numpy as np


# ======================================================
# CONFIGURAÇÃO DA MALHA
# ======================================================

MASK_FILE = "MASK.png"

# Imagem opcional, usada apenas como fundo do POLYGON.png.
# Se não existir, o contorno é desenhado sobre a própria máscara.
IMAGE_FILE = "BIT07A_SMC39 NetPay.png"

LEFT   = 32
RIGHT  = 1110
TOP    = 59
BOTTOM = 1055

NX = 72

DX = (RIGHT - LEFT) / NX
DY = DX

NY = int(round((BOTTOM - TOP) / DY))


# ======================================================
# COMPRESSÃO RLE ESTILO ECLIPSE
# ======================================================

def eclipse_compress(values):

    result = []

    current = values[0]
    count = 1

    for value in values[1:]:

        if value == current:
            count += 1

        else:

            if count == 1:
                result.append(str(current))
            else:
                result.append(f"{count}*{current}")

            current = value
            count = 1

    if count == 1:
        result.append(str(current))
    else:
        result.append(f"{count}*{current}")

    return result


# ======================================================
# CARREGA MÁSCARA EXISTENTE
# ======================================================

mask = cv2.imread(MASK_FILE, cv2.IMREAD_GRAYSCALE)

if mask is None:
    raise FileNotFoundError(MASK_FILE)

# garante máscara binária (0 / 255)
_, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

mask_h, mask_w = mask.shape

if RIGHT > mask_w or BOTTOM > mask_h:
    raise ValueError(
        f"A malha (RIGHT={RIGHT}, BOTTOM={BOTTOM}) excede as "
        f"dimensões da máscara ({mask_w}x{mask_h})."
    )

# ======================================================
# CONTORNOS
# ======================================================

contours, _ = cv2.findContours(
    mask,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

if len(contours) == 0:
    raise RuntimeError(
        "Nenhuma região ativa encontrada na máscara."
    )

# maior corpo conectado

main_contour = max(
    contours,
    key=cv2.contourArea
)

# ======================================================
# OPCIONAL:
# SUAVIZA O POLÍGONO
# ======================================================

epsilon = 0.002 * cv2.arcLength(
    main_contour,
    True
)

main_contour = cv2.approxPolyDP(
    main_contour,
    epsilon,
    True
)

# ======================================================
# ACTNUM
# ======================================================

actnum = []

for j in range(NY):

    for i in range(NX):

        xc = int(round(
            LEFT + (i + 0.5) * DX
        ))

        yc = int(round(
            TOP + (j + 0.5) * DY
        ))

        inside = cv2.pointPolygonTest(
            main_contour,
            (float(xc), float(yc)),
            False
        )

        if inside >= 0:
            actnum.append(1)
        else:
            actnum.append(0)

# ======================================================
# COMPRESSÃO
# ======================================================

compressed = eclipse_compress(actnum)

# ======================================================
# ESCREVE ACTNUM
# ======================================================

with open("ACTNUM.INC", "w") as f:

    f.write("ACTNUM\n")

    line = ""

    for token in compressed:

        test_line = line + token + " "

        if len(test_line) > 120:
            f.write(line + "\n")
            line = token + " "
        else:
            line = test_line

    if line:
        f.write(line + "\n")

    f.write("/\n")


# ======================================================
# ARQUIVO DE CONTROLE QA/QC
# ======================================================

preview = None

if os.path.exists(IMAGE_FILE):
    preview = cv2.imread(IMAGE_FILE)

if preview is None or preview.shape[:2] != mask.shape:
    preview = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

cv2.drawContours(
    preview,
    [main_contour],
    -1,
    (0, 0, 255),
    3
)

if not cv2.imwrite("POLYGON.png", preview):
    raise IOError(
        "Não foi possível gravar POLYGON.png "
        "(feche o arquivo se estiver aberto em algum visualizador)."
    )

print()
print("===================================")
print("ACTNUM criado")
print("===================================")
print(f"NX = {NX}")
print(f"NY = {NY}")
print(f"NCELLS = {NX*NY}")
print(f"ATIVAS = {sum(actnum)}")
print()
print("Arquivos:")
print(" ACTNUM.INC")
print(" POLYGON.png")
print("===================================")
