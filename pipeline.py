# -*- coding: utf-8 -*-
"""
EL SEMÁFORO DE LA VIRTUALIDAD — construcción del panel 2018-2022
================================================================
Cruza las bases de graduados del SNIES con las bases IBC del Observatorio
Laboral para la Educación y produce:

  panel_celda.csv    área CINE campo amplio × modalidad × cohorte
  panel_programa.csv programa × cohorte (para el modelo con acreditación)
  semaforo.csv       clasificación por área

Cada cohorte de graduación t se observa en la base IBC del año de corte t+1,
que es el seguimiento a un año que el OLE define como «recién graduados».

Ejecución:  python3 pipeline.py
"""
import csv
import unicodedata
from collections import defaultdict, Counter

import openpyxl

from pathlib import Path

DATOS = Path(__file__).resolve().parent / 'datos'
DATOS.mkdir(exist_ok=True)

# --------------------------------------------------------------------------
# 1. RUTAS  (ajustar a la carpeta local antes de ejecutar)
# --------------------------------------------------------------------------
BASE = '/root/.claude/uploads/48069b8c-df83-5bc0-bf52-749e61fe81fc/'

LIBRO_IBC = BASE + 'd584c7d0-IBC_COHORTE_2019-2023.xlsx'
LIBRO_GRAD = BASE + '67af009f-GRADUADOS_2019-2022.xlsx'
ARCHIVO_2018 = BASE + '5770ae62-Graduados_2018.xlsx'

# cohorte -> (fuente de graduados, hoja de IBC del año de corte siguiente)
COHORTES = {
    2018: ((ARCHIVO_2018, 'Graduados 2018'), 'IBC 2019'),
    2019: ((LIBRO_GRAD, 'Graduados 2019'), 'IBC 2020'),
    2020: ((LIBRO_GRAD, 'Graduados 2020'), 'IBC 2021'),
    2021: ((LIBRO_GRAD, 'Graduados 2021'), 'IBC 2022'),
    2022: ((LIBRO_GRAD, 'Graduados 2022'), 'IBC 2023'),
}

# --------------------------------------------------------------------------
# 2. ARMONIZACIÓN
# --------------------------------------------------------------------------
# El SNIES renombró las metodologías a partir de la vigencia 2021: lo que antes
# era «Distancia (virtual)» pasó a llamarse «Virtual», y «Distancia
# (tradicional)» pasó a «A distancia». Ambas etiquetas de virtualidad se
# unifican; la distancia tradicional, la dual y las híbridas quedan fuera del
# alcance del estudio.
VIRTUAL = {'virtual', 'distancia (virtual)'}
PRESENCIAL = {'presencial'}


def sin_tildes(s):
    if s is None:
        return ''
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).strip()


def norm(s):
    return sin_tildes(s).lower()


def modalidad(metodologia):
    m = norm(metodologia)
    if m in VIRTUAL:
        return 'Virtual'
    if m in PRESENCIAL:
        return 'Presencial'
    return 'Excluida'


def codigo(v):
    """El código SNIES llega como texto y a veces con decimal ('19.0')."""
    if v is None:
        return None
    s = str(v).strip()
    return s[:-2] if s.endswith('.0') else s


# --------------------------------------------------------------------------
# 3. LECTURA
# --------------------------------------------------------------------------
def leer(libro, hoja):
    """Devuelve (índice de columnas normalizado, filas) de una hoja."""
    wb = openpyxl.load_workbook(libro, read_only=True, data_only=True)
    ws = wb[hoja]
    it = ws.iter_rows(values_only=True)
    cab = [norm(x) if x is not None else x for x in next(it)]
    idx = {k: i for i, k in enumerate(cab) if k}
    return idx, [r for r in it if r[0] is not None]


def col(idx, *alias):
    """Busca una columna por varios nombres posibles; los archivos anuales del
    SNIES cambian mayúsculas, tildes y hasta el nombre entre vigencias."""
    for a in alias:
        k = norm(a)
        if k in idx:
            return idx[k]
    for a in alias:
        k = norm(a)
        for nombre, i in idx.items():
            if nombre.startswith(k):
                return i
    return None


# --------------------------------------------------------------------------
# 4. PUENTE HACIA CINE PARA LA COHORTE 2018
# --------------------------------------------------------------------------
# El SNIES implementó la CINE-F 2013 A.C. a partir de la vigencia 2019, de modo
# que el archivo de graduados de 2018 solo trae Área de Conocimiento y NBC. El
# área CINE de esa cohorte se recupera en dos pasos: primero por código de
# programa, usando los archivos posteriores donde el mismo programa sí aparece
# clasificado; y para los programas que no reaparecen, por el NBC, asignando la
# categoría CINE mayoritaria de ese núcleo. Se registra qué vía se usó.
def construir_puente():
    por_programa, por_nbc = {}, defaultdict(Counter)
    for anio in (2019, 2020, 2021, 2022):
        (libro, hoja), _ = COHORTES[anio]
        idx, filas = leer(libro, hoja)
        c_prog = col(idx, 'código snies del programa')
        c_cine = col(idx, 'desc cine campo amplio', 'cine campo amplio')
        c_nbc = col(idx, 'núcleo básico del conocimiento (nbc)', 'nucleo basico')
        c_gr = col(idx, 'graduados')
        for r in filas:
            cine = sin_tildes(r[c_cine]).title()
            if not cine:
                continue
            por_programa.setdefault(codigo(r[c_prog]), cine)
            por_nbc[norm(r[c_nbc])][cine] += float(r[c_gr] or 0)
    nbc_a_cine = {k: v.most_common(1)[0][0] for k, v in por_nbc.items()}
    return por_programa, nbc_a_cine


# --------------------------------------------------------------------------
# 5. CONSTRUCCIÓN DE UNA COHORTE
# --------------------------------------------------------------------------
def cohorte(anio, puente_prog, puente_nbc):
    (libro, hoja), hoja_ibc = COHORTES[anio]
    idx, filas = leer(libro, hoja)
    c_prog = col(idx, 'código snies del programa')
    c_niv = col(idx, 'nivel académico')
    c_met = col(idx, 'metodología')
    c_cine = col(idx, 'desc cine campo amplio', 'cine campo amplio')
    c_nbc = col(idx, 'núcleo básico del conocimiento (nbc)', 'nucleo basico')
    c_gr = col(idx, 'graduados')
    c_acr = col(idx, 'programa acreditado')
    c_ies = col(idx, 'código de la institución')
    c_acr_ies = col(idx, 'ies acreditada')

    graduados, atributos = defaultdict(float), {}
    via = Counter()
    for r in filas:
        if norm(r[c_niv]) != 'pregrado':
            continue
        cod = codigo(r[c_prog])
        graduados[cod] += float(r[c_gr] or 0)
        if cod in atributos:
            continue
        if c_cine is not None and r[c_cine]:
            area, v = sin_tildes(r[c_cine]).title(), 'directa'
        elif cod in puente_prog:
            area, v = puente_prog[cod], 'por programa'
        else:
            area = puente_nbc.get(norm(r[c_nbc]), 'Sin Clasificacion')
            v = 'por nbc'
        via[v] += 1
        acr = str(r[c_acr]).strip().upper() if c_acr is not None else None
        acr_ies = str(r[c_acr_ies]).strip().upper() if c_acr_ies is not None else None
        traducir = {'S': 1, 'N': 0}
        atributos[cod] = {
            'modalidad': modalidad(r[c_met]),
            'area': area,
            'acreditado': traducir.get(acr),
            'ies_acreditada': traducir.get(acr_ies),
            'ies': codigo(r[c_ies]),
        }

    idx_i, filas_i = leer(LIBRO_IBC, hoja_ibc)
    i_prog = col(idx_i, 'código snies del programa')
    i_gr = col(idx_i, 'graduados')
    cotizantes, huerfanos = defaultdict(float), 0.0
    for r in filas_i:
        cod = codigo(r[i_prog])
        g = float(r[i_gr] or 0)
        if cod in graduados:
            cotizantes[cod] += g
        else:
            huerfanos += g
    return graduados, atributos, cotizantes, huerfanos, via


