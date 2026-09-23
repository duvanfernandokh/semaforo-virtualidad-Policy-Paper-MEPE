# -*- coding: utf-8 -*-
"""Figura 2: cobertura de la acreditación por campo de conocimiento y modalidad.

Barras horizontales pareadas. Paleta categórica validada (slots 1 y 2):
azul #2a78d6 para presencial, naranja #eb6834 para virtual.
"""
import csv
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from pathlib import Path

DATOS = Path(__file__).resolve().parent / 'datos'
SALIDAS = Path(__file__).resolve().parent / 'salidas'
SALIDAS.mkdir(exist_ok=True)


AZUL = '#2a78d6'
NARANJA = '#eb6834'
TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
TINTA_3 = '#8a8984'
SUPERFICIE = '#ffffff'

CORTOS = {
    'Salud Y Bienestar': 'Salud y bienestar',
    'Ciencias Naturales, Matematicas Y Estadistica': 'Ciencias naturales y matemáticas',
    'Ciencias Sociales, Periodismo E Informacion': 'Ciencias sociales y periodismo',
    'Educacion': 'Educación',
    'Ingenieria, Industria Y Construccion': 'Ingeniería e industria',
    'Arte Y Humanidades': 'Arte y humanidades',
    'Agropecuario, Silvicultura, Pesca Y Veterinaria': 'Agropecuario y veterinaria',
    'Servicios': 'Servicios',
    'Administracion De Empresas Y Derecho': 'Administración y derecho',
    'Tecnologias De La Informacion Y La Comunicacion (Tic)': 'Tecnologías de la información',
}

cov = defaultdict(lambda: defaultdict(lambda: [0, 0]))
with open(DATOS / 'panel_programa.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['cohorte'] != '2022' or r['acreditado'] == '':
            continue
        cov[r['area']][r['modalidad']][0] += 1
        cov[r['area']][r['modalidad']][1] += int(r['acreditado'])

datos = []
for area, d in cov.items():
    pt, pa = d['Presencial']
    vt, va = d['Virtual']
    datos.append((CORTOS.get(area, area),
                  100 * pa / pt if pt else 0,
                  100 * va / vt if vt else 0))
datos.sort(key=lambda x: x[1])

etiquetas = [d[0] for d in datos]
pres = [d[1] for d in datos]
virt = [d[2] for d in datos]

fig, ax = plt.subplots(figsize=(9.8, 4.5), dpi=300)
fig.patch.set_facecolor(SUPERFICIE)
ax.set_facecolor(SUPERFICIE)

alto = 0.34
hueco = 0.03          # separación de 2 px entre barras contiguas
ys = range(len(etiquetas))


def barra(y, valor, color):
    """Barra con extremo redondeado y anclada en el eje."""
    if valor <= 0:
        ax.plot([0.12], [y], marker='|', color=color, markersize=7, mew=1.6)
        return
    radio = min(0.6, valor / 2)
    p = FancyBboxPatch((0, y - alto / 2), max(valor - radio, 0.01), alto,
                       boxstyle=f'round,pad=0,rounding_size={radio}',
                       linewidth=0, facecolor=color, mutation_aspect=0.045)
    ax.add_patch(p)


for i, (p_, v_) in enumerate(zip(pres, virt)):
    barra(i + (alto + hueco) / 2, p_, AZUL)
    barra(i - (alto + hueco) / 2, v_, NARANJA)
    ax.text(p_ + 0.7, i + (alto + hueco) / 2, f'{p_:.0f} %', va='center', ha='left',
            fontsize=8.5, color=TINTA_2)
    ax.text(max(v_, 0) + 0.7, i - (alto + hueco) / 2, f'{v_:.0f} %', va='center',
            ha='left', fontsize=8.5,
            color=TINTA_2 if v_ > 0 else TINTA_3)

ax.set_yticks(list(ys))
ax.set_yticklabels(etiquetas, fontsize=9, color=TINTA)
ax.set_xlim(0, 44)
ax.set_ylim(-0.75, len(etiquetas) - 0.25)
ax.set_xlabel('Programas con acreditación de alta calidad (%)', fontsize=9.5, color=TINTA_2,
              labelpad=8)
ax.tick_params(axis='x', labelsize=9, colors=TINTA_2, length=0)
ax.tick_params(axis='y', length=0)
ax.xaxis.grid(True, color='#e6e5e1', linewidth=0.8)
ax.set_axisbelow(True)
for lado in ('top', 'right', 'left'):
    ax.spines[lado].set_visible(False)
ax.spines['bottom'].set_color('#d5d4cf')
ax.spines['bottom'].set_linewidth(0.8)

manijas = [plt.Line2D([0], [0], color=AZUL, lw=7, solid_capstyle='round'),
           plt.Line2D([0], [0], color=NARANJA, lw=7, solid_capstyle='round')]
leg = ax.legend(manijas, ['Presencial', 'Virtual'], loc='lower right',
                bbox_to_anchor=(1.0, 1.005), ncol=2, frameon=False, fontsize=9.5,
                handlelength=1.1, handletextpad=0.6, columnspacing=1.6)
for t in leg.get_texts():
    t.set_color(TINTA)

fig.tight_layout()
fig.savefig(SALIDAS / 'figura_cobertura.png', dpi=300, bbox_inches='tight', facecolor=SUPERFICIE)
print(SALIDAS / 'figura_cobertura.png')
for e, p_, v_ in datos:
    print(f'  {e:<34} presencial {p_:>5.1f} %   virtual {v_:>5.1f} %')
