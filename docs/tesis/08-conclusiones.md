# 8. Conclusiones y trabajo futuro

> **Estado al 29/09/2026**: capítulo cerrado sobre la base del capítulo 7, que a esta fecha está
> completo salvo la integración de la cámara Scati (§7.8), pendiente de acceso al hardware. Ese
> caso es un contraste adicional previsto desde el anteproyecto, no una pieza de la que dependa la
> respuesta a la pregunta de investigación — así que las conclusiones que siguen no deberían
> cambiar de fondo cuando se cierre, aunque sí conviene revisarlas cuando eso ocurra.

## 8.1 Respuesta a la pregunta de investigación

La pregunta (§2.1) es en qué medida es posible unificar el acceso a funciones básicas y avanzadas
de cámaras IP de distintos fabricantes o modelos, sin perder trazabilidad sobre las diferencias
reales entre marcas. La respuesta tiene tres niveles, no un sí o un no:

**Qué se unificó por completo.** La interfaz de administración es única para todas las cámaras
integradas, sin importar el protocolo real detrás de cada operación: el frontend nunca sabe si una
llamada se resolvió por ISAPI, por ONVIF o por RTSP (§6.1–6.2). El modelo de datos de eventos,
reglas de analítica y capacidades es el mismo para las dos familias de Hikvision, a pesar de que
sus reglas de analítica se configuran por dos APIs completamente distintas por debajo (§6, §7.2).

**Qué se unificó parcialmente, con la diferencia documentada en vez de ocultada.** Las funciones
comunes —información del dispositivo, perfiles de video, hora, imagen, OSD— se leen y escriben por
los dos protocolos con paridad de resultado pero no de camino: ONVIF resuelve identidad y hora con
menos latencia que ISAPI, e ISAPI resuelve todo lo que depende de negociar un perfil de video con
menos latencia que ONVIF (§7.5, §7.5.1). La detección de movimiento es el caso límite de esta
categoría: por ONVIF no se puede leer ni escribir como una operación de datos, solo confirmar si la
cámara *publica* el evento correspondiente — una asimetría prevista en la teoría (§3.3) y
confirmada empíricamente en las dos cámaras, con una tasa de éxito del 0 % consistente y
reproducible, no un fallo intermitente (§7.5).

**Qué no se logró unificar, y por qué es un límite estructural y no una falla de implementación.**
La analítica de inteligencia artificial del domo por AI Open Platform nunca se pudo recrear por
API una vez perdida tras un reinicio, pese a probar seis variantes distintas de la petición (§7.7)
— un límite documentado de la superficie que expone el fabricante, no de la plataforma. Y, de forma
más significativa para la pregunta de investigación: la fragmentación de API que se buscaba medir
*entre marcas* resultó estar presente, con la misma severidad, *dentro de una sola marca* (§7.2), y
además no fija en el tiempo: la misma unidad de domo pasó, sin cambiar de modelo, a exponer una
segunda familia de analítica que antes rechazaba explícitamente (§7.2.1). Eso no es una falla de la
plataforma — es exactamente el fenómeno que la plataforma existe para hacer visible en vez de
ocultar.

**Síntesis**: es posible unificar el acceso operativo (una interfaz, un modelo de datos, un
registro de capacidades) sin necesidad de unificar la profundidad funcional real, que sigue
dependiendo de qué expone cada dispositivo en cada momento. La trazabilidad no se pierde porque el
sistema nunca afirma más de lo que pudo verificar — es, de hecho, el aporte específico del motor de
capacidades declarado/verificado (§3.5, §6, §7.9).

## 8.2 Validación o refutación de la hipótesis

La hipótesis (§2.2) sostiene que es posible desarrollar una plataforma unificada que integre
cámaras de distintos fabricantes o modelos y ejecute sobre ellas un conjunto común de funciones,
siempre que se combinen protocolos estándar con adaptadores propietarios, aceptando que la
profundidad funcional dependerá de la apertura técnica de cada marca.

**La evidencia del capítulo 7 sostiene la hipótesis.** El conjunto común de funciones básicas
—identidad, hora, video, imagen, movimiento— se ejecuta hoy sobre las dos cámaras Hikvision por los
dos protocolos, con el nivel de profundidad efectivamente desigual que la propia hipótesis
anticipaba (§7.4, §7.5, §7.9). La analítica avanzada, que la hipótesis reconoce como dependiente de
"la apertura técnica de cada marca", en efecto varió: completa por API propietaria en la PTZ desde
el inicio, completa por dos APIs propietarias distintas en el domo hacia el final del trabajo, y
sin verificación posible en la cámara de contraste sin analítica (Value, §7.1).

