"""
Gera ACTNUM para FLOW / OPM / Eclipse
a partir do mapa de NetPay.

Autor: Copilot

Saídas:
  ACTNUM.INC
  MASK.png
  POLYGON.png
"""

import cv2
import numpy as np


# ======================================================
# CONFIGURAÇÃO DA MALHA
# ======================================================

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
# LIMITES DE COR
# ======================================================

#
# A região produtiva é amarela / bege.
#
# Trabalhar em HSV é muito mais robusto
# do que RGB.
#

HSV_LOWER = np.array([15, 20, 150])
HSV_UPPER = np.array([45, 255, 255])


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
# CARREGA IMAGEM
# ======================================================

img_bgr = cv2.imread(IMAGE_FILE)

if img_bgr is None:
    raise FileNotFoundError(IMAGE_FILE)

img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

# ======================================================
# MÁSCARA DO RESERVATÓRIO
# ======================================================

mask = cv2.inRange(
    img_hsv,
    HSV_LOWER,
    HSV_UPPER
)

# ======================================================
# LIMPEZA MORFOLÓGICA
# ======================================================

kernel = np.ones((5, 5), np.uint8)

mask = cv2.morphologyEx(
    mask,
    cv2.MORPH_OPEN,
    kernel
)

mask = cv2.morphologyEx(
    mask,
    cv2.MORPH_CLOSE,
    kernel
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
        "Nenhuma região amarela encontrada."
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
# ARQUIVOS DE CONTROLE QA/QC
# ======================================================

cv2.imwrite("MASK.png", mask)

preview = img_bgr.copy()

cv2.drawContours(
    preview,
    [main_contour],
    -1,
    (0, 0, 255),
    3
)

cv2.imwrite(
    "POLYGON.png",
    preview
)

print()
print("===================================")
print("ACTNUM criado")
print("===================================")
print(f"NX = {NX}")
print(f"NY = {NY}")
print(f"NCELLS = {NX*NY}")
print()
print("Arquivos:")
print(" ACTNUM.INC")
print(" MASK.png")
print(" POLYGON.png")
print("===================================")