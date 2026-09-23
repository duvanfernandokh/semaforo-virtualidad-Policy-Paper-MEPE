*==============================================================================
* EL SEMÁFORO DE LA VIRTUALIDAD
* Acreditación de alta calidad y vinculación laboral formal de los egresados
* de pregrado virtual en Colombia. Cohortes de graduación 2018-2022.
*
* Insumos: panel_celda.csv y panel_programa.csv, producidos por pipeline.py
* Autor: Duvan Fernando Caleño Henao — MEPE, Universidad Externado de Colombia
*
* CORRESPONDENCIA CON EL DOCUMENTO
*   M1  ecuación (1) del cuerpo y del Anexo 1: brecha media
*   M2  ecuación (2): brecha por campo. Produce el semáforo y la Figura del Anexo
*   M3  ecuación (3): acreditación e interacción, sobre el panel de programas
*   M4  = R3 de la Tabla A4: especificación binomial con enlace logit
*   M5  = R4 de la Tabla A4: exclusión de las cohortes 2019 y 2020
*   M6  prueba de proporciones sobre la cobertura del instrumento
*   R1  agrupación de errores por campo          R2  bootstrap wild-cluster
*   R5  ponderación alternativa                  R6  prueba placebo
*   R7  sensibilidad al umbral de soporte
*
* Requiere el comando de usuario boottest para la prueba R2:
*   ssc install boottest, replace
*
*==============================================================================

clear all
set more off
version 17

* Ajustar a la carpeta de trabajo local
* Ruta de la carpeta del proyecto (la que contiene la subcarpeta datos)
global proyecto "C:/Tesis/semaforo-virtualidad"
global ruta "$proyecto/datos"
cd "$ruta"

capture log close
log using "$proyecto/salidas/semaforo_virtualidad.log", replace text

*------------------------------------------------------------------------------
* 1. PANEL DE CELDAS: área CINE campo amplio x modalidad x cohorte
*------------------------------------------------------------------------------
import delimited "panel_celda.csv", clear varnames(1) encoding(UTF-8)

* La dependiente es la tasa de cotización dependiente: cotizantes dependientes
* observados en el año de corte t+1 sobre graduados de la cohorte t.
label variable tasa       "Tasa de cotización dependiente"
label variable virtual    "Modalidad virtual (1 = sí)"
label variable graduados  "Graduados de pregrado de la celda"

encode area, generate(area_id)
label variable area_id "Área CINE campo amplio"

* Las celdas resumen poblaciones de tamaño muy distinto, así que toda la
* estimación se pondera por el número de graduados.
generate double pond = graduados

*--- Descriptivo: brecha nacional por cohorte --------------------------------
preserve
    collapse (sum) graduados cotizantes, by(cohorte virtual)
    generate tasa_nac = cotizantes / graduados
    reshape wide graduados cotizantes tasa_nac, i(cohorte) j(virtual)
    generate brecha_pp = 100 * (tasa_nac1 - tasa_nac0)
    list cohorte tasa_nac0 tasa_nac1 brecha_pp, noobs abbreviate(12)
restore

*--- M1: brecha media con efectos fijos de campo y cohorte -------------------
* Descuenta que la oferta virtual se concentra en unos campos y no en otros,
* y que el ciclo económico mueve la tasa de todos los egresados a la vez.
regress tasa virtual i.area_id i.cohorte [pweight = pond], vce(robust)
estimates store M1
display "Brecha media en puntos porcentuales: " %6.2f 100*_b[virtual]

*--- M2: brecha por campo de conocimiento (el semáforo con inferencia) -------
regress tasa i.virtual##i.area_id i.cohorte [pweight = pond], vce(robust)
estimates store M2

* Efecto marginal de la virtualidad dentro de cada campo, con intervalo.
* El semáforo se lee del intervalo: rojo si queda enteramente por debajo de
* cero, verde si queda por encima de cero y supera los cinco puntos.
margins area_id, dydx(virtual) level(95)
marginsplot, horizontal recast(scatter) yscale(reverse) ///
    xline(0, lpattern(dash)) ///
    title("Brecha de vinculación formal por campo de conocimiento") ///
    subtitle("Efecto de la modalidad virtual, cohortes 2018-2022") ///
    xtitle("Diferencia en la tasa de cotización dependiente") ///
    ytitle("") name(semaforo, replace)
graph export "$proyecto/salidas/semaforo.png", replace width(1600)

*--- M4: robustez con GLM binomial -------------------------------------------
* La dependiente es una proporción acotada entre cero y uno construida a partir
* de conteos; el enlace logit respeta esa estructura.
glm tasa virtual i.area_id i.cohorte, family(binomial graduados) link(logit) vce(robust)
estimates store M4
margins, dydx(virtual)

*--- M5: robustez excluyendo el seguimiento en pandemia ----------------------
* Las cohortes 2019 y 2020 se observan en 2020 y 2021, los dos años de mayor
* perturbación del mercado laboral.
regress tasa virtual i.area_id i.cohorte [pweight = pond] ///
    if !inlist(cohorte, 2019, 2020), vce(robust)
estimates store M5

estimates table M1 M5, keep(virtual) b(%9.4f) se(%9.4f) stats(N r2_a)


