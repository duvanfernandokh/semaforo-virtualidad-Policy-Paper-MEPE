# -*- coding: utf-8 -*-
"""
EL SEMÁFORO DE LA VIRTUALIDAD — estimación
===========================================
Corre sobre los archivos que produce pipeline.py.

M1  brecha media condicionada a campo y cohorte (nivel celda)
M2  brecha por campo de conocimiento: el semáforo con inferencia (nivel celda)
M3  acreditación e interacción con virtualidad (nivel programa, 2021-2022)
M4  robustez: GLM binomial, porque la dependiente es una proporción de conteos
M5  robustez: exclusión de las cohortes afectadas por la pandemia

La variable dependiente es la tasa de cotización dependiente: cotizantes
dependientes del año de corte t+1 sobre graduados de la cohorte t. Todas las
regresiones se ponderan por el número de graduados de la celda o del programa,
porque cada observación resume poblaciones de tamaño muy distinto.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from pathlib import Path

DATOS = Path(__file__).resolve().parent / 'datos'
SALIDAS = Path(__file__).resolve().parent / 'salidas'
SALIDAS.mkdir(exist_ok=True)


pd.set_option('display.width', 160)
MIN_GRAD = 10          # programas con menos graduados producen tasas demasiado ruidosas


def titulo(t):
    print('\n' + '=' * 78)
    print(t)
    print('=' * 78)


def tabla(res, terminos=None):
    """Imprime coeficiente, error estándar e intervalo de los términos pedidos."""
    ic = res.conf_int()
    filas = []
    for nombre in (terminos or res.params.index):
        if nombre not in res.params.index:
            continue
        filas.append({
            'término': nombre,
            'coef. (pp)': 100 * res.params[nombre],
            'e.e. (pp)': 100 * res.bse[nombre],
            'p': res.pvalues[nombre],
            'IC95 inf': 100 * ic.loc[nombre, 0],
            'IC95 sup': 100 * ic.loc[nombre, 1],
        })
    print(pd.DataFrame(filas).to_string(index=False, float_format=lambda x: f'{x:8.3f}'))


# --------------------------------------------------------------------------
celda = pd.read_csv(DATOS / 'panel_celda.csv')
programa = pd.read_csv(DATOS / 'panel_programa.csv')

celda['area'] = celda['area'].astype('category')
celda['cohorte_f'] = celda['cohorte'].astype('category')

titulo('DESCRIPTIVO — brecha nacional por cohorte')
desc = (celda.groupby(['cohorte', 'modalidad'])[['graduados', 'cotizantes']].sum()
        .assign(tasa=lambda d: 100 * d.cotizantes / d.graduados)
        .reset_index().pivot(index='cohorte', columns='modalidad', values='tasa'))
desc['brecha_pp'] = desc['Virtual'] - desc['Presencial']
print(desc.to_string(float_format=lambda x: f'{x:7.2f}'))

# --------------------------------------------------------------------------
titulo('M1 — Brecha media, efectos fijos de campo y cohorte (nivel celda)')
m1 = smf.wls('tasa ~ virtual + C(area) + C(cohorte)', data=celda,
             weights=celda['graduados']).fit(cov_type='HC1')
tabla(m1, ['virtual'])
print(f'\nN = {int(m1.nobs)}   R² ajustado = {m1.rsquared_adj:.3f}')
print('Lectura: diferencia en puntos porcentuales entre la tasa de vinculación de los\n'
      'egresados virtuales y la de los presenciales, una vez descontadas las diferencias\n'
      'de composición por campo de conocimiento y por año.')

# --------------------------------------------------------------------------
titulo('M2 — Brecha por campo de conocimiento: el semáforo con inferencia')
m2 = smf.wls('tasa ~ virtual * C(area) + C(cohorte)', data=celda,
             weights=celda['graduados']).fit(cov_type='HC1')
base = sorted(celda['area'].unique())[0]
filas = []
for area in sorted(celda['area'].unique()):
    if area == base:
        coef, se = m2.params['virtual'], m2.bse['virtual']
    else:
        t = f'virtual:C(area)[T.{area}]'
        if t not in m2.params.index:
            continue
        # efecto del área = término base + interacción; el error se obtiene
        # con una combinación lineal para respetar la covarianza entre ambos
        c = np.zeros(len(m2.params))
        c[list(m2.params.index).index('virtual')] = 1
        c[list(m2.params.index).index(t)] = 1
        coef = float(c @ m2.params)
        se = float(np.sqrt(c @ m2.cov_params() @ c))
    filas.append({'área': area[:44], 'brecha (pp)': 100 * coef, 'e.e.': 100 * se,
                  'IC95 inf': 100 * (coef - 1.96 * se), 'IC95 sup': 100 * (coef + 1.96 * se),
                  'semáforo': 'Rojo' if coef + 1.96 * se < 0 else
                              'Verde' if (coef - 1.96 * se > 0 and coef >= 0.05)
                              else 'Amarillo'})
print(pd.DataFrame(filas).to_string(index=False, float_format=lambda x: f'{x:8.2f}'))
print('\nRojo: el intervalo de confianza queda enteramente por debajo de cero, de modo que\n'
      'hay rezago estadísticamente distinguible. Verde: el intervalo queda enteramente por\n'
      'encima de cero y la ventaja estimada alcanza al menos cinco puntos porcentuales.\n'
      'Amarillo: el resto, sea por diferencia pequeña o por imprecisión de la estimación.')

# --------------------------------------------------------------------------
titulo('M3 — Acreditación y virtualidad (nivel programa, cohortes 2021 y 2022)')
pr = programa.dropna(subset=['acreditado']).query('graduados >= @MIN_GRAD').copy()
pr['acreditado'] = pr['acreditado'].astype(int)
print(f'Programas en la estimación: {len(pr):,}')
print(pr.groupby(['modalidad', 'acreditado']).size().rename('programas').to_string())
m3 = smf.wls('tasa ~ virtual * acreditado + C(area) + C(cohorte)', data=pr,
             weights=pr['graduados']).fit(cov_type='cluster',
                                          cov_kwds={'groups': pr['codigo_ies']})
tabla(m3, ['virtual', 'acreditado', 'virtual:acreditado'])
print(f'\nN = {int(m3.nobs)}   conglomerados (IES) = {pr["codigo_ies"].nunique()}')
n_va = pr.query('virtual == 1 and acreditado == 1').shape[0]
print(f'\nADVERTENCIA: la interacción se identifica con solo {n_va} programas virtuales\n'
      'acreditados. El intervalo de confianza es amplio por construcción y el coeficiente\n'
      'no debe leerse como evidencia concluyente en ningún sentido.')

# --------------------------------------------------------------------------
titulo('M4 — Robustez: GLM binomial con enlace logit (nivel celda)')
m4 = smf.glm('cotizantes + I(graduados - cotizantes) ~ virtual + C(area) + C(cohorte)',
             data=celda, family=sm.families.Binomial()).fit(cov_type='HC1')
print(f"virtual: coeficiente logit {m4.params['virtual']:.4f} "
      f"(e.e. {m4.bse['virtual']:.4f}), razón de momios "
      f"{np.exp(m4.params['virtual']):.3f}, p = {m4.pvalues['virtual']:.3g}")
p0 = celda.loc[celda.virtual == 0, 'cotizantes'].sum() / celda.loc[celda.virtual == 0, 'graduados'].sum()
odds = p0 / (1 - p0) * np.exp(m4.params['virtual'])
print(f'Efecto en la escala de la tasa, evaluado en la media presencial '
      f'({100*p0:.1f} %): {100*(odds/(1+odds) - p0):+.1f} pp')

# --------------------------------------------------------------------------
titulo('M5 — Robustez: sin las cohortes con seguimiento en pandemia (2019 y 2020)')
sub = celda.query('cohorte not in [2019, 2020]')
m5 = smf.wls('tasa ~ virtual + C(area) + C(cohorte)', data=sub,
             weights=sub['graduados']).fit(cov_type='HC1')
tabla(m5, ['virtual'])
print(f'N = {int(m5.nobs)}  (cohortes {sorted(sub.cohorte.unique())})')

# --------------------------------------------------------------------------
titulo('M6 — Asimetría en la cobertura del instrumento de acreditación')
cob = (programa.query('cohorte == 2022').dropna(subset=['acreditado'])
       .groupby('modalidad')['acreditado'].agg(['size', 'sum']))
cob.columns = ['programas', 'acreditados']
cob['cobertura_%'] = 100 * cob.acreditados / cob.programas
print(cob.to_string(float_format=lambda x: f'{x:7.1f}'))
z = sm.stats.proportions_ztest(cob['acreditados'].values, cob['programas'].values)
print(f'\nPrueba de diferencia de proporciones: z = {z[0]:.2f}, p = {z[1]:.3g}')
print('Esta es la brecha que el policy paper puede documentar sin depender de ningún\n'
      'supuesto de identificación: el instrumento de política está disponible para una\n'
      'modalidad y prácticamente ausente en la otra.')
