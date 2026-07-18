from pathlib import Path
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


def criar_screenshot(caminho, largura, altura):
    azul = (10, 25, 47, 255)
    azul_2 = (17, 34, 64, 255)
    ciano = (100, 255, 218, 255)
    branco = (255, 255, 255, 255)
    cinza = (136, 146, 176, 255)

    pixels = [
        [azul for _ in range(largura)]
        for _ in range(altura)
    ]

    for y in range(altura):
        for x in range(largura):
            if y < altura * 0.16:
                pixels[y][x] = azul_2

            if largura * 0.06 < x < largura * 0.94 and altura * 0.24 < y < altura * 0.40:
                pixels[y][x] = azul_2

            if largura * 0.06 < x < largura * 0.29 and altura * 0.48 < y < altura * 0.75:
                pixels[y][x] = azul_2

            if largura * 0.36 < x < largura * 0.59 and altura * 0.48 < y < altura * 0.75:
                pixels[y][x] = azul_2

            if largura * 0.66 < x < largura * 0.89 and altura * 0.48 < y < altura * 0.75:
                pixels[y][x] = azul_2

            if altura * 0.10 < y < altura * 0.12 and largura * 0.06 < x < largura * 0.24:
                pixels[y][x] = ciano

            if altura * 0.29 < y < altura * 0.31 and largura * 0.09 < x < largura * 0.60:
                pixels[y][x] = branco

            if altura * 0.35 < y < altura * 0.37 and largura * 0.09 < x < largura * 0.48:
                pixels[y][x] = cinza

            if altura * 0.57 < y < altura * 0.59:
                if largura * 0.09 < x < largura * 0.22:
                    pixels[y][x] = ciano
                if largura * 0.39 < x < largura * 0.52:
                    pixels[y][x] = ciano
                if largura * 0.69 < x < largura * 0.82:
                    pixels[y][x] = ciano

    escrever_png(
        caminho,
        largura,
        altura,
        pixels,
    )


saida = Path("frontend/screenshots")
saida.mkdir(parents=True, exist_ok=True)

criar_screenshot(
    saida / "desktop-wide.png",
    1280,
    720,
)

criar_screenshot(
    saida / "mobile-narrow.png",
    540,
    720,
)

print("Screenshots PWA gerados com sucesso.")