# --------------------------------------------------------------------------
# 6. SEMÁFORO
# --------------------------------------------------------------------------
# Dos dimensiones, porque el policy paper pregunta dos cosas distintas:
#   (a) desempeño: ¿los egresados virtuales del área se vinculan formalmente
#       peor que los presenciales, y de manera sostenida?
#   (b) cobertura: ¿existe siquiera oferta virtual acreditada en el área, es
#       decir, está disponible el instrumento de política?
UMBRAL = 5.0          # puntos porcentuales
MIN_GRADUADOS = 100   # celdas más pequeñas no se clasifican


def clasificar(brechas):
    """brechas: lista de (cohorte, brecha en pp) con datos suficientes.

    Rojo: el promedio desfavorece a la virtualidad y el signo negativo se repite
    en casi todas las cohortes, de modo que se trata de un rezago sostenido y no
    del resultado de un año atípico.
    Verde: el promedio favorece a la virtualidad en al menos el umbral y el signo
    positivo se mantiene.
    Amarillo: diferencias por debajo del umbral o de signo inestable.
    """
    if len(brechas) < 3:
        return 'Sin datos suficientes'
    valores = [b for _, b in brechas]
    negativos = sum(1 for b in valores if b < 0)
    promedio = sum(valores) / len(valores)
    if promedio < 0 and negativos >= len(valores) - 1:
        return 'Rojo'
    if promedio >= UMBRAL and negativos <= 1:
        return 'Verde'
    return 'Amarillo'


