# -*- coding: utf-8 -*-
"""
EL SEMÁFORO DE LA VIRTUALIDAD — tablero interactivo
===================================================
Implementa la especificación del Anexo 7 del policy paper.

Arquitectura en tres capas:
  datos          panel_celda.csv y panel_programa.csv, leídos y validados al iniciar
  modelo         coeficientes y clasificación precalculados en COEFICIENTES y
                 SEMAFORO; no se reestima nada en tiempo de ejecución, para que
                 las cifras coincidan necesariamente con las de los anexos 1 y 4
  presentación   una banda de encabezado, cuatro indicadores de cabecera, tres
                 controles en la barra lateral y cuatro vistas

Ejecución local:
    pip install -r requirements.txt
    streamlit run tablero.py

Publicación: cualquier servicio de aplicaciones analíticas que ejecute
Streamlit. La dirección resultante se consigna en el Anexo 7.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATOS = Path(__file__).parent / 'datos'

# --------------------------------------------------------------------------
# PALETA
# Categóricas: ranuras 1 y 2 de la paleta validada (ΔE con visión normal 33,6;
# ΔE con deuteranopía 24,7, ambos por encima del piso exigido).
# Estado: paleta reservada de estado. Nunca comunica sola: cada marca lleva
# además una forma propia y un rótulo de texto.
# --------------------------------------------------------------------------
AZUL = '#2a78d6'          # presencial
NARANJA = '#eb6834'       # virtual
TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
TINTA_3 = '#898781'
REJILLA = '#e1e0d9'
BASE = '#c3c2b7'
LIENZO = '#ffffff'

ESTADO = {'Verde': '#0ca30c', 'Amarillo': '#fab219', 'Rojo': '#d03b3b',
          'Sin datos suficientes': '#898781'}
ESTADO_SUAVE = {'Verde': '#eaf6ea', 'Amarillo': '#fdf4e0', 'Rojo': '#fbecec',
                'Sin datos suficientes': '#f2f2ef'}
FORMA = {'Verde': 'circle', 'Amarillo': 'diamond', 'Rojo': 'square',
         'Sin datos suficientes': 'circle-open'}
GLIFO = {'Verde': '●', 'Amarillo': '◆', 'Rojo': '■', 'Sin datos suficientes': '○'}

TIPOGRAFIA = 'system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif'
VERSION_PANEL = 'Cohortes 2018-2022 · seguimiento laboral 2019-2023'

# --------------------------------------------------------------------------
# CAPA DE MODELO — resultados precalculados (anexos 1 y 4)
# --------------------------------------------------------------------------
COEFICIENTES = {
    'brecha_media': {'coef': 7.13, 'ee': 0.95, 'ic': (5.26, 9.00), 'n': 99},
    'interaccion': {'coef': -3.41, 'ee': 3.49, 'ic': (-10.24, 3.42), 'n': 9194,
                    'programas_identificantes': 30},
    'rango_observado_acreditacion': (0.0, 8.0),
    'cobertura': {'virtual': 4.5, 'presencial': 24.7, 'z': 8.49},
}

SEMAFORO = {
    'Servicios': (26.44, 18.66, 34.23, 'Verde'),
    'Educacion': (11.91, 7.76, 16.05, 'Verde'),
    'Administracion De Empresas Y Derecho': (8.79, 6.98, 10.60, 'Verde'),
    'Ingenieria, Industria Y Construccion': (5.91, 3.89, 7.93, 'Verde'),
    'Salud Y Bienestar': (3.53, 1.10, 5.96, 'Amarillo'),
    'Ciencias Naturales, Matematicas Y Estadistica': (2.30, -2.19, 6.79, 'Amarillo'),
    'Ciencias Sociales, Periodismo E Informacion': (2.22, -5.49, 9.94, 'Amarillo'),
    'Arte Y Humanidades': (-0.67, -7.44, 6.10, 'Amarillo'),
    'Agropecuario, Silvicultura, Pesca Y Veterinaria': (-0.97, -6.85, 4.91, 'Amarillo'),
    'Tecnologias De La Informacion Y La Comunicacion (Tic)': (-5.25, -8.30, -2.19, 'Rojo'),
}

# Rótulos cortos y acentuados para ejes y tarjetas. Las claves del panel vienen
# del SNIES sin tildes y en mayúscula inicial; mostrarlas así resulta ilegible.
CORTO = {
    'Administracion De Empresas Y Derecho': 'Administración y Derecho',
    'Agropecuario, Silvicultura, Pesca Y Veterinaria': 'Agropecuario y Veterinaria',
    'Arte Y Humanidades': 'Arte y Humanidades',
    'Ciencias Naturales, Matematicas Y Estadistica': 'Ciencias Naturales',
    'Ciencias Sociales, Periodismo E Informacion': 'Ciencias Sociales',
    'Educacion': 'Educación',
    'Ingenieria, Industria Y Construccion': 'Ingeniería e Industria',
    'Salud Y Bienestar': 'Salud y Bienestar',
    'Servicios': 'Servicios',
    'Tecnologias De La Informacion Y La Comunicacion (Tic)': 'TIC',
}


def corto(area):
    return CORTO.get(area, area)


def num(x, dec=1, signo=False):
    """Formato colombiano: coma decimal, punto de miles."""
    if x is None or pd.isna(x):
        return '—'
    s = f'{x:,.{dec}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')
    if signo and x > 0:
        s = '+' + s
    return s


# --------------------------------------------------------------------------
# CAPA DE DATOS
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cargar():
    celda = pd.read_csv(DATOS / 'panel_celda.csv')
    programa = pd.read_csv(DATOS / 'panel_programa.csv')
    calidad = {}
    for nombre, df in (('celdas', celda), ('programas', programa)):
        df['tasa'] = pd.to_numeric(df['tasa'], errors='coerce')
        fuera = int((~df['tasa'].dropna().between(0, 1)).sum())
        calidad[nombre] = (fuera, len(df))
    return celda, programa, calidad


def cobertura_virtual(programa, cohorte=2022):
    d = programa[(programa.cohorte == cohorte) & programa.acreditado.notna()]
    d = d[d.modalidad == 'Virtual']
    g = d.groupby('area')['acreditado'].agg(['size', 'sum'])
    g.columns = ['programas', 'acreditados']
    g['cobertura'] = 100 * g.acreditados / g.programas
    return g


# --------------------------------------------------------------------------
# CHROME DE LAS GRÁFICAS
# --------------------------------------------------------------------------
def lienzo(fig, titulo_x='', titulo_y='', alto=460, leyenda=True):
    fig.update_layout(
        plot_bgcolor=LIENZO, paper_bgcolor=LIENZO, height=alto,
        font=dict(family=TIPOGRAFIA, size=13, color=TINTA),
        margin=dict(l=8, r=8, t=46 if leyenda else 14, b=8),
        hoverlabel=dict(bgcolor='white', bordercolor=REJILLA,
                        font=dict(family=TIPOGRAFIA, size=13, color=TINTA)),
        showlegend=leyenda,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0,
                    font=dict(size=12, color=TINTA_2),
                    bgcolor='rgba(0,0,0,0)'),
        xaxis=dict(title=titulo_x, gridcolor=REJILLA, zeroline=False,
                   linecolor=BASE, ticks='outside', tickcolor=BASE, ticklen=4,
                   tickfont=dict(size=12, color=TINTA_3),
                   title_font=dict(size=12, color=TINTA_2)),
        yaxis=dict(title=titulo_y, gridcolor=REJILLA, zeroline=False,
                   linecolor=BASE, tickfont=dict(size=12, color=TINTA_3),
                   title_font=dict(size=12, color=TINTA_2)),
    )
    return fig


PLOTLY_CONF = {'displayModeBar': False, 'displaylogo': False,
               'scrollZoom': False, 'responsive': True}


# --------------------------------------------------------------------------
# CAPA DE PRESENTACIÓN
# --------------------------------------------------------------------------
st.set_page_config(page_title='El semáforo de la virtualidad',
                   page_icon='🚦', layout='wide',
                   initial_sidebar_state='expanded')

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }}
  #MainMenu, footer {{ visibility: hidden; }}
  header[data-testid="stHeader"] {{ background: transparent; }}

  /* Tipografía solo sobre texto. No usar [class*="st-"] ni "*": pisa la fuente
     de íconos de Streamlit y aparecen rótulos como "keyboard_double_arrow_left". */
  html, body, .stApp, .stMarkdown, p, label, li, h1, h2, h3, h4,
  [data-testid="stWidgetLabel"], [data-baseweb="tab"], [data-testid="stCaptionContainer"],
  [data-testid="stExpander"] summary p, button p {{ font-family: {TIPOGRAFIA}; }}
  [data-testid="stIconMaterial"], span[class*="material-symbols"],
  span[class*="material-icons"] {{
      font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                   "Material Icons" !important;
  }}
  /* barra superior de Streamlit: sin botón Deploy ni menú */
  [data-testid="stToolbar"], .stAppDeployButton, [data-testid="stAppDeployButton"],
  [data-testid="stDecoration"] {{ display: none !important; }}

  /* ---------- banda de encabezado ---------- */
  .banda {{
      background: linear-gradient(180deg, #f7f7f4 0%, #fdfdfc 100%);
      border: 1px solid rgba(11,11,11,0.09); border-radius: 14px;
      padding: 22px 26px 20px 26px; margin-bottom: 18px;
  }}
  .banda h1 {{
      font-size: 27px; line-height: 1.18; font-weight: 700; letter-spacing: -0.4px;
      color: {TINTA}; margin: 0 0 6px 0;
  }}
  .banda p {{ font-size: 14px; line-height: 1.55; color: {TINTA_2}; margin: 0; max-width: 78ch; }}
  .sello {{
      display: inline-block; margin-top: 12px; padding: 4px 11px; border-radius: 999px;
      background: #eef4fd; border: 1px solid rgba(42,120,214,0.24);
      font-size: 11.5px; font-weight: 600; color: #1c5cab; letter-spacing: 0.2px;
  }}

  /* ---------- tarjetas de indicador ---------- */
  .kpi {{
      background: #ffffff; border: 1px solid rgba(11,11,11,0.10); border-radius: 12px;
      padding: 15px 17px 14px 17px; height: 100%;
      box-shadow: 0 1px 2px rgba(11,11,11,0.035);
  }}
  .kpi .rotulo {{
      font-size: 10.5px; font-weight: 700; letter-spacing: 0.75px; text-transform: uppercase;
      color: {TINTA_3}; margin-bottom: 7px;
  }}
  .kpi .cifra {{
      font-size: 31px; font-weight: 700; line-height: 1; letter-spacing: -1px; color: {TINTA};
  }}
  .kpi .cifra small {{ font-size: 15px; font-weight: 600; letter-spacing: 0; color: {TINTA_2}; }}
  .kpi .pie {{ font-size: 12px; line-height: 1.45; color: {TINTA_2}; margin-top: 7px; }}

  /* ---------- tarjetas del semáforo ---------- */
  .tarjeta {{
      border: 1px solid rgba(11,11,11,0.10); border-left-width: 5px; border-radius: 10px;
      padding: 12px 14px 13px 13px; margin-bottom: 9px; background: #ffffff;
      min-height: 146px; display: flex; flex-direction: column;
  }}
  .tarjeta .campo {{
      font-size: 13.5px; font-weight: 650; color: {TINTA}; line-height: 1.25;
      margin-bottom: 5px; min-height: 2.5em;
  }}
  .tarjeta .valor {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; color: {TINTA}; }}
  .tarjeta .ficha-pie {{ margin-top: auto; padding-top: 9px; }}
  .tarjeta .ic {{ font-size: 11.5px; color: {TINTA_3}; margin-top: 2px;
                  font-variant-numeric: tabular-nums; }}
  .ficha {{
      display: inline-block; padding: 2px 9px; border-radius: 999px;
      font-size: 10.5px; font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase;
  }}

  /* ---------- carriles del semáforo ---------- */
  .carril {{ border: 1px solid rgba(11,11,11,0.09); border-top-width: 6px; border-radius: 12px;
             padding: 14px 16px 10px 16px; margin: 8px 0 6px 0; min-height: 250px; }}
  .carril-cab {{ display: flex; align-items: center; gap: 10px; }}
  .luz {{ width: 30px; height: 30px; border-radius: 50%; display: inline-flex;
          align-items: center; justify-content: center; color: #fff; font-size: 13px;
          box-shadow: 0 0 0 4px rgba(255,255,255,0.75); }}
  .carril-nombre {{ font-size: 15px; font-weight: 800; letter-spacing: 1px; color: {TINTA}; }}
  .carril-n {{ margin-left: auto; font-size: 12px; font-weight: 600; color: {TINTA_2};
               background: rgba(255,255,255,0.7); border-radius: 999px; padding: 2px 9px; }}
  .carril-sentido {{ font-size: 12.5px; color: {TINTA_2}; margin: 8px 0 8px 0; }}
  .renglon {{ display: flex; justify-content: space-between; gap: 10px; font-size: 14px;
              color: {TINTA}; padding: 7px 0; border-top: 1px solid rgba(11,11,11,0.07); }}
  .renglon b {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .renglon.vacio {{ color: {TINTA_3}; font-style: italic; }}

  /* ---------- pestañas ---------- */
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {REJILLA}; }}
  .stTabs [data-baseweb="tab"] {{
      height: 42px; padding: 0 16px; font-size: 14px; font-weight: 600; color: {TINTA_2};
  }}
  .stTabs [aria-selected="true"] {{ color: {AZUL}; }}

  /* ---------- barra lateral ---------- */
  section[data-testid="stSidebar"] {{ background: #f7f7f4; border-right: 1px solid {REJILLA}; }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}
  .rotulo-lat {{
      font-size: 10.5px; font-weight: 700; letter-spacing: 0.75px; text-transform: uppercase;
      color: {TINTA_3}; margin: 0 0 14px 0;
  }}

  .nota {{
      font-size: 12.5px; line-height: 1.6; color: {TINTA_2};
      border-left: 3px solid {REJILLA}; padding: 2px 0 2px 13px; margin: 14px 0 4px 0;
      max-width: 88ch;
  }}
  .titulo-vista {{
      font-size: 17px; font-weight: 700; color: {TINTA}; letter-spacing: -0.2px;
      margin: 14px 0 2px 0;
  }}
  .sub-vista {{ font-size: 13px; color: {TINTA_2}; margin: 0 0 10px 0; max-width: 84ch; }}
</style>
""", unsafe_allow_html=True)