*------------------------------------------------------------------------------
* 1B. VERIFICACIONES DE ROBUSTEZ SOBRE EL PANEL DE CELDAS
*     Corresponden a las pruebas R1, R2, R5 y R6 de la Tabla A4 del Anexo 1.
*------------------------------------------------------------------------------

*--- R1: errores agrupados por campo de conocimiento -------------------------
* El panel tiene solo diez campos. Agrupar por campo permite correlación
* arbitraria entre las cohortes de un mismo campo.
regress tasa virtual i.area_id i.cohorte [pweight = pond], vce(cluster area_id)
estimates store R1
display "Conglomerados: " e(N_clust)

*--- R2: bootstrap wild-cluster ----------------------------------------------
* Con diez conglomerados los errores agrupados convencionales subestiman la
* varianza. boottest es un comando de usuario: si no está instalado, ejecute
* una sola vez  ssc install boottest, replace
capture which boottest
if _rc {
    display as error "Instale boottest con: ssc install boottest, replace"
}
else {
    quietly regress tasa virtual i.area_id i.cohorte [pweight = pond], ///
        cluster(area_id)
    boottest virtual, reps(4999) weighttype(rademacher) nograph
}

*--- R5: ponderación alternativa ---------------------------------------------
regress tasa virtual i.area_id i.cohorte, vce(robust)
estimates store R5
estimates table M1 R1 R5, keep(virtual) b(%9.4f) se(%9.4f) stats(N r2_a) ///
    title("Coeficiente de virtualidad según ponderación y agrupación")

*--- R6: prueba placebo por reasignación aleatoria ---------------------------
* Se reasigna al azar la condición de virtualidad mil veces, conservando el
* número de celdas virtuales, y se guarda el coeficiente de cada réplica.
* Ninguna debería acercarse al valor observado.
quietly regress tasa virtual i.area_id i.cohorte [pweight = pond], vce(robust)
scalar b_real = _b[virtual]
quietly count if virtual == 1
local k = r(N)

set seed 20260922
tempname memoria
tempfile placebos
postfile `memoria' double b_falso using "`placebos'", replace
forvalues i = 1/1000 {
    quietly {
        generate double u = runiform()
        sort u
        generate byte falso = (_n <= `k')
        regress tasa falso i.area_id i.cohorte [pweight = pond]
        post `memoria' (_b[falso])
        drop u falso
    }
}
postclose `memoria'

preserve
    use "`placebos'", clear
    replace b_falso = b_falso * 100
    summarize b_falso
    count if b_falso >= scalar(b_real) * 100
    display "Coeficiente real: " %6.2f scalar(b_real) * 100 " pp"
    display "Réplicas placebo que lo igualan o superan: " r(N) " de 1000"
restore

*------------------------------------------------------------------------------
* 2. PANEL DE PROGRAMAS: acreditación (solo cohortes 2021 y 2022)
*------------------------------------------------------------------------------
* El SNIES incorpora el estado de acreditación del programa en los archivos de
* graduados a partir de la vigencia 2021, de modo que esta parte del análisis
* solo puede correr sobre las dos últimas cohortes.
import delimited "panel_programa.csv", clear varnames(1) encoding(UTF-8)

destring acreditado ies_acreditada tasa, replace force
drop if missing(acreditado)

* Los programas muy pequeños producen tasas mecánicamente ruidosas: con tres
* graduados la tasa solo puede tomar cuatro valores.
keep if graduados >= 10

encode area, generate(area_id)
generate double pond = graduados
generate byte virt_acred = virtual * acreditado
label variable virt_acred "Virtual x Acreditado"

tabulate modalidad acreditado, row

*--- M3: acreditación, virtualidad y su interacción --------------------------
regress tasa i.virtual##i.acreditado i.area_id i.cohorte [pweight = pond], ///
    vce(cluster codigo_ies)
estimates store M3
margins, dydx(virtual) over(acreditado)
lincom 1.virtual#1.acreditado

* Advertencia metodológica: la interacción se identifica con una treintena de
* programas virtuales acreditados. El intervalo es amplio por construcción y el
* coeficiente no sostiene una conclusión en ningún sentido. Se reporta por
* transparencia, no como evidencia.
count if virtual == 1 & acreditado == 1
display "Programas virtuales acreditados en la estimación: " r(N)


*--- R7: sensibilidad al umbral mínimo de graduados por programa -------------
* El umbral de diez graduados es una decisión discrecional. Se replica la
* estimación con umbrales alternativos para verificar que no la gobierna.
foreach u in 0 5 10 20 50 {
    preserve
        quietly keep if graduados >= `u'
        quietly regress tasa i.virtual##i.acreditado i.area_id i.cohorte ///
            [pweight = pond], vce(cluster codigo_ies)
        display "Umbral `u' graduados | N = " e(N) ///
            " | virtual = " %6.4f _b[1.virtual] ///
            " | interacción = " %7.4f _b[1.virtual#1.acreditado]
    restore
}

*--- M6: asimetría en la cobertura del instrumento ---------------------------
* Este es el resultado que no depende de ningún supuesto de identificación.
preserve
    keep if cohorte == 2022
    tabulate modalidad acreditado, row chi2
    prtest acreditado, by(virtual)
restore

log close
*==============================================================================
