# El semáforo de la virtualidad

Código y datos del policy paper *Vinculación laboral formal de los egresados de
pregrado virtual en Colombia: brechas por campo de conocimiento y cobertura de la
acreditación en alta calidad, 2018-2023*.

Duvan Fernando Caleño Henao · Maestría en Economía y Política de la Educación ·
Universidad Externado de Colombia

---

## Qué hay en cada carpeta

```
semaforo-virtualidad/
├── datos/                    los cuatro archivos del panel
│   ├── panel_celda.csv       campo CINE × modalidad × cohorte (99 filas)
│   ├── panel_programa.csv    programa × cohorte (27.939 filas)
│   ├── semaforo.csv          clasificación por campo
│   └── control_calidad.csv   verificación del cruce
├── salidas/                  lo que generan los guiones (figuras, log, QR)
├── tablero.py                tablero interactivo — el semáforo
├── .streamlit/config.toml    tema visual del tablero
├── pipeline.py               reconstruye el panel desde los archivos del SNIES y el OLE
├── analisis.py               las seis especificaciones
├── robustez.py               las siete verificaciones de robustez
├── figura_cobertura.py       genera la Figura 2 del documento
├── generar_qr.py             genera el código QR del tablero publicado
├── analisis.do               las mismas estimaciones en Stata
└── requirements.txt          dependencias
```

---

## Puesta en marcha en Visual Studio Code

### 1. Instalar lo necesario

Necesitas **Python 3.10 o superior** y **Visual Studio Code**. Si no tienes Python,
descárgalo de python.org y, durante la instalación en Windows, marca la casilla
*Add Python to PATH*; sin eso VS Code no lo encuentra.

En VS Code instala la extensión **Python** de Microsoft. Al abrir esta carpeta, el
editor te la sugerirá solo, porque está declarada en `.vscode/extensions.json`.

### 2. Abrir el proyecto

`Archivo > Abrir carpeta…` y selecciona `semaforo-virtualidad`. Abre la carpeta
completa, no un archivo suelto: las rutas del proyecto se resuelven a partir de ella.

### 3. Crear el entorno virtual

Abre la terminal integrada con `Ctrl + Ñ` (o `Ver > Terminal`) y ejecuta:

**Windows**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS o Linux**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Después pulsa `Ctrl + Shift + P`, escribe *Python: Select Interpreter* y elige el que
diga `.venv`. Es el paso que más se olvida: si no lo haces, VS Code ejecuta con el
Python del sistema y no encuentra las librerías.

### 4. Levantar el tablero

Dos formas, ambas equivalentes.

Desde la terminal:
```
streamlit run tablero.py
```

O con el depurador: ve al panel *Ejecutar y depurar* (`Ctrl + Shift + D`), elige
**Tablero (Streamlit)** en el desplegable y pulsa `F5`. Esta segunda forma permite
poner puntos de interrupción dentro del código del tablero.

El navegador abre en `http://localhost:8501`. Para detenerlo, `Ctrl + C` en la
terminal.

### 5. Los demás guiones

El archivo `launch.json` trae una configuración por guion, de modo que puedes
ejecutarlos con `F5` sin escribir comandos. También funcionan desde la terminal:

```
python analisis.py            # las seis especificaciones
python robustez.py            # las siete verificaciones (tarda unos minutos)
python figura_cobertura.py    # regenera la Figura 2 en salidas/
python generar_qr.py https://direccion-del-tablero
python pipeline.py            # reconstruye el panel desde las fuentes originales
```

`pipeline.py` es el único que necesita los archivos originales del SNIES y del
Observatorio Laboral. Antes de ejecutarlo, ajusta las rutas del bloque `RUTAS` al
comienzo del archivo. Los demás trabajan sobre los CSV de `datos/`, que ya están
construidos.

---

## El tablero

La pantalla se lee de arriba hacia abajo. Una banda de encabezado con el título y la
versión del panel; cuatro indicadores de cabecera con las cifras que el documento
defiende —brecha media, conteo del semáforo, cobertura de la acreditación y volumen
de egresados bajo el filtro—; y debajo, cuatro vistas. Los tres controles —cohorte,
modalidad y campo— viven en la barra lateral y actúan simultáneamente sobre todas
las vistas.

1. **Semáforo.** Arriba, el semáforo propiamente dicho: tres carriles —rojo, amarillo y
   verde— con los campos que caen en cada uno y su brecha estimada. Debajo, un gráfico
   de bosque con la brecha de cada campo y su intervalo de confianza. Rojo cuando el
   intervalo queda enteramente por debajo de cero; verde cuando queda por encima y la
   ventaja alcanza cinco puntos; amarillo en el resto.
2. **Evolución.** La tasa de cotización dependiente por modalidad a lo largo de las
   cinco cohortes, con la franja entre ambas líneas sombreada, y debajo la brecha
   observada cohorte a cohorte.
3. **Brecha y cobertura.** El cruce entre la brecha de vinculación y la proporción de
   programas virtuales acreditados en cada campo. La franja inferior —rezago
   verificado y cobertura casi nula— es la que concentra la prioridad de política.
4. **Incertidumbre.** No es un simulador. Muestra la franja del intervalo de
   confianza del coeficiente de interacción, con el rango de cobertura realmente
   observado marcado sobre el eje.

Cada vista trae su versión en tabla dentro de un desplegable, para que ninguna cifra
dependa de leer un gráfico.

Los coeficientes están precalculados en el diccionario `COEFICIENTES` de `tablero.py`
y **no se reestiman al ejecutar**. Es deliberado: garantiza que lo que el tablero
muestre coincida con lo que reportan los anexos 1 y 4 del documento. Si los datos
cambian, hay que actualizar ese diccionario a mano y dejar constancia del cambio.

### Sobre los colores

El azul y el naranja de las modalidades son las dos primeras ranuras de una paleta
categórica validada: se distinguen entre sí con visión normal y con los tres tipos
de daltonismo más frecuentes. Los colores del semáforo son una paleta reservada de
estado y **nunca comunican solos**: cada punto lleva además una forma propia
—círculo, rombo, cuadrado— y cada carril, un rótulo de texto.

El tema de la aplicación está en `.streamlit/config.toml`, que además oculta el
botón *Deploy* y el menú de Streamlit. Si lo borra, Streamlit
usará sus colores por defecto y el tablero se verá distinto.

---

## Publicar el tablero

Para que el lector no tenga que instalar nada:

1. Sube esta carpeta a un repositorio público.
2. Despliégala en un servicio que ejecute aplicaciones Streamlit. Necesita ver
   `requirements.txt` en la raíz y apuntar a `tablero.py` como archivo principal.
3. Con la dirección en mano, ejecuta `python generar_qr.py <dirección>` y consigna la
   dirección y el QR en la tabla de acceso del Anexo 7.

---

## Stata

`analisis.do` replica las estimaciones. Abre el archivo, ajusta la línea

```
global proyecto "C:/Tesis/semaforo-virtualidad"
```

a la ruta de esta carpeta y ejecútalo completo. Lee los CSV de `datos/` y escribe el
registro y el gráfico en `salidas/`.
