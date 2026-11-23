from PIL import Image, ImageDraw
import os

# ---------------------------
# Configuração da malha
# ---------------------------

# Limites da moldura do mapa obtidos do mapa estrutural
LEFT = 32
RIGHT = 1110
TOP = 59
BOTTOM = 1055

# 3600 m entre 813800 e 817400
PIXELS_PER_50M = (RIGHT - LEFT) / 72.0  # 3600/50 = 72 células

GRID_COLOR = (0, 0, 0, 80)  # preto semitransparente
GRID_WIDTH = 1

# ---------------------------
# Arquivos de entrada
# ---------------------------

arquivos = [
    "BIT07A_SMC39 NetPay.png",
    "BIT07A_SMC39 Porosidade.png"
]

for arquivo in arquivos:

    if not os.path.exists(arquivo):
        print(f"Arquivo não encontrado: {arquivo}")
        continue

    img = Image.open(arquivo).convert("RGBA")

    camada_grid = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(camada_grid)

    # Linhas verticais
    ncols = int(round((RIGHT - LEFT) / PIXELS_PER_50M))

    for i in range(ncols + 1):
        x = LEFT + i * PIXELS_PER_50M
        draw.line(
            [(x, TOP), (x, BOTTOM)],
            fill=GRID_COLOR,
            width=GRID_WIDTH
        )

    # Linhas horizontais
    nrows = int(round((BOTTOM - TOP) / PIXELS_PER_50M))

    for j in range(nrows + 1):
        y = TOP + j * PIXELS_PER_50M
        draw.line(
            [(LEFT, y), (RIGHT, y)],
            fill=GRID_COLOR,
            width=GRID_WIDTH
        )

    resultado = Image.alpha_composite(img, camada_grid)

    nome_saida = arquivo.replace(".png", "_Grid50m.png")
    resultado.save(nome_saida)

    print(f"Gerado: {nome_saida}")

print("Concluído.")