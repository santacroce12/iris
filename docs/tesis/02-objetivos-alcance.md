# 2. Objetivos y alcance

## 2.1 Pregunta de investigación

¿En qué medida es posible unificar, mediante una plataforma web local, el acceso a funciones
básicas y avanzadas de cámaras IP de distintos fabricantes o modelos usando ONVIF, RTSP y APIs
propietarias, sin perder trazabilidad sobre las diferencias reales entre marcas?

## 2.2 Hipótesis

Es posible desarrollar una plataforma unificada que integre cámaras IP de distintos fabricantes o
modelos y ejecute sobre ellas un conjunto común de funciones básicas y avanzadas, siempre que el
sistema combine protocolos estándar (ONVIF, RTSP) con adaptadores específicos para APIs
propietarias, aceptando que el nivel de profundidad funcional alcanzado dependerá de la apertura
técnica de cada marca.

## 2.3 Objetivo general

Desarrollar una plataforma web local capaz de integrar cámaras IP multimarca y unificar el acceso
a funciones comunes y avanzadas mediante un motor central de capacidades que detecte, para cada
operación, qué protocolo la resuelve y con qué nivel de confianza puede afirmarse que la cámara la
soporta.

## 2.4 Objetivos específicos y su estado

| # | Objetivo específico | Estado |
|---|---|---|
| 1 | Diseñar una arquitectura modular basada en adaptadores para protocolos estándar y APIs propietarias | ✅ Logrado — ver cap. 6 |
| 2 | Implementar un backend que registre cámaras, detecte sus capacidades reales y exponga una interfaz uniforme de operaciones | ✅ Logrado |
| 3 | Implementar un frontend que administre cámaras, visualice video/snapshots y ejecute funciones avanzadas desde una interfaz única | ✅ Logrado |
| 4 | Integrar al menos tres escenarios de cámaras o fabricantes distintos, priorizando Hikvision como caso principal | ✅ Logrado — ver §2.5 |
| 5 | Validar el acceso a funciones básicas comunes (video en vivo, snapshot, perfiles, estado, hora, reinicio, OSD, imagen, movimiento, eventos, salud) | ✅ Logrado por ISAPI y por ONVIF en las **dos** cámaras Hikvision, PTZ y domo (29/09) |
| 6 | Integrar al menos un conjunto de funciones premium reales sobre una cámara con API propietaria avanzada | ✅ Logrado — analítica de reglas dibujables sobre la PTZ, y desde el 29/09 también sobre el domo por la vía clásica (§7.2.1), ver cap. 7 |
| 7 | Construir una matriz comparativa de compatibilidad por cámara y por función | ✅ Logrado, con exportación a CSV |
| 8 | Documentar experimentalmente las diferencias entre interoperabilidad estándar y acceso propietario | ✅ Logrado sobre las dos cámaras Hikvision, con latencias medidas por los dos protocolos en cada una (§7.5) |

## 2.5 Sobre el objetivo #4: los escenarios integrados

El objetivo pide "al menos tres escenarios de cámaras o fabricantes distintos, priorizando
Hikvision como caso principal". El trabajo integró los siguientes:

1. **PTZ Hikvision** (DS-2DF8A836IX-AEL) — analítica clásica sobre `/ISAPI/Smart/*`.
2. **Domo Hikvision DeepinView** (iDS-2CD7146G2-IZS) — analítica sobre AI Open Platform, una API
   completamente distinta a la anterior aunque el fabricante sea el mismo.
3. **Bullet Hikvision DeepinView de parking** (iDS-2CD7A46G0/P-IZHSY) — reconocimiento de plazas
   de estacionamiento sobre `/ISAPI/Parking/*`, una **tercera** familia de analítica, distinta de
   las dos anteriores en formato, convención de coordenadas y modelo de activación (§7.2).
4. **Cámara Hikvision Value** (DS-2CD1023G2-I) — sin analítica, caso de contraste.
5. **Cámara Scati** — marca distinta a Hikvision, sin funciones de analítica propietaria. [Estado
   de la integración: ver cap. 7 — pendiente al momento de escribir este capítulo.]

