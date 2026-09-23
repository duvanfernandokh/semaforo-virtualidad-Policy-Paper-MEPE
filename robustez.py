# -*- coding: utf-8 -*-
"""Verificaciones de robustez que el Anexo 1 anunciaba y no se habían corrido."""
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from pathlib import Path

DATOS = Path(__file__).resolve().parent / 'datos'
SALIDAS = Path(__file__).resolve().parent / 'salidas'
SALIDAS.mkdir(exist_ok=True)


celda = pd.read_csv(DATOS / 'panel_celda.csv')
programa = pd.read_csv(DATOS / 'panel_programa.csv')
rng = np.random.default_rng(20260922)


def linea(t):
    print('\n' + t)
    print('-' * len(t))


# R-a: errores agrupados por campo (10 conglomerados) frente a robustos
linea('R1. Agrupación de errores por campo de conocimiento')
base = smf.wls('tasa ~ virtual + C(area) + C(cohorte)', data=celda,
               weights=celda.graduados)
m_hc1 = base.fit(cov_type='HC1')
m_cl = base.fit(cov_type='cluster', cov_kwds={'groups': celda.area})
for nombre, m in (('robustos HC1', m_hc1), ('agrupados por campo', m_cl)):
    ic = m.conf_int().loc['virtual']
    print(f'  {nombre:<24} coef {100*m.params["virtual"]:.2f} pp | '
          f'ee {100*m.bse["virtual"]:.2f} | IC [{100*ic[0]:.2f}; {100*ic[1]:.2f}] | '
          f'p {m.pvalues["virtual"]:.4f}')
print(f'  conglomerados: {celda.area.nunique()}')

# bootstrap wild-cluster sobre el campo
linea('R1b. Bootstrap wild-cluster (Rademacher, 4.999 réplicas, agrupado por campo)')
y = celda.tasa.values
X = pd.get_dummies(celda[['area', 'cohorte']].astype(str), drop_first=True).astype(float)
X.insert(0, 'virtual', celda.virtual.values)
X = sm.add_constant(X)
w = celda.graduados.values
ajuste = sm.WLS(y, X, weights=w).fit()
res_r = sm.WLS(y, X.drop(columns='virtual'), weights=w).fit()   # hipótesis nula impuesta
u = res_r.resid
grupos = celda.area.values
t_obs = ajuste.params['virtual'] / ajuste.bse['virtual']
t_boot = []
for _ in range(4999):
    signos = {g: rng.choice([-1.0, 1.0]) for g in np.unique(grupos)}
    s = np.array([signos[g] for g in grupos])
    y_b = res_r.fittedvalues + u * s
    a_b = sm.WLS(y_b, X, weights=w).fit()
    t_boot.append(a_b.params['virtual'] / a_b.bse['virtual'])
p_boot = float(np.mean(np.abs(np.array(t_boot)) >= abs(t_obs)))
print(f'  estadístico t observado: {t_obs:.2f}')
print(f'  valor p por bootstrap wild-cluster: {p_boot:.4f}')

# R5: ponderación
linea('R5. Ponderación alternativa')
m_sin = smf.ols('tasa ~ virtual + C(area) + C(cohorte)', data=celda).fit(cov_type='HC1')
print(f'  ponderada por graduados  {100*m_hc1.params["virtual"]:.2f} pp '
      f'(ee {100*m_hc1.bse["virtual"]:.2f})')
print(f'  sin ponderar             {100*m_sin.params["virtual"]:.2f} pp '
      f'(ee {100*m_sin.bse["virtual"]:.2f})')
print(f'  diferencia: {abs(100*(m_hc1.params["virtual"]-m_sin.params["virtual"])):.2f} pp')

# R6: placebo por reasignación aleatoria de la modalidad
linea('R6. Prueba placebo (1.000 reasignaciones aleatorias de la modalidad)')
coefs = []
d = celda.copy()
for _ in range(1000):
    d['falso'] = rng.permutation(d.virtual.values)
    mm = smf.wls('tasa ~ falso + C(area) + C(cohorte)', data=d, weights=d.graduados).fit()
    coefs.append(100 * mm.params['falso'])
coefs = np.array(coefs)
real = 100 * m_hc1.params['virtual']
print(f'  coeficiente real: {real:.2f} pp')
print(f'  placebo: media {coefs.mean():.2f} | desv. {coefs.std():.2f} | '
      f'percentil 97,5 {np.percentile(coefs, 97.5):.2f}')
print(f'  proporción de placebos que igualan o superan el real: '
      f'{float(np.mean(coefs >= real)):.4f}')

# R8: sensibilidad al umbral mínimo de graduados en el panel de programas
linea('R8. Sensibilidad al umbral mínimo de graduados por programa')
pr = programa.dropna(subset=['acreditado']).copy()
pr['acreditado'] = pr.acreditado.astype(int)
for umbral in (0, 5, 10, 20, 50):
    s = pr[pr.graduados >= umbral]
    mm = smf.wls('tasa ~ virtual * acreditado + C(area) + C(cohorte)', data=s,
                 weights=s.graduados).fit(cov_type='cluster',
                                          cov_kwds={'groups': s.codigo_ies})
    ic = mm.conf_int().loc['virtual:acreditado']
    print(f'  umbral {umbral:>3}: N {len(s):>6,} | virtual {100*mm.params["virtual"]:>6.2f} pp'
          f' | interacción {100*mm.params["virtual:acreditado"]:>7.2f} pp '
          f'[{100*ic[0]:.2f}; {100*ic[1]:.2f}]')
