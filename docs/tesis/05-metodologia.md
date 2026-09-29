# 5. Metodología

La metodología aplicada fue de carácter aplicado y experimental, organizada en cinco etapas. A
diferencia del anteproyecto original —que las describía de forma prospectiva—, este capítulo las
documenta de forma retrospectiva: qué se hizo, con qué herramienta y con qué resultado
metodológico, independientemente del resultado técnico (que se desarrolla en el capítulo 7).

## 5.1 Principio metodológico transversal

Antes de describir las etapas, corresponde señalar el principio que las atraviesa a todas y que se
sostiene como el aporte metodológico central del trabajo: **la plataforma no confía en lo que
declara el fabricante.** Cada afirmación sobre una capacidad de una cámara se clasifica según su
origen —declarada por el fabricante o verificada mediante una llamada real— y toda escritura sobre
una cámara sigue el ciclo *respaldo → escritura → relectura → comparación* antes de darse por
aplicada. Este principio se adoptó desde el diseño inicial y se sostuvo a lo largo de las cinco
etapas, no se incorporó a posteriori: aparece por primera vez en el diseño de la arquitectura
(etapa 2) y se verifica activamente durante la validación experimental (etapa 4).

## 5.2 Etapa 1 — Relevamiento técnico

Se relevaron tres fuentes de información, en orden de confiabilidad creciente:

1. **Documentación oficial del fabricante**: los manuales ISAPI de la serie PTZ Ultra (896
   páginas) y de la serie DeepinView (974 páginas), y las especificaciones públicas de ONVIF.
2. **Sondeo directo contra el hardware disponible**: se construyó una herramienta de sondeo que
   consulta sistemáticamente un catálogo de endpoints conocidos y desconocidos contra cada cámara,
   registrando qué responde, con qué latencia y con qué código de error cuando corresponde.
3. **Ingeniería inversa de la interfaz web de la cámara**, como último recurso cuando las dos
   fuentes anteriores no alcanzaron. Este caso se dio de forma concreta con la API de analítica del
   domo DeepinView, cuyos endpoints de AI Open Platform no figuran en el manual oficial de 974
   páginas y se recuperaron descargando y analizando los archivos JavaScript de la propia interfaz
   de administración de la cámara. Se documenta como hallazgo en el capítulo 7 porque constituye,
   en sí mismo, evidencia sobre el estado de la documentación pública disponible para integradores.

Esta etapa se apoyó, además, en una herramienta de grabación (`tools/recorder`) que automatiza el
sondeo, sanitiza las respuestas (elimina número de serie, dirección MAC, direcciones IP y
credenciales antes de guardarlas) y las conserva como *fixtures* — insumo tanto para la
documentación como para las pruebas automatizadas descritas en la etapa 3.

## 5.3 Etapa 2 — Diseño de arquitectura

Se definieron, en este orden: el modelo de datos persistente, la interfaz común que deben cumplir
los adaptadores de cada protocolo, el motor de capacidades (que resuelve qué adaptador ejecuta cada
operación y registra el resultado) y el flujo de detección–ejecución–registro que atraviesa todas
las operaciones del sistema. Las decisiones de arquitectura y su justificación se documentan en el
capítulo 6.

## 5.4 Etapa 3 — Implementación

El desarrollo se organizó de forma incremental: primero el núcleo (alta de cámaras, detección
básica, registro de operaciones), luego los adaptadores por protocolo, luego las funciones
avanzadas (reglas de analítica dibujables, motor de eventos en tiempo real) y por último las
herramientas de evidencia (corredor de experimentos, exportación de matriz). Cada incremento se
acompañó de pruebas automatizadas — 112 pruebas al momento de escribir este capítulo, ejecutadas
contra respuestas grabadas de hardware real y contra un simulador construido específicamente para
este trabajo (§5.6).

## 5.5 Etapa 4 — Validación experimental

Esta etapa combina dos tipos de evidencia, deliberadamente distintos entre sí:

- **Validación funcional contra hardware real**: registrar la cámara en la plataforma, ejecutar
  cada función y observar el resultado directamente contra el equipo — por ejemplo, dibujar una
  línea de detección en la interfaz, guardarla, y verificar físicamente que cruzarla dispara el
  evento correspondiente en la pantalla de eventos en menos de dos segundos.
- **Validación cuantitativa mediante repetición**: para las funciones que lo permiten, se construyó
  un corredor de experimentos que repite cada operación un número configurable de veces (30 por
  defecto) contra cada cámara y cada protocolo, y calcula la tasa de éxito y las latencias en los
  percentiles 50 y 95. Esto responde a una limitación metodológica de la sola validación funcional:
  que una función haya funcionado una vez no permite afirmar que funcione de forma consistente.

## 5.6 Uso de un simulador como instrumento metodológico

Una decisión metodológica particular de este trabajo, no prevista en el anteproyecto original,
merece justificación explícita: se construyó una **cámara Hikvision simulada** que reproduce, a
partir de las respuestas reales grabadas en la etapa 1, el comportamiento verificado de las cámaras
físicas — incluidas sus particularidades no documentadas, como que una escritura sobre la colección
completa de reglas responda con éxito sin aplicar el cambio.

Esta decisión no reemplaza la validación contra hardware real: **ninguna afirmación de este trabajo
sobre lo que una cámara real soporta se basa en el simulador.** Su función es exclusivamente
metodológica, en dos sentidos. Primero, permite que el desarrollo y las pruebas automatizadas del
sistema no dependan de tener acceso continuo al hardware físico, lo cual resultó necesario dado que
el acceso a las cámaras de este trabajo es intermitente (red local de una oficina, con
disponibilidad variable). Segundo, y más relevante metodológicamente, permite **verificar que el
sistema se comporta correctamente frente a las particularidades adversas ya documentadas del
hardware real** de forma repetible y sin consumir tiempo de acceso al equipo físico: si el sistema
falla al manejar una cámara que responde éxito sin aplicar el cambio, ese defecto se puede
reproducir y corregir contra el simulador, y solo la corrección final se confirma una vez contra el
hardware real.

## 5.7 Etapa 5 — Análisis de resultados

Se construyó la matriz comparativa de compatibilidad, se clasificó cada función en soportada, no
soportada, parcialmente soportada o sin verificar, y se analizaron las limitaciones encontradas
distinguiendo su origen: limitación de firmware, de permisos de usuario, de documentación pública
insuficiente o de diseño del propio protocolo. Esta clasificación se desarrolla con el detalle
completo en el capítulo 7.

## 5.8 Técnicas e instrumentos

**Técnicas**: análisis documental de manuales y especificaciones; pruebas de integración contra
hardware real; pruebas funcionales sobre capacidades comunes y avanzadas; comparación experimental
entre protocolo estándar y acceso propietario; registro sistemático de resultados mediante logs
estructurados, capturas y la matriz de compatibilidad.

**Instrumentos**: el backend y frontend desarrollados en este trabajo (que son, a la vez, objeto de
estudio e instrumento de medición); la base de datos PostgreSQL como registro persistente de toda
la evidencia (`operation_logs` conserva protocolo, latencia, resultado y detalle de cada llamada
realizada durante todo el desarrollo); el servidor MediaMTX para la validación de streaming; la
herramienta de grabación de respuestas (`tools/recorder`); el corredor de experimentos
(`tools/experiments`); y la documentación técnica oficial de cada fabricante.
