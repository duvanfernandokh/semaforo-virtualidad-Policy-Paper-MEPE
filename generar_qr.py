# -*- coding: utf-8 -*-
"""Genera el código QR del tablero para insertarlo en el Anexo 7.

Uso:  python3 generar_qr.py https://direccion-del-tablero

Produce qr_tablero.png, listo para reemplazar el recuadro reservado del anexo.
Requiere: pip install "qrcode[pil]"
"""
import sys

from pathlib import Path

import qrcode

SALIDAS = Path(__file__).resolve().parent / 'salidas'
SALIDAS.mkdir(exist_ok=True)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    url = sys.argv[1]
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    img.save(SALIDAS / 'qr_tablero.png')
    print(f'salidas/qr_tablero.png generado para {url}')


if __name__ == '__main__':
    main()