**El hallazgo de §7.2 no estaba previsto en la hipótesis original, y corresponde preguntarse si la
refuerza o la debilita.** Se sostiene que la **refuerza**: la hipótesis no exige que "cada marca sea
internamente consistente" — exige que la plataforma pueda combinar protocolos estándar con
adaptadores específicos y aceptar que el resultado será desigual. Que la desigualdad aparezca
*dentro* de una misma marca, y que además no sea estable en el tiempo para el mismo equipo físico
(§7.2.1), es una versión más exigente del escenario que la hipótesis ya contemplaba, no una
excepción a él. Si la hipótesis hubiera fallado ante este hallazgo, habría sido señal de que estaba
mal formulada — al sostenerse, es señal de que reconoció desde el planteo cuál era el verdadero
problema: no "las marcas son distintas entre sí", sino "ningún fabricante garantiza una superficie
de API estable ni siquiera dentro de su propio catálogo, y por lo tanto ninguna plataforma de
integración puede permitirse memorizar capacidades en vez de verificarlas".

## 8.3 Cumplimiento de los objetivos específicos

Retomando la tabla de §2.4:

Los **objetivos 1 a 4** (arquitectura modular por adaptadores, backend con detección de
capacidades, frontend unificado, al menos tres escenarios de cámara) se dan por logrados sin
reservas: la arquitectura está implementada, probada con 112 tests, y verificada contra dos
cámaras reales de dos familias de firmware distintas dentro de la misma marca — que, según se
argumenta en §2.5, satisface la intención del objetivo con un margen mayor al previsto, porque la
fragmentación encontrada es más severa que la fragmentación entre marcas que motivó el trabajo.

El **objetivo 5** (validar funciones básicas comunes) y el **objetivo 8** (documentar
experimentalmente la diferencia entre interoperabilidad estándar y acceso propietario) dependían
directamente de verificar ONVIF contra hardware real — el bloqueo más importante de todo el
proyecto durante la mayor parte de su desarrollo. Se cerraron los dos el 29/09/2026, con evidencia
cuantitativa (latencias p50/p95, tasas de éxito) medida en las dos cámaras reales, no estimada ni
tomada del simulador (§7.4, §7.5, §7.5.1).

El **objetivo 6** (integrar funciones premium reales sobre una cámara con API propietaria avanzada)
se logró dos veces por caminos distintos: la analítica dibujable de la PTZ desde el inicio del
trabajo, y la misma analítica clásica sobre el domo desde el 29/09, cuando esa cámara empezó a
responder también por esa vía (§7.2.1). El objetivo pedía "al menos un conjunto"; el trabajo entrega
dos, sobre dos cámaras, con dos historias de verificación independientes.

El **objetivo 7** (matriz comparativa de compatibilidad) se logró con un alcance mayor al
mínimo exigible: no es una tabla de sí/no, sino una matriz con tres estados de soporte y dos niveles
de confianza (declarado/verificado) por cada celda, exportable a CSV y a Markdown, con la evidencia
cruda de cada verificación disponible para auditoría (§3.5, §6.7, §7.9).

## 8.4 Aporte del trabajo

Retomando lo previsto en la justificación del trabajo (§1.4):

- **Interoperabilidad básica viable por protocolos estándar** — sostenido con evidencia cuantitativa
  para las dos cámaras Hikvision (§7.4, §7.5). Queda como límite conocido, no como aporte refutado,
  que esto se demostró dentro de una sola marca; el caso Scati (§7.8) es el que hubiera extendido
  esta conclusión a un segundo fabricante, y queda pendiente de acceso al hardware.
- **La unificación profunda de funciones premium requiere integración por marca, y por modelo
  dentro de la marca** — sostenido con fuerza inesperada por §7.2 y, sobre todo, por §7.2.1: no
  alcanza con integrar por modelo, porque el mismo modelo cambió de superficie de API sin cambiar de
  identidad de hardware ni de versión de firmware documentada.
- **Una arquitectura por adaptadores permite escalar sin acoplar al frontend a un protocolo
  particular** — sostenido por el diseño verificado en el capítulo 6 y confirmado en la práctica
  cuando el domo empezó a responder por una segunda familia de analítica: agregar esa familia al
  motor de reglas es, por diseño, un adaptador más, no un cambio en el resto del sistema (aunque
  ese adaptador específico —ofrecer ambas familias a la vez en la misma cámara— quedó como trabajo
  pendiente, §8.6).
