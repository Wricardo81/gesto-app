from pathlib import Path
import math
import struct
import zlib


def escrever_png(caminho, largura, altura, pixels):
    raw = bytearray()

    for y in range(altura):
        raw.append(0)
        for x in range(largura):
            raw.extend(pixels[y][x])

    def chunk(tipo, dados):
        return (
            struct.pack(">I", len(dados))
            + tipo
            + dados
            + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", largura, altura, 8, 6, 0, 0, 0),
    )
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    caminho.write_bytes(png)


def dentro_retangulo_arredondado(x, y, left, top, right, bottom, radius):
    if x < left or x > right or y < top or y > bottom:
        return False

    if left + radius <= x <= right - radius:
        return True

    if top + radius <= y <= bottom - radius:
        return True

    cantos = [
        (left + radius, top + radius),
        (right - radius, top + radius),
        (left + radius, bottom - radius),
        (right - radius, bottom - radius),
    ]

    return any((x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 for cx, cy in cantos)


def criar_icone(tamanho, caminho, maskable=False):
    azul_profundo = (10, 25, 47, 255)
    azul_card = (17, 34, 64, 255)
    ciano = (100, 255, 218, 255)
    azul_neon = (56, 189, 248, 255)
    branco = (248, 250, 252, 255)

    pixels = [[azul_profundo for _ in range(tamanho)] for _ in range(tamanho)]

    centro = tamanho / 2

    # Fundo radial simples
    for y in range(tamanho):
        for x in range(tamanho):
            dx = x - centro
            dy = y - centro
            d = math.sqrt(dx * dx + dy * dy)

            if d < tamanho * 0.48:
                pixels[y][x] = azul_card

            if d < tamanho * 0.34:
                pixels[y][x] = (
                    int((azul_card[0] + azul_profundo[0]) / 2),
                    int((azul_card[1] + azul_profundo[1]) / 2),
                    int((azul_card[2] + azul_profundo[2]) / 2),
                    255,
                )

    # Moldura externa
    raio_externo = tamanho * (0.40 if not maskable else 0.34)
    raio_interno = tamanho * (0.36 if not maskable else 0.30)

    for y in range(tamanho):
        for x in range(tamanho):
            d = math.sqrt((x - centro) ** 2 + (y - centro) ** 2)
            if raio_interno <= d <= raio_externo:
                pixels[y][x] = ciano

    # Calendário minimalista
    cal_w = int(tamanho * 0.50)
    cal_h = int(tamanho * 0.46)
    cal_left = int((tamanho - cal_w) / 2)
    cal_top = int(tamanho * 0.25)
    cal_right = cal_left + cal_w
    cal_bottom = cal_top + cal_h
    radius = int(tamanho * 0.045)

    for y in range(tamanho):
        for x in range(tamanho):
            if dentro_retangulo_arredondado(
                x,
                y,
                cal_left,
                cal_top,
                cal_right,
                cal_bottom,
                radius,
            ):
                pixels[y][x] = branco

    # Topo do calendário
    topo_h = int(cal_h * 0.23)
    for y in range(cal_top, cal_top + topo_h):
        for x in range(cal_left, cal_right):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = ciano

    # Argolas
    argola_w = max(4, tamanho // 26)
    argola_h = max(10, tamanho // 12)
    for cx in (cal_left + int(cal_w * 0.25), cal_left + int(cal_w * 0.75)):
        for y in range(cal_top - argola_h // 2, cal_top + argola_h // 2):
            for x in range(cx - argola_w // 2, cx + argola_w // 2):
                if 0 <= x < tamanho and 0 <= y < tamanho:
                    pixels[y][x] = azul_neon

    # Letra B estilizada
    b_left = cal_left + int(cal_w * 0.21)
    b_top = cal_top + int(cal_h * 0.34)
    b_w = int(cal_w * 0.30)
    b_h = int(cal_h * 0.42)

    stroke = max(5, tamanho // 28)

    # haste do B
    for y in range(b_top, b_top + b_h):
        for x in range(b_left, b_left + stroke):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = azul_profundo

    # partes superior/inferior do B
    for y in range(b_top, b_top + stroke):
        for x in range(b_left, b_left + b_w):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = azul_profundo

    meio_y = b_top + b_h // 2
    for y in range(meio_y - stroke // 2, meio_y + stroke // 2):
        for x in range(b_left, b_left + b_w):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = azul_profundo

    for y in range(b_top + b_h - stroke, b_top + b_h):
        for x in range(b_left, b_left + b_w):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = azul_profundo

    # lado direito do B
    for y in range(b_top, b_top + b_h):
        for x in range(b_left + b_w - stroke, b_left + b_w):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = azul_profundo

    # check de confirmação
    check_points = []
    start_x = cal_left + int(cal_w * 0.58)
    start_y = cal_top + int(cal_h * 0.58)

    for i in range(int(tamanho * 0.10)):
        check_points.append((start_x + i, start_y + i))

    for i in range(int(tamanho * 0.18)):
        check_points.append(
            (
                start_x + int(tamanho * 0.10) + i,
                start_y + int(tamanho * 0.10) - i,
            )
        )

    check_stroke = max(5, tamanho // 30)

    for px, py in check_points:
        for y in range(py - check_stroke, py + check_stroke):
            for x in range(px - check_stroke, px + check_stroke):
                if 0 <= x < tamanho and 0 <= y < tamanho:
                    if (x - px) ** 2 + (y - py) ** 2 <= check_stroke ** 2:
                        pixels[y][x] = ciano

    escrever_png(caminho, tamanho, tamanho, pixels)


saida = Path("frontend/icons")
saida.mkdir(parents=True, exist_ok=True)

criar_icone(192, saida / "bitsagenda-icon-192.png")
criar_icone(512, saida / "bitsagenda-icon-512.png")
criar_icone(512, saida / "bitsagenda-maskable-512.png", maskable=True)

print("Ícones BitsAgenda OS gerados com sucesso.")
