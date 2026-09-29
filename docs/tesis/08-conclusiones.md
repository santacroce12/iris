# 8. Conclusiones y trabajo futuro

> 🔴 **Este capítulo es un esqueleto guiado, no un borrador.** Las conclusiones de una tesis
> tienen que sintetizar resultados cerrados, y el capítulo 7 todavía tiene dos secciones abiertas
> (ONVIF y Scati). Escribir las conclusiones ahora significaría, en el mejor de los casos,
> adelantar una respuesta y tener que reescribirla, y en el peor, comprometerse con una conclusión
> que los datos finales podrían no sostener. Lo que sigue son las preguntas que cada sección
> tiene que responder, con la evidencia ya disponible marcada entre corchetes donde corresponde.

## 8.1 Respuesta a la pregunta de investigación

La pregunta (§2.1) es en qué medida es posible unificar el acceso a funciones básicas y avanzadas
de cámaras IP de distintos fabricantes sin perder trazabilidad sobre las diferencias reales entre
marcas. Esta sección tiene que responderla con una síntesis de tres niveles, no con un sí o un no:

- **Qué se unificó por completo** — [la interfaz de administración es única para las tres cámaras
  Hikvision y, si §7.8 se cierra favorablemente, también para Scati; el modelo de datos de eventos,
  reglas y capacidades es el mismo sin importar el protocolo de origen].
- **Qué se unificó parcialmente, con la diferencia documentada en vez de ocultada** — [funciones
  comunes leídas y escritas por dos protocolos con semántica distinta, como la hora o la imagen
  (§6, marco teórico §3.6); la detección de movimiento, que por ONVIF solo se puede *saber que
  existe*, no leer ni modificar (§3.3)].
- **Qué no se logró unificar, y por qué es un límite estructural y no una falla de
  implementación** — [la analítica de IA del domo, que no se puede recrear por API tras perderse
  (§7.7); la comparación ONVIF vs. propietaria, si §7.4 no llega a cerrarse con hardware real antes
  de la entrega].

## 8.2 Validación o refutación de la hipótesis

La hipótesis (§2.2) admite que el nivel de profundidad funcional dependerá de la apertura técnica
de cada marca. Con la evidencia del capítulo 7, corresponde evaluar explícitamente:

- ¿Se sostiene que combinar protocolos estándar con adaptadores propietarios permite un conjunto
  común de funciones básicas y avanzadas? [La evidencia de §7.2 a §7.6 lo sostiene para ISAPI; falta
  la mitad "protocolo estándar" de la afirmación, pendiente de §7.4].
- El hallazgo de §7.2 (dos APIs incompatibles dentro de la misma marca) no estaba previsto en la
  hipótesis original. ¿La refuerza o la matiza? Se sugiere argumentar que la **refuerza**: si la
  hipótesis dependiera de que "cada marca es internamente consistente", este hallazgo la
  refutaría; como la hipótesis solo exige combinar protocolos y aceptar profundidad desigual, la
  fragmentación intra-marca es una instancia más severa del mismo fenómeno, no una excepción a él.

## 8.3 Cumplimiento de los objetivos específicos

Retomar la tabla de §2.4 y convertir cada fila en un párrafo de conclusión, no en una repetición del
estado. Los objetivos 1, 2, 3, 4, 6 y 7 tienen evidencia suficiente en el capítulo 7 para
redactarse ahora. Los objetivos 5 y 8 dependen de §7.4.

## 8.4 Aporte del trabajo

Retomar el aporte esperado del anteproyecto (§1.4) y confirmar o matizar cada punto con evidencia
del capítulo 7:

- Interoperabilidad básica viable por protocolos estándar — [pendiente de §7.4].
- Unificación profunda de funciones premium requiere integración por marca, **y por modelo dentro
  de la marca** — [sostenido con fuerza por §7.2].
- Arquitectura por adaptadores permite escalar sin acoplar al frontend — [sostenido por §6.1–6.2;
  el frontend nunca conoce el protocolo de origen de una operación].
- La comparación entre marcas puede modelarse formalmente mediante una matriz de capacidades —
  [sostenido por §3.5 y §7.9, con la distinción declarada/verificada como aporte específico no
  anticipado en el anteproyecto original].

## 8.5 Limitaciones del trabajo

Enumerar sin atenuantes, porque una tesis que no reconoce sus límites es menos creíble, no más
prolija:

- El acceso al hardware fue intermitente (red de una oficina, sin control total del investigador
  sobre su disponibilidad), lo cual retrasó la verificación de ONVIF y de la cámara Scati.
- La analítica de IA del domo nunca se observó disparando un evento real durante el desarrollo del
  trabajo (§7.7); la conclusión sobre esa función se basa en evidencia indirecta (declaración de
  capacidades, configuración del canal de notificación), no en un evento observado.
- El trabajo se concentra en Hikvision como caso fuerte, según lo previsto en el anteproyecto; la
  generalización a otros fabricantes se apoya en un solo caso adicional (Scati), sin analítica
  propia que comparar.

## 8.6 Trabajo futuro

- Verificar ONVIF y la analítica de la cámara Scati (si §7.4/§7.8 no cerraron antes de la entrega).
- Ampliar el corredor de experimentos (§7.5) a una corrida sostenida en el tiempo, que permita
  observar si la latencia o la tasa de éxito de una función varían con la carga de la red o con el
  uso prolongado del equipo.
- Explorar si la analítica de IA del domo puede recrearse mediante un mecanismo distinto al
  probado (por ejemplo, exportando e importando la configuración completa del equipo en lugar de
  crear la tarea de a partes).
- Extender el motor de capacidades a un tercer fabricante con analítica propietaria real, para
  confirmar si el patrón de "un adaptador por familia de comportamiento, no por marca" (§6.7) se
  sostiene fuera de Hikvision.