celda, programa, calidad = cargar()

# ---- banda de encabezado ----
st.markdown(f"""
<div class="banda">
  <h1>El semáforo de la virtualidad</h1>
  <p>Vinculación laboral formal de los egresados de pregrado virtual en Colombia,
     por campo de conocimiento. Construido con registros administrativos del SNIES
     y del Observatorio Laboral para la Educación. La medida es la tasa de cotización
     dependiente: cotizantes dependientes en el año de corte sobre graduados de la
     cohorte del año anterior.</p>
  <span class="sello">{VERSION_PANEL}</span>
</div>
""", unsafe_allow_html=True)

# ---- controles, en la barra lateral, actuando sobre todas las vistas ----
cohortes = sorted(celda.cohorte.unique())
campos = sorted(celda.area.unique())

with st.sidebar:
    st.markdown('<div class="rotulo-lat">Filtros</div>', unsafe_allow_html=True)

    desde, hasta = st.select_slider(
        'Cohorte de graduación', options=cohortes,
        value=(cohortes[0], cohortes[-1]),
        help='Año de grado. El seguimiento laboral ocurre un año después.')
    sel_cohortes = [c for c in cohortes if desde <= c <= hasta]

    sel_mod = st.pills('Modalidad', ['Presencial', 'Virtual'],
                       selection_mode='multi', default=['Presencial', 'Virtual'])

    n_marcados = sum(1 for a in campos if st.session_state.get(f'campo_{a}', True))
    with st.expander(f'Campo de conocimiento · {n_marcados} de {len(campos)}',
                     expanded=False):
        marcados = []
        for a in campos:
            if st.checkbox(corto(a), value=True, key=f'campo_{a}'):
                marcados.append(a)
        sel_campos = marcados
    st.divider()
    st.caption('Los filtros afectan las vistas descriptivas. El semáforo y los '
               'coeficientes provienen de los anexos 1 y 4 del policy paper y no se '
               'reestiman aquí: al filtrar campos, la vista muestra un subconjunto '
               'de los mismos resultados, nunca una nueva estimación.')
    with st.expander('Control de calidad del panel'):
        f_cel, n_cel = calidad['celdas']
        f_pro, n_pro = calidad['programas']
        st.caption(
            f'Celdas: {num(n_cel, 0)} observaciones, {f_cel} con tasa fuera de [0, 1].\n\n'
            f'Programas: {num(n_pro, 0)} observaciones, {f_pro} con tasa fuera de '
            f'[0, 1] ({num(100 * f_pro / n_pro, 2)} %).\n\n'
            'Las tasas superiores a uno corresponden a programas con muy pocos '
            'graduados en la cohorte cuyo registro de cotizantes incluye egresados de '
            'promociones anteriores. Quedan documentadas en el anexo 2 y no entran en '
            'las estimaciones, que se hacen a nivel de celda y ponderadas por '
            'graduados.')