El anteproyecto original consideraba también, como arquitectura de referencia, adaptadores para
Axis (VAPIX) y para un "tercer proveedor genérico", y el cronograma de la Fase 3 proponía
específicamente validar Scati u otra marca disponible como caso comparativo. Sobre esto corresponde
una aclaración metodológica: los tres primeros escenarios (PTZ, domo DeepinView y bullet de
parking) son, formalmente, de la misma marca. Sin embargo, se sostiene que satisfacen la intención
del objetivo —y la superan— porque exponen una fragmentación **más severa** que la fragmentación
entre marcas que motivó originalmente el trabajo: tres productos del mismo fabricante, hablando el
mismo protocolo de transporte (ISAPI), resultan tan incompatibles entre sí en su analítica como lo
serían tres fabricantes distintos. Este hallazgo se desarrolla en el capítulo 7 y se sostiene que
constituye evidencia más fuerte para la hipótesis del trabajo, no una desviación de ella: si la
fragmentación apareciera solo entre marcas, cabría pensar que basta con "conocer bien a cada
fabricante" para resolverla; que aparezca dentro de una misma marca indica que el problema es
estructural y no anecdótico. (El §7.2.1 agrega un matiz descubierto el 29/09: esa misma
fragmentación puede no ser una propiedad fija del modelo, sino depender del estado de firmware o
configuración de cada unidad en un momento dado. El §7.2.2, con la tercera cámara, identifica el
mecanismo concreto detrás de eso: los modos de análisis de video del equipo son mutuamente
excluyentes, de modo que una misma cámara cambia su superficie de API completa según cómo esté
configurada. Ambos hallazgos refuerzan, no debilitan, la necesidad de verificar contra el hardware
real en vez de asumir capacidades por modelo o por fabricante.)

## 2.6 Alcance

El trabajo contempla el desarrollo de un producto mínimo viable con los siguientes alcances:

- Registro manual de cámaras IP por dirección y credenciales.
- Validación de conectividad por ONVIF, RTSP y API propietaria, cuando corresponda.
- Consulta de información del dispositivo, perfiles de video y snapshot.
- Visualización de video en vivo mediante RTSP, republicado a través de MediaMTX hacia el
  navegador (WebRTC/HLS), sin que las credenciales de la cámara lleguen nunca al cliente web.
- Consulta de estado general, sincronización horaria, reinicio remoto, configuración de OSD,
  ajustes básicos de imagen, configuración y consulta de detección de movimiento.
- Recepción de eventos en tiempo real, agrupados en episodios para evitar el registro redundante
  de avisos repetidos.
- Matriz de compatibilidad por cámara y por función, con distinción entre lo declarado por el
  fabricante y lo verificado mediante una llamada real.
- Editor de reglas de analítica (líneas de cruce, zonas de intrusión) dibujadas sobre la imagen,
  con traducción de coordenadas hacia el sistema propio de cada cámara.
- Registro de logs por acción y protocolo utilizado, incluida la latencia de cada llamada.
- Un corredor de experimentos que repite cada función N veces por protocolo y cámara para obtener
  tasa de éxito y latencias (percentiles 50 y 95), como evidencia cuantitativa adicional a la
  demostración funcional.

## 2.7 Limitaciones

El trabajo no contempla, en esta etapa:

- Grabación continua tipo NVR (existe una grabación bajo demanda por cámara, distinta de un
  sistema de grabación permanente con gestión de retención).
- Actualización de firmware.
- Gestión avanzada de usuarios (la herramienta es local y de un único operador; no incluye
  autenticación de usuarios de la plataforma).
- Arquitectura en clúster o de alta disponibilidad, ni soporte multi-tenant.
- Soporte total y profundo para todas las marcas del mercado.

El nivel de acceso alcanzado a las funciones avanzadas de cada cámara depende, en cada caso, de
factores fuera del control del desarrollo: la documentación pública disponible del fabricante, la
versión de firmware instalada, los permisos del usuario configurado en la cámara y la existencia
real de una API propietaria abierta para esa función. El capítulo 7 documenta, cámara por cámara,
en qué medida cada uno de estos factores limitó el resultado.
