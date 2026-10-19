# El documento de tesis

Esto es el documento en sí — no notas de trabajo como la bitácora o el relevamiento, sino los
capítulos que se entregan y se defienden. Está en Markdown, capítulo por capítulo, para poder
editarlo con el resto del proyecto y llevar el historial en git. Cuando esté estable se pasa a
Word con el formato que pida la facultad.

**Principio de redacción**: todo lo que dice "verificado" o da un número concreto sale de la
bitácora, del relevamiento o de una corrida real de la plataforma — nunca se inventa un dato para
rellenar un capítulo. Donde falta evidencia, el capítulo lo dice explícitamente en vez de
disimularlo.

## Estado de cada capítulo

| # | Capítulo | Estado | Depende de |
|---|---|---|---|
| — | [Glosario de términos técnicos](00-glosario.md) | 🟡 Borrador completo | — |
| 1 | [Introducción](01-introduccion.md) | 🟡 Borrador completo | — |
| 2 | [Objetivos y alcance](02-objetivos-alcance.md) | 🟡 Borrador completo | — |
| 3 | [Marco teórico](03-marco-teorico.md) | 🟡 Borrador completo | — |
| 4 | [Estado del arte](04-estado-del-arte.md) | 🟡 Borrador completo | — |
| 5 | [Metodología](05-metodologia.md) | 🟡 Borrador completo | — |
| 6 | [Arquitectura e implementación](06-arquitectura-implementacion.md) | 🟡 Borrador completo | — |
| 7 | [Resultados](07-resultados.md) | 🟠 Parcial: falta **otra marca** (§7.8) | Acceso a una cámara que no sea Hikvision |
| 8 | [Conclusiones](08-conclusiones.md) | 🟡 Borrador completo (29/09) | — |
| 9 | [Bibliografía](09-bibliografia.md) | 🟡 Borrador, crece con las citas que se agreguen | — |

🟡 = escrito, listo para que Luca lo lea y corrija estilo/énfasis. 🟠 = escrito hasta donde da la
evidencia actual, con huecos marcados. 🔴 = todavía no se puede escribir en serio.

## Cómo se completa lo que falta

Al 9/10/2026 lo que le falta al capítulo 7 es **una cámara que no sea Hikvision** (§7.8).

Ojo con no confundir dos cosas que antes iban juntas en la Scati:

- **El caso "sin analítica"** ya está cubierto: el 9/10 se dio de alta una **DS-2CD1023G2-I**
  (Value, `192.168.1.64`), que no tiene analítica de ningún tipo — `VCAResource` da
  `403 notSupport`, `SmartCap` declara todo en `false` salvo ROI, y `triggersCap` solo trae
  movimiento y sabotaje. Es el cuarto escenario de cámara y el contraste de gama que pedía el
  anteproyecto.
- **El caso "otra marca" sigue abierto**, y es el más importante de los dos: ONVIF está
  verificado únicamente contra Hikvision. El argumento del capítulo 8 es "estándar contra
  propietario", y el valor del estándar es funcionar entre fabricantes distintos — que es
  justo lo que todavía no se probó. Sirve la Scati o cualquier otra marca. Todo lo demás que dependía de
hardware ya cerró: ONVIF verificado en las dos Hikvision (§7.4), la corrida real de experimentos en
las dos (§7.5 y §7.5.1), y la analítica del domo documentada como resultado negativo con un hallazgo
adicional relevante — que la misma cámara empezó a responder también a la analítica clásica
(§7.2.1, §7.7).

El capítulo 8 ya está escrito sobre esa base. Cuando se consiga acceso a la Scati, hay que: agregar
su columna a la matriz de §7.9, completar §7.8, y revisar si el capítulo 8 necesita algún ajuste
menor (no debería cambiar la síntesis general, porque la Scati es un caso de contraste ya previsto,
no una pieza de la que dependa la respuesta a la pregunta de investigación). Los capítulos 1 a 6 no
dependen de las cámaras y no deberían cambiar salvo detalle de redacción.

## Qué le falta a este documento y no es responsabilidad mía completar

- **Portada con los datos formales** (institución, carrera, cátedra, director, fecha de defensa):
  no los tengo. Dejé un marcador en el propio documento.
- **Formato exacto que pida la facultad** (interlineado, citas APA/IEEE/Vancouver, numeración):
  ningún archivo que encontré en tu máquina lo especifica. Si tenés una guía de la facultad,
  pasámela y ajusto todo de una.
- **Revisión de estilo en primera persona vs. impersonal**: escribí en impersonal
  ("se desarrolló", "se verificó"), que es lo más común en tesis de ingeniería en español, pero
  cambialo si tu facultad pide otra cosa.