if not sel_cohortes or not sel_mod or not sel_campos:
    st.info('Seleccione al menos una cohorte, una modalidad y un campo de conocimiento '
            'en la barra lateral.')
    st.stop()

f = celda[celda.cohorte.isin(sel_cohortes) & celda.modalidad.isin(sel_mod)
          & celda.area.isin(sel_campos)]

# ---- fila de indicadores ----
vistos = [a for a in sel_campos if a in SEMAFORO]
conteo = {c: sum(1 for a in vistos if SEMAFORO[a][3] == c)
          for c in ('Verde', 'Amarillo', 'Rojo')}
bm = COEFICIENTES['brecha_media']
cb = COEFICIENTES['cobertura']
graduados = int(f.graduados.sum())

k1, k2, k3, k4 = st.columns(4, gap='small')
with k1:
    st.markdown(f"""
    <div class="kpi">
      <div class="rotulo">Brecha media nacional</div>
      <div class="cifra">{num(bm['coef'], 2, signo=True)} <small>pp</small></div>
      <div class="pie">A favor de la modalidad virtual, descontando campo y cohorte.
        Intervalo de confianza del 95&nbsp;%: {num(bm['ic'][0], 2)} a {num(bm['ic'][1], 2)}.</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi">
      <div class="rotulo">Semáforo por campo</div>
      <div class="cifra">
        <span style="color:{ESTADO['Verde']}">{conteo['Verde']}</span><small
          style="color:{TINTA_3}"> / </small><span
          style="color:{ESTADO['Amarillo']}">{conteo['Amarillo']}</span><small
          style="color:{TINTA_3}"> / </small><span
          style="color:{ESTADO['Rojo']}">{conteo['Rojo']}</span>
      </div>
      <div class="pie">Campos en verde, amarillo y rojo, de {len(vistos)} evaluados.
        El único rezago verificado está en TIC.</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi">
      <div class="rotulo">Cobertura de la acreditación</div>
      <div class="cifra" style="color:{NARANJA}">{num(cb['virtual'])} <small
         style="color:{TINTA_2}">% virtual</small></div>
      <div class="pie">Frente a {num(cb['presencial'])}&nbsp;% de los programas
        presenciales con graduados. Diferencia de proporciones z&nbsp;=&nbsp;{num(cb['z'], 2)}.</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class="kpi">
      <div class="rotulo">Egresados en el filtro</div>
      <div class="cifra">{num(graduados, 0)}</div>
      <div class="pie">Graduados cubiertos por la selección actual, en
        {len(sel_cohortes)} cohorte(s) y {len(sel_campos)} campo(s).</div>
    </div>""", unsafe_allow_html=True)