- **La comparación entre marcas puede modelarse formalmente mediante una matriz de capacidades con
  distinción declarado/verificado** — es, junto con el hallazgo de §7.2.1, el aporte más específico
  de este trabajo por sobre lo que pedía el anteproyecto original: no se limita a decir qué función
  anda en qué cámara, sino a decir *con qué grado de certeza* se puede afirmar eso, y a dejar
  registrada la evidencia concreta (payload, latencia, código de estado) detrás de cada afirmación
  (§3.5, §6.7, §7.9). El caso del bug propio en `GetOSDs` (§7.4) es la prueba de que esta disciplina
  no es un formalismo: encontró un error real que un enfoque "declarado alcanza" habría dejado
  invisible para siempre detrás de un "no soportado" incorrecto.

## 8.5 Limitaciones del trabajo

- **El acceso al hardware fue intermitente durante todo el desarrollo**, sujeto a la disponibilidad
  de la red de una oficina fuera del control del investigador. Esto retrasó la verificación de
  ONVIF durante semanas y dejó, al cierre de este documento, la integración de la cámara Scati sin
  resolver (§7.8) — no por una limitación técnica de la plataforma, sino por falta de acceso físico
  o de red al equipo.
- **La analítica de IA por AI Open Platform del domo nunca se observó disparando un evento real**
  durante el desarrollo del trabajo (§7.7); la conclusión sobre esa función específica se apoya en
  evidencia indirecta (declaración de capacidades, intentos de recreación documentados) y no en un
  evento observado. El hallazgo posterior de que la misma cámara sí dispara analítica por la vía
  clásica (§7.2.1) atenúa el impacto de esta limitación sobre el trabajo en conjunto, pero no la
  resuelve para AI Open Platform en particular.
- **El trabajo se concentra en Hikvision como caso fuerte**, según lo previsto en el anteproyecto;
  la generalización a otros fabricantes queda, a la fecha de este documento, sin un segundo caso con
  analítica propia que comparar (la Scati, cuando se integre, es un caso sin analítica avanzada, útil
  como contraste pero no como segunda instancia del fenómeno de fragmentación de §7.2).
- **La detección de un cambio de comportamiento en el domo (§7.2.1) fue casual, no buscada**: se
  descubrió al volver a grabar fixtures después de un cambio de IP, no como resultado de un
  monitoreo sistemático de cambios de capacidad a lo largo del tiempo. Es una limitación
  metodológica real: el trabajo puede afirmar que las capacidades cambian, pero no puede afirmar con
  qué frecuencia lo hacen, porque no se diseñó un mecanismo para observarlo de forma continua.
- **La evidencia cuantitativa de latencias (§7.5) es de una sola sesión de medición por cámara**, no
  una serie temporal. No permite afirmar si la latencia varía con la carga de la red, la hora del
  día o el uso prolongado del equipo — solo que, en el momento medido, el patrón relativo entre
  protocolos fue consistente entre las dos cámaras.

## 8.6 Trabajo futuro

- **Integrar la cámara Scati** cuando se resuelva el acceso (§7.8), y con eso extender la matriz de
  §7.9 y la comparación de §8.4 a un segundo fabricante.
- **Que el motor de reglas ofrezca las dos familias de analítica del domo a la vez** (Smart y AI
  Open Platform) en vez de comprometerse con una sola — el gap de diseño concreto que dejó expuesto
  el hallazgo de §7.2.1.
- **Convertir la medición de latencias en una serie temporal**, corriendo el corredor de
  experimentos (§7.5) de forma periódica y no solo una vez, para poder afirmar si el patrón
  ISAPI-vs-ONVIF se sostiene bajo distintas condiciones de red y de uso del equipo.
- **Monitorear cambios de capacidad de forma continua**, no solo al volver a grabar fixtures
  manualmente — re-ejecutar la detección de capacidades periódicamente y alertar cuando una cámara
  cambia de superficie de API, convirtiendo el hallazgo casual de §7.2.1 en un mecanismo sistemático
  de la propia plataforma.
- **Explorar si la analítica de AI Open Platform del domo puede recrearse por un mecanismo
  distinto** al probado (por ejemplo, exportando e importando la configuración completa del equipo
  en lugar de crear la tarea de análisis por partes), para cerrar la limitación de §7.7 y §8.5.
- **Extender el motor de capacidades a un tercer fabricante con analítica propietaria real** (no
  solo de contraste, como la Scati), para confirmar si el patrón "un adaptador por familia de
  comportamiento observada, no por marca ni por modelo" —que este trabajo tuvo que adoptar a partir
  del hallazgo de §7.2— se sostiene fuera de Hikvision.
- **Implementar la decisión pendiente sobre fotos en los eventos** (§7.6 y la bitácora, §6.6): que
  la plataforma pida un snapshot propio al abrir cada episodio, en lugar de depender de una función
  de adjuntar imagen que al menos una de las cámaras del trabajo no tiene.