# --------------------------------------------------------------------------
# 7. EJECUCIÓN
# --------------------------------------------------------------------------
def main():
    puente_prog, puente_nbc = construir_puente()

    celdas = defaultdict(lambda: [0.0, 0.0, 0])   # (anio, mod, area)
    filas_programa = []
    control = []

    for anio in sorted(COHORTES):
        graduados, atributos, cotizantes, huerfanos, via = cohorte(
            anio, puente_prog, puente_nbc)
        tg = tc = 0.0
        for cod, g in graduados.items():
            a = atributos[cod]
            c = cotizantes.get(cod, 0.0)
            celdas[(anio, a['modalidad'], a['area'])][0] += g
            celdas[(anio, a['modalidad'], a['area'])][1] += c
            celdas[(anio, a['modalidad'], a['area'])][2] += 1
            tg += g
            tc += c
            if a['modalidad'] in ('Virtual', 'Presencial'):
                filas_programa.append({
                    'cohorte': anio, 'seguimiento': anio + 1,
                    'codigo_programa': cod, 'codigo_ies': a['ies'],
                    'area': a['area'], 'modalidad': a['modalidad'],
                    'virtual': 1 if a['modalidad'] == 'Virtual' else 0,
                    'acreditado': a['acreditado'],
                    'ies_acreditada': a['ies_acreditada'],
                    'graduados': int(g), 'cotizantes': int(c),
                    'tasa': round(c / g, 6) if g else '',
                })
        control.append({
            'cohorte': anio, 'ano_corte': anio + 1,
            'graduados': int(tg), 'cotizantes': int(tc),
            'cotizantes_sin_programa': int(huerfanos),
            'programas': len(graduados),
            'area_directa': via['directa'], 'area_por_programa': via['por programa'],
            'area_por_nbc': via['por nbc'],
        })

    # ---- panel de celdas ----
    with open(DATOS / 'panel_celda.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['cohorte', 'seguimiento', 'area', 'modalidad', 'virtual',
                    'programas', 'graduados', 'cotizantes', 'tasa'])
        for (anio, mod, area), (g, c, n) in sorted(celdas.items()):
            if mod == 'Excluida':
                continue
            w.writerow([anio, anio + 1, area, mod, 1 if mod == 'Virtual' else 0,
                        n, int(g), int(c), round(c / g, 6) if g else ''])

    # ---- panel de programas ----
    with open(DATOS / 'panel_programa.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(filas_programa[0]))
        w.writeheader()
        w.writerows(filas_programa)

    # ---- semáforo ----
    areas = sorted({a for (_, m, a) in celdas if m == 'Presencial'})
    semaforo = []
    for area in areas:
        brechas = []
        for anio in sorted(COHORTES):
            gp, cp, _ = celdas.get((anio, 'Presencial', area), [0, 0, 0])
            gv, cv, _ = celdas.get((anio, 'Virtual', area), [0, 0, 0])
            if gp >= MIN_GRADUADOS and gv >= MIN_GRADUADOS:
                brechas.append((anio, 100 * (cv / gv - cp / gp)))
        # cobertura de acreditación en la oferta virtual (cohortes 2021-2022)
        acred = sum(1 for r in filas_programa
                    if r['area'] == area and r['virtual'] == 1
                    and r['acreditado'] == 1 and r['cohorte'] == 2022)
        virt = sum(1 for r in filas_programa
                   if r['area'] == area and r['virtual'] == 1
                   and r['acreditado'] is not None and r['cohorte'] == 2022)
        semaforo.append({
            'area': area,
            'cohortes_con_dato': len(brechas),
            'brecha_promedio_pp': round(sum(b for _, b in brechas) / len(brechas), 1)
            if brechas else '',
            'brecha_ultima_pp': round(brechas[-1][1], 1) if brechas else '',
            'clasificacion': clasificar(brechas),
            'programas_virtuales': virt,
            'virtuales_acreditados': acred,
            'cobertura_acreditacion': round(100 * acred / virt, 1) if virt else '',
        })
    with open(DATOS / 'semaforo.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(semaforo[0]))
        w.writeheader()
        w.writerows(semaforo)

    with open(DATOS / 'control_calidad.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(control[0]))
        w.writeheader()
        w.writerows(control)

    # ---- reporte en consola ----
    print('=== CONTROL DE CALIDAD ===')
    for c in control:
        print(f"  cohorte {c['cohorte']} -> corte {c['ano_corte']}: "
              f"{c['graduados']:>8,} graduados | {c['cotizantes']:>8,} cotizantes | "
              f"huérfanos {c['cotizantes_sin_programa']:>5,} | "
              f"área: {c['area_directa']} directa / {c['area_por_programa']} por programa "
              f"/ {c['area_por_nbc']} por nbc")
    print()
    print('=== BRECHA NACIONAL (Virtual − Presencial, pp) ===')
    for anio in sorted(COHORTES):
        r = {}
        for mod in ('Presencial', 'Virtual'):
            g = sum(v[0] for (y, m, _), v in celdas.items() if y == anio and m == mod)
            c = sum(v[1] for (y, m, _), v in celdas.items() if y == anio and m == mod)
            r[mod] = 100 * c / g
        print(f'  {anio}: presencial {r["Presencial"]:.1f}%  '
              f'virtual {r["Virtual"]:.1f}%  brecha {r["Virtual"]-r["Presencial"]:+.1f}')
    print()
    print('=== SEMÁFORO ===')
    for s in semaforo:
        print(f"  {s['clasificacion']:<22} {s['area'][:44]:<46} "
              f"brecha prom {str(s['brecha_promedio_pp']):>6} pp | "
              f"acreditación virtual {s['virtuales_acreditados']}/{s['programas_virtuales']}")


if __name__ == '__main__':
    main()