st.write('')

v1, v2, v3, v4 = st.tabs(['Semáforo', 'Evolución', 'Brecha y cobertura', 'Incertidumbre'])

# ==========================================================================
# VISTA 1 — el semáforo
# ==========================================================================
with v1:
    filas = sorted([(a, *SEMAFORO[a]) for a in vistos], key=lambda x: x[1])

    # ---- el semáforo propiamente dicho: tres carriles, visibles sin desplazarse ----
    SENTIDO = {'Rojo': 'Rezago verificado de la modalidad virtual',
               'Amarillo': 'Diferencia pequeña o no distinguible de cero',
               'Verde': 'Ventaja virtual verificada de 5 pp o más'}
    carriles = st.columns(3, gap='medium')
    for col, cat in zip(carriles, ('Rojo', 'Amarillo', 'Verde')):
        sub = sorted([x for x in filas if x[4] == cat], key=lambda x: x[1])
        renglones = ''.join(
            f'<div class="renglon"><span>{corto(a)}</span>'
            f'<b>{num(b, 1, signo=True)} pp</b></div>'
            for a, b, lo, hi, c in sub) or '<div class="renglon vacio">Ningún campo con los filtros actuales</div>'
        with col:
            st.markdown(f"""
            <div class="carril" style="border-top-color:{ESTADO[cat]};background:{ESTADO_SUAVE[cat]}">
              <div class="carril-cab">
                <span class="luz" style="background:{ESTADO[cat]}">{GLIFO[cat]}</span>
                <span class="carril-nombre">{cat.upper()}</span>
                <span class="carril-n">{len(sub)} campo{'s' if len(sub) != 1 else ''}</span>
              </div>
              <div class="carril-sentido">{SENTIDO[cat]}</div>
              {renglones}
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="titulo-vista">Brecha de vinculación formal por campo '
                'de conocimiento</div>'
                '<div class="sub-vista">Cada punto es la diferencia entre la tasa de '
                'los egresados virtuales y la de los presenciales del mismo campo. La '
                'barra es el intervalo de confianza del 95&nbsp;%.</div>',
                unsafe_allow_html=True)

    fig = go.Figure()
    # franja de referencia para el cero
    fig.add_vrect(x0=-1.0e-9, x1=1.0e-9, line_width=0)
    for cat in ('Rojo', 'Amarillo', 'Verde'):
        sub = [x for x in filas if x[4] == cat]
        if not sub:
            continue
        fig.add_trace(go.Scatter(
            x=[x[1] for x in sub], y=[corto(x[0]) for x in sub],
            error_x=dict(type='data', symmetric=False,
                         array=[x[3] - x[1] for x in sub],
                         arrayminus=[x[1] - x[2] for x in sub],
                         color=ESTADO[cat], thickness=2, width=7),
            mode='markers',
            marker=dict(size=13, color=ESTADO[cat], symbol=FORMA[cat],
                        line=dict(width=2, color='white')),
            name=cat,
            customdata=[[x[2], x[3]] for x in sub],
            hovertemplate='<b>%{y}</b><br>Brecha %{x:.2f} pp<br>'
                          'IC 95 %: %{customdata[0]:.2f} a %{customdata[1]:.2f}'
                          '<extra></extra>'))
    # rótulos directos del valor, fuera del extremo superior del intervalo
    der = [x for x in filas if x[3] >= 0]
    izq = [x for x in filas if x[3] < 0]
    for grupo, pos, dx, lado in ((der, 'middle right', 1.2, 3), (izq, 'middle left', -1.2, 2)):
        if grupo:
            fig.add_trace(go.Scatter(
                x=[x[lado] + dx for x in grupo], y=[corto(x[0]) for x in grupo],
                mode='text', text=[f'<b>{num(x[1], 1, signo=True)}</b>' for x in grupo],
                textposition=pos, textfont=dict(size=12.5, color=TINTA),
                showlegend=False, hoverinfo='skip'))
    fig.add_vline(x=0, line_dash='dot', line_color=TINTA_3, line_width=1.5)
    lienzo(fig, 'Diferencia en la tasa de cotización dependiente (puntos porcentuales)',
           alto=max(340, 62 * len(filas)))
    fig.update_xaxes(range=[-15, 40], zeroline=False)
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)', linecolor='rgba(0,0,0,0)', ticks='')
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONF)

    st.markdown('<div class="nota"><b>Regla de clasificación.</b> Rojo cuando el intervalo '
                'de confianza queda enteramente por debajo de cero, de modo que hay rezago '
                'estadísticamente distinguible. Verde cuando queda enteramente por encima '
                'y la ventaja estimada alcanza al menos cinco puntos porcentuales. Amarillo '
                'en los demás casos, sea por diferencia pequeña o por imprecisión de la '
                'estimación. El color nunca comunica solo: cada punto lleva además una forma '
                'propia y cada carril, un rótulo.</div>', unsafe_allow_html=True)

    with st.expander('Ver como tabla'):
        st.dataframe(
            pd.DataFrame([(corto(a), b, lo, hi, c) for a, b, lo, hi, c in filas],
                         columns=['Campo', 'Brecha (pp)', 'IC 95 % inferior',
                                  'IC 95 % superior', 'Semáforo']),
            hide_index=True, width='stretch',
            column_config={
                'Brecha (pp)': st.column_config.NumberColumn(format='%.2f'),
                'IC 95 % inferior': st.column_config.NumberColumn(format='%.2f'),
                'IC 95 % superior': st.column_config.NumberColumn(format='%.2f')})

# ==========================================================================
# VISTA 2 — evolución por modalidad
# ==========================================================================
with v2:
    ev = (f.groupby(['cohorte', 'modalidad'])[['graduados', 'cotizantes']].sum()
          .assign(tasa=lambda d: 100 * d.cotizantes / d.graduados).reset_index())

    st.markdown('<div class="titulo-vista">Tasa de cotización dependiente por cohorte '
                'y modalidad</div>'
                '<div class="sub-vista">La franja sombreada entre las dos líneas es la '
                'brecha observada en cada cohorte, antes de cualquier control por '
                'composición.</div>', unsafe_allow_html=True)

    fig = go.Figure()
    series = {}
    for mod in ('Presencial', 'Virtual'):
        s = ev[ev.modalidad == mod].sort_values('cohorte')
        if not s.empty:
            series[mod] = s
    # la franja se dibuja primero, en tinta neutra, para no competir con las series
    if len(series) == 2:
        p, v = series['Presencial'], series['Virtual']
        fig.add_trace(go.Scatter(x=p.cohorte, y=p.tasa, mode='lines',
                                 line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=v.cohorte, y=v.tasa, mode='lines', fill='tonexty',
                                 fillcolor='rgba(11,11,11,0.055)', line=dict(width=0),
                                 name='Brecha', showlegend=False, hoverinfo='skip'))
    for mod, color in (('Presencial', AZUL), ('Virtual', NARANJA)):
        if mod not in series:
            continue
        s = series[mod]
        fig.add_trace(go.Scatter(
            x=s.cohorte, y=s.tasa, name=mod, mode='lines+markers',
            line=dict(color=color, width=2.5),
            marker=dict(size=9, color=color, line=dict(width=2, color='white')),
            hovertemplate='Cohorte %{x}<br>' + mod + ': %{y:.1f} %<extra></extra>'))
        # rótulo directo al final de la línea
        fig.add_trace(go.Scatter(
            x=[s.cohorte.iloc[-1]], y=[s.tasa.iloc[-1]], mode='text',
            text=[f'  {mod} {num(s.tasa.iloc[-1])} %'], textposition='middle right',
            textfont=dict(size=12.5, color=color), showlegend=False, hoverinfo='skip'))
    lienzo(fig, 'Cohorte de graduación', 'Tasa de cotización dependiente (%)',
           alto=400, leyenda=False)
    fig.update_xaxes(tickmode='array', tickvals=sel_cohortes,
                     range=[min(sel_cohortes) - 0.25, max(sel_cohortes) + 1.15])
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONF)

    br = ev.pivot(index='cohorte', columns='modalidad', values='tasa')
    if {'Virtual', 'Presencial'} <= set(br.columns):
        br['brecha'] = br['Virtual'] - br['Presencial']
        st.markdown('<div class="titulo-vista">Brecha observada, cohorte a cohorte</div>',
                    unsafe_allow_html=True)
        fb = go.Figure()
        fb.add_trace(go.Bar(
            x=br.index.astype(str), y=br.brecha, width=0.52,
            marker=dict(color=NARANJA, cornerradius=4,
                        line=dict(width=2, color='white')),
            text=[num(x, 1, signo=True) for x in br.brecha], textposition='outside',
            textfont=dict(size=12.5, color=TINTA_2), cliponaxis=False,
            hovertemplate='Cohorte %{x}<br>Brecha %{y:.2f} pp<extra></extra>'))
        lienzo(fb, 'Cohorte de graduación', 'Puntos porcentuales', alto=270, leyenda=False)
        fb.update_yaxes(range=[0, max(br.brecha.max() * 1.32, 1)])
        st.plotly_chart(fb, width='stretch', config=PLOTLY_CONF)

    st.markdown('<div class="nota">La brecha es positiva en las cinco cohortes y su '
                'magnitud es estable. El máximo de la cohorte 2019 coincide con el '
                'seguimiento realizado en 2020: el confinamiento afectó de manera '
                'desigual a los sectores donde se emplean unos y otros egresados. Por '
                'eso el anexo 1 reporta la estimación excluyendo esas cohortes.</div>',
                unsafe_allow_html=True)

    with st.expander('Ver como tabla'):
        t = ev.copy()
        t['tasa'] = t['tasa'].round(2)
        st.dataframe(t.rename(columns={'cohorte': 'Cohorte', 'modalidad': 'Modalidad',
                                       'graduados': 'Graduados', 'cotizantes': 'Cotizantes',
                                       'tasa': 'Tasa (%)'}),
                     hide_index=True, width='stretch')

# ==========================================================================
# VISTA 3 — brecha contra cobertura de la acreditación
# ==========================================================================
with v3:
    cob = cobertura_virtual(programa)
    puntos = [(a, SEMAFORO[a][0],
               float(cob.loc[a, 'cobertura']) if a in cob.index else 0.0,
               int(cob.loc[a, 'programas']) if a in cob.index else 0,
               SEMAFORO[a][3]) for a in vistos]

    st.markdown('<div class="titulo-vista">Dónde el instrumento de política llega, '
                'y dónde no</div>'
                '<div class="sub-vista">Eje horizontal: porcentaje de programas virtuales '
                'del campo con acreditación en alta calidad. Eje vertical: brecha estimada. '
                'El tamaño del punto es el número de programas virtuales del campo.</div>',
                unsafe_allow_html=True)

    # Los puntos se agolpan contra el eje vertical, así que los rótulos se colocan
    # como anotaciones con un desplazamiento propio: el automático los encima.
    DESPLAZ = {'Salud Y Bienestar': 9, 'Ciencias Naturales, Matematicas Y Estadistica': -9,
               'Arte Y Humanidades': -13, 'Ingenieria, Industria Y Construccion': 2}

    def radio(n_programas):
        return max(13, min(34, 11 + n_programas / 7))

    fig = go.Figure()
    fig.add_hrect(y0=-9, y1=0, fillcolor='rgba(208,59,59,0.05)', line_width=0,
                  layer='below')
    for cat in ('Rojo', 'Amarillo', 'Verde'):
        sub = [p for p in puntos if p[4] == cat]
        if not sub:
            continue
        fig.add_trace(go.Scatter(
            x=[p[2] for p in sub], y=[p[1] for p in sub], mode='markers',
            marker=dict(size=[radio(p[3]) for p in sub],
                        color=ESTADO[cat], symbol=FORMA[cat], opacity=0.92,
                        line=dict(width=2, color='white')),
            name=cat,
            customdata=[[corto(p[0]), p[3]] for p in sub],
            hovertemplate='<b>%{customdata[0]}</b><br>Cobertura %{x:.1f} %<br>'
                          'Brecha %{y:.2f} pp<br>%{customdata[1]} programas virtuales'
                          '<extra></extra>'))
    for a, b, cv, npro, cat in puntos:
        fig.add_annotation(x=cv, y=b, text=corto(a), showarrow=False,
                           xanchor='left', yanchor='middle',
                           xshift=radio(npro) / 2 + 7, yshift=DESPLAZ.get(a, 0),
                           font=dict(size=11.5, color=TINTA_2))
    fig.add_hline(y=0, line_dash='dot', line_color=TINTA_3, line_width=1.5)
    fig.add_annotation(x=0.35, y=-8.2, text='rezago verificado con cobertura casi nula',
                       showarrow=False, xanchor='left',
                       font=dict(size=11.5, color='#a02e2e'))
    lienzo(fig, 'Programas virtuales acreditados en el campo (%)',
           'Brecha de vinculación formal (pp)', alto=470)
    fig.update_xaxes(range=[-0.6, 13])
    fig.update_yaxes(range=[-10, 31])
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONF)

    st.markdown('<div class="nota">Todos los campos se agolpan contra el eje vertical: '
                'ninguno supera el 13&nbsp;% de cobertura y la mayoría está por debajo '
                'del 6&nbsp;%. La franja inferior —rezago verificado y cobertura casi '
                'nula— es la que concentra la prioridad de política, y en ella solo '
                'aparece TIC.</div>', unsafe_allow_html=True)

    with st.expander('Ver como tabla'):
        st.dataframe(
            pd.DataFrame([(corto(p[0]), p[1], p[2], p[3], p[4]) for p in puntos],
                         columns=['Campo', 'Brecha (pp)', 'Cobertura (%)',
                                  'Programas virtuales', 'Semáforo']),
            hide_index=True, width='stretch',
            column_config={
                'Brecha (pp)': st.column_config.NumberColumn(format='%.2f'),
                'Cobertura (%)': st.column_config.NumberColumn(format='%.1f')})

# ==========================================================================
# VISTA 4 — incertidumbre, no simulación
# ==========================================================================
with v4:
    ident = COEFICIENTES['interaccion']['programas_identificantes']
    st.markdown('<div class="titulo-vista">Qué tanto podría cambiar la brecha si '
                'creciera la acreditación</div>'
                f'<div class="sub-vista"><b>Esta vista no simula escenarios: muestra '
                f'incertidumbre.</b> El coeficiente de interacción entre virtualidad y '
                f'acreditación no está identificado, porque solo {ident} programas '
                f'virtuales acreditados sostienen su estimación. La franja es el intervalo '
                f'de confianza del 95&nbsp;%, y abarca efectos de signo opuesto: los datos '
                f'no permiten saber si la pendiente sube o baja.</div>',
                unsafe_allow_html=True)

    inf, sup = COEFICIENTES['interaccion']['ic']
    coef = COEFICIENTES['interaccion']['coef']
    obs_min, obs_max = COEFICIENTES['rango_observado_acreditacion']
    xs = [i / 2 for i in range(0, 101)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs + xs[::-1],
        y=[sup * x / 100 for x in xs] + [inf * x / 100 for x in xs[::-1]],
        fill='toself', fillcolor='rgba(235,104,52,0.14)', line=dict(width=0),
        name='Intervalo de confianza del 95 %', hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=xs, y=[coef * x / 100 for x in xs], mode='lines',
        line=dict(color=NARANJA, width=2.5, dash='dot'),
        name='Estimación puntual (no significativa)',
        hovertemplate='Cobertura %{x:.0f} %<br>Cambio implicado %{y:.2f} pp<extra></extra>'))
    fig.add_vrect(x0=obs_min, x1=obs_max, fillcolor='rgba(42,120,214,0.10)', line_width=0,
                  layer='below')
    fig.add_annotation(x=(obs_min + obs_max) / 2, y=0.965, yref='paper', yanchor='top',
                       text='rango observado<br>en los datos', showarrow=False,
                       align='center', font=dict(size=11.5, color='#1c5cab'))
    fig.add_hline(y=0, line_color=BASE, line_width=1.5)
    lienzo(fig, 'Cobertura de la acreditación en la oferta virtual (%)',
           'Cambio implicado en la brecha (pp)', alto=440)
    fig.update_xaxes(range=[0, 50])
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONF)

    c1, c2, c3 = st.columns(3, gap='small')
    for col, rot, cif, pie in (
        (c1, 'Coeficiente de interacción', f'{num(coef, 2, signo=True)} pp',
         'Estimación puntual, sin significancia estadística.'),
        (c2, 'Intervalo de confianza del 95 %', f'{num(inf, 1)} a {num(sup, 1)}',
         'Incluye el cero y ambos signos: el efecto no está identificado.'),
        (c3, 'Programas que lo identifican', f'{ident}',
         'Programas virtuales acreditados en todo el país, cohortes 2021 y 2022.'),
    ):
        with col:
            st.markdown(f"""
            <div class="kpi">
              <div class="rotulo">{rot}</div>
              <div class="cifra" style="font-size:25px">{cif}</div>
              <div class="pie">{pie}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="nota">La franja azul marca el rango de cobertura que '
                'existe hoy en los datos. A su derecha, cualquier valor corresponde a un '
                'escenario sin respaldo empírico, y la franja naranja se ensancha porque '
                'la incertidumbre crece con la distancia a lo observado. La lectura de '
                'política es directa: la pregunta sobre si la acreditación sirve a la '
                'modalidad virtual no podrá responderse mientras la cobertura siga donde '
                'está.</div>', unsafe_allow_html=True)

st.divider()
st.caption(f'Versión del panel: {VERSION_PANEL}. Los coeficientes y la clasificación '
           'provienen de los anexos 1 y 4 del policy paper y no se reestiman en tiempo de '
           'ejecución. Fuentes: SNIES, archivos de graduados; Observatorio Laboral para '
           'la Educación, indicador de ingreso base de cotización.')
