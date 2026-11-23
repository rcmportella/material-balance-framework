import cv2
import numpy as np

# ============================================================
# ARQUIVOS
# ============================================================

TOPO_FILE = "BIT07A_SMC39 Topo.png"
MASK_FILE = "MASK.png"

# ============================================================
# GRID
# ============================================================

LEFT   = 32
RIGHT  = 1110
TOP    = 59
BOTTOM = 1055

NX = 72

DX = (RIGHT - LEFT) / NX
DY = DX

NY = round((BOTTOM - TOP) / DY)

# ============================================================
# LEGENDA
# ============================================================
#
# Ajuste apenas se necessário.
# O retângulo deve englobar somente a barra colorida.
#

BAR_X1 = 987
BAR_X2 = 1006

BAR_Y1 = 781
BAR_Y2 = 1094

# ============================================================
# ESCALA DE PROFUNDIDADE (POSITIVA)
# ============================================================

Z_TOP  = 1320.0
Z_BASE = 1610.0

# ============================================================
# LEITURA DOS ARQUIVOS
# ============================================================

img = cv2.imread(TOPO_FILE)

if img is None:
    raise RuntimeError(
        "Não consegui abrir o mapa estrutural."
    )

mask = cv2.imread(
    MASK_FILE,
    cv2.IMREAD_GRAYSCALE
)

if mask is None:
    raise RuntimeError(
        "Não consegui abrir MASK.png."
    )

# ============================================================
# TABELA RGB -> PROFUNDIDADE
# ============================================================

samples_rgb = []
samples_z   = []

for y in range(BAR_Y1, BAR_Y2 + 1):

    rgb = img[y, (BAR_X1 + BAR_X2)//2]

    frac = (
        (y - BAR_Y1)
        /
        (BAR_Y2 - BAR_Y1)
    )

    z = Z_TOP + frac*(Z_BASE - Z_TOP)

    samples_rgb.append(
        rgb.astype(np.float32)
    )

    samples_z.append(float(z))

samples_rgb = np.array(samples_rgb)
samples_z   = np.array(samples_z)

# ============================================================
# RGB -> PROFUNDIDADE
# ============================================================

def rgb_to_depth(rgb):

    rgb = rgb.astype(np.float32)

    diff = samples_rgb - rgb

    dist = np.sqrt(
        np.sum(
            diff**2,
            axis=1
        )
    )

    idx = np.argmin(dist)

    return float(samples_z[idx])

# ============================================================
# AMOSTRAGEM 3x3 NA CÉLULA
# ============================================================

def cell_depth(i, j):

    xc = LEFT + (i + 0.5)*DX
    yc = TOP  + (j + 0.5)*DY

    offsets = [

        (-0.25, -0.25),
        ( 0.00, -0.25),
        ( 0.25, -0.25),

        (-0.25,  0.00),
        ( 0.00,  0.00),
        ( 0.25,  0.00),

        (-0.25,  0.25),
        ( 0.00,  0.25),
        ( 0.25,  0.25),

    ]

    values = []

    for ox, oy in offsets:

        x = int(
            round(
                xc + ox*DX
            )
        )

        y = int(
            round(
                yc + oy*DY
            )
        )

        x = max(
            0,
            min(
                x,
                img.shape[1]-1
            )
        )

        y = max(
            0,
            min(
                y,
                img.shape[0]-1
            )
        )

        rgb = img[y, x]

        depth = rgb_to_depth(rgb)

        values.append(depth)

    return float(np.mean(values))

# ============================================================
# TOPS
# ============================================================

tops = []

for j in range(NY):

    for i in range(NX):

        xc = int(
            round(
                LEFT + (i + 0.5)*DX
            )
        )

        yc = int(
            round(
                TOP + (j + 0.5)*DY
            )
        )

        active = mask[yc, xc] > 127

        if active:

            z = cell_depth(i, j)

            tops.append(z)

        else:

            tops.append(9999.0)

# ============================================================
# ESCRITA DO ARQUIVO TOPS
# ============================================================

with open("TOPS.INC", "w") as f:

    f.write("TOPS\n")

    count = 0

    for value in tops:

        f.write(f"{value:.2f} ")

        count += 1

        if count % 8 == 0:
            f.write("\n")

    f.write("\n/\n")

# ============================================================
# RELATÓRIO
# ============================================================

active_values = [
    v for v in tops
    if v < 9999
]

print()
print("==================================")
print("TOPS.INC criado")
print("==================================")
print(f"NX      = {NX}")
print(f"NY      = {NY}")
print(f"NCELLS  = {NX*NY}")
print(f"TOP MIN = {min(active_values):.2f}")
print(f"TOP MAX = {max(active_values):.2f}")
print("==================================")