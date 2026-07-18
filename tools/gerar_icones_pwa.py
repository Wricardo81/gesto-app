from pathlib import Path
import struct
import zlib
import math


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


def criar_icone(tamanho, caminho, maskable=False):
    azul = (10, 25, 47, 255)
    azul_2 = (17, 34, 64, 255)
    ciano = (100, 255, 218, 255)
    branco = (255, 255, 255, 255)

    pixels = [
        [azul for _ in range(tamanho)]
        for _ in range(tamanho)
    ]

    centro = tamanho / 2
    raio_externo = tamanho * (0.30 if maskable else 0.34)
    raio_interno = tamanho * (0.22 if maskable else 0.25)

    for y in range(tamanho):
        for x in range(tamanho):
            distancia = math.sqrt(
                (x - centro) ** 2 + (y - centro) ** 2
            )

            if distancia < tamanho * 0.43:
                pixels[y][x] = azul_2

            if raio_interno <= distancia <= raio_externo:
                if not (
                    x > centro
                    and y < centro + tamanho * 0.08
                    and y > centro - tamanho * 0.18
                ):
                    pixels[y][x] = ciano

    barra_altura = max(8, tamanho // 14)
    barra_inicio_x = int(centro)
    barra_fim_x = int(centro + raio_externo * 0.72)
    barra_y = int(centro - barra_altura / 2)

    for y in range(barra_y, barra_y + barra_altura):
        for x in range(barra_inicio_x, barra_fim_x):
            if 0 <= x < tamanho and 0 <= y < tamanho:
                pixels[y][x] = ciano

    bloco = max(10, tamanho // 18)
    margem = int(tamanho * 0.16)

    for i in range(3):
        inicio_x = margem + i * int(bloco * 1.35)
        inicio_y = tamanho - margem - bloco

        for y in range(inicio_y, inicio_y + bloco):
            for x in range(inicio_x, inicio_x + bloco):
                if 0 <= x < tamanho and 0 <= y < tamanho:
                    pixels[y][x] = branco

    escrever_png(
        caminho,
        tamanho,
        tamanho,
        pixels,
    )


saida = Path("frontend/icons")
saida.mkdir(parents=True, exist_ok=True)

criar_icone(
    192,
    saida / "icon-192.png",
)

criar_icone(
    512,
    saida / "icon-512.png",
)

criar_icone(
    512,
    saida / "icon-maskable-512.png",
    maskable=True,
)

print("Ícones PWA gerados com sucesso.")
