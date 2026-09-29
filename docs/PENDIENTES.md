# Pendientes

Lista larga de cosas sueltas. **Para el plan de trabajo ordenado, ver
[HOJA-DE-RUTA.md](HOJA-DE-RUTA.md)**: ahí está qué se hace con cámaras, qué sin cámaras, y en
qué orden. **El documento de tesis en sí está en [docs/tesis/](tesis/README.md)**.

## Eventos

- [ ] **Fotos en los eventos — replanteado (29/09).** Se revisó en la interfaz de la PTZ: **este
      modelo no tiene una opción para adjuntar la foto al canal que ya escuchamos** ("Notificar al
      software remoto"). Lo único que ofrece es "Cargar en FTP/tarjeta de memoria/NAS", un mecanismo
      distinto. Ver `bitacora-apis.md` §6.6 para el detalle y las dos alternativas posibles: montar
      un servidor FTP propio, o (más simple) que la plataforma pida ella misma un snapshot
      (`GET .../picture`, ya implementado) al abrir cada episodio. Falta decidir cuál, e implementarla.
      Repetir la revisión en el domo por si su modelo sí tiene la opción.
- [ ] **Recrear la tarea de análisis del domo desde su interfaz web** y capturar el pedido que
      manda el navegador. Después de un reinicio la tarea desapareció y no se pudo recrear por
      API (6 variantes, ver `bitacora-apis.md` §5.1). Sin tarea no hay analítica de IA.
- [x] Los eventos de `sound_classification` del domo: ver qué sonido clasificó (está en el
      payload). **27 de 27 eventos capturados desde el 18/09 clasificaron `"gunfire"`** — casi
      seguro un falso positivo recurrente sobre ruido ambiente, no algo real. Ver
      `bitacora-apis.md` §6.8.

## Reglas

- [x] Orientación vertical verificada en las dos cámaras: la PTZ cuenta desde abajo y el domo
      desde arriba (ver `bitacora-apis.md`).
- [x] Zona de la Regla1 del domo restaurada a pantalla completa.
- [x] Editor de reglas sobre la imagen: probado contra la PTZ real (se arrastró un punto en el
      navegador, se guardó, la cámara lo aplicó y se restauró la línea de la demo).
- [ ] La línea 2 de la PTZ quedó con una línea dibujada a mano durante la prueba; borrarla si
      molesta (la línea 1 es la de la demo).
- [ ] Si se cambia el montaje de la PTZ o se activa la rotación de imagen, repetir la verificación
      de orientación.

## Analítica del domo que no dispara

- [ ] El disparador de la Regla1 está vacío (`…/AIRuleConfig/task/<tarea>/channels/1/trigger` →
      `{}`) y el calendario de armado de la app está en `enabled: false`. Falta confirmar si
      HikCentral recibe igual las alarmas por su canal propio.
- [ ] Revisar del lado de HikCentral si llegan eventos de esa cámara y con qué nombre.
- [ ] El parser ya mapea los cuatro tipos de IA (`AIOpenPlatform`, `AIOP_Video`,
      `AIOP_Polling_Snap`, `HEOPCustomEvent`) y la cámara los declara suscribibles, pero todavía
      **no se vio llegar ninguno de estos cuatro** (la tarea de video sigue vacía, §"Analítica del
      domo que no dispara"). Aclaración (29/09): esto no significa que el domo no mande *ningún*
      evento de IA — `sound_classification`, que es un tipo de evento distinto y no depende de la
      tarea de AIOP, sí llegó (27 veces, ver arriba). Queda sin verificar solo lo que depende de
      esa tarea puntual.

## Cámaras y red

- [ ] **Dar de alta la cámara Scati** (27/09: confirmado que hay acceso). Es el caso "otra marca"
      que pedía el cronograma del anteproyecto (Fase 3: "validación de Scati u otra marca
      disponible"). No tiene analítica — es el resultado esperado, no un problema: el propio
      anteproyecto dice que una marca sin API avanzada es un caso comparativo válido. Puede
      resolver ONVIF gratis si lo trae activado de fábrica. Ver Sesión 0 de `HOJA-DE-RUTA.md`.
- [x] **ONVIF habilitado y verificado en la PTZ y en el domo** (29/09), por API en el primer
      intento en las dos: `PUT /ISAPI/System/Network/Integrate` + usuario ONVIF creado.
      `status: online` por los tres protocolos en ambas cámaras. Ver `bitacora-apis.md` §6.5.
      Falta repetirlo en la Scati si se consigue acceso.
- [x] **El domo cambió de IP** (192.168.239.101 → .174, mismo equipo y firmware, reiniciado el
      25/09). Actualizado en la plataforma.
- [ ] **Hallazgo grande (29/09): el domo ahora responde a la analítica clásica** (`/ISAPI/Smart/*`),
      que antes daba `403 notSupport` — confirmado escribiendo una regla real y viendo que se
      aplica. Ver `bitacora-apis.md` §6.7. La plataforma hoy elige una sola familia de reglas por
      cámara (AI Open Platform, por ser más específica) y no ofrece la clásica aunque responda.
      Falta que el motor de reglas pueda mostrar las dos cuando las dos funcionen.
- [ ] Video del domo en el navegador del usuario: del lado del servidor funciona (MediaMTX lo lee,
      WebRTC y HLS responden). Falta saber qué ve exactamente el usuario para cerrar el tema.
- [x] El usuario `stmcam` del domo es rechazado por RTSP (401): revisar si existe o sus permisos.
      **Confirmado por API (29/09): existe, es Operator, y tiene `preview: true` en el canal de
      video — los permisos están bien.** El 401 es una contraseña incorrecta o desconocida, no un
      problema de permisos. Falta la contraseña real para seguir; no se intentó adivinarla.
- [x] **Las dos cámaras tenían la zona horaria en +08:00 (China) y se corrigieron (29/09)**, con
      respaldo y relectura. La plataforma ya normalizaba a UTC así que no afectaba nada
      funcionalmente, pero es una rareza más: el mismo campo `timeZone` necesitó el signo opuesto
      en cada cámara para dar el mismo resultado real (`GMT+3:00:00` en la PTZ,
      `GMT-3:00:00` en el domo). Ver `bitacora-apis.md` §6.8.
- [ ] Credenciales de la cámara 192.168.239.151 (responde ISAPI pero con otras credenciales).

## Estado que dejamos modificado en las cámaras

- PTZ (192.168.239.189): regla de cruce de línea 1 activa, línea horizontal (150,500)→(850,500),
  filtro persona + vehículo. Respaldo de la configuración original en el scratchpad de la sesión
  del 18/09.
- PTZ (192.168.239.189): **ONVIF activado** (estaba apagado) y usuario ONVIF `tesisonvif`
  creado (29/09). Respaldo del `Integrate` original en el scratchpad de esa sesión. Esto queda
  así a propósito, no hay que restaurarlo: es la comparación que necesita la tesis.
- Domo (ahora 192.168.239.174): detección de movimiento encendida (estaba apagada), sensibilidad 80.
- Domo (192.168.239.174): **ONVIF activado** y usuario `tesisonvif` creado (29/09), igual que
  en la PTZ. No hay que restaurarlo.
- Domo (192.168.239.174): **la línea 1 de `/ISAPI/Smart/LineDetection` quedó con coordenadas de
  prueba** (0,2/0,8)–(0,8/0,2), sensibilidad 70, **desactivada** (`enabled: false`, no genera
  alarmas). Se dejó a propósito como evidencia de que la escritura se aplica de verdad; no hace
  falta limpiarla antes de la demo porque está apagada.
- PTZ (192.168.239.189) y Domo (192.168.239.174): **zona horaria corregida de China (UTC+8) a
  Argentina (UTC-3)** (29/09). Respaldo del `/ISAPI/System/time` original de cada una en el
  scratchpad de esa sesión. Cambio intencional y permanente, no hay que restaurarlo.

## Reglas: lo que falta del editor


- [ ] Botón "Probar": después de guardar, marcar en el feed el próximo evento de esa regla.
- [ ] Horario de armado de la regla (`/ISAPI/Event/schedules/...`), hoy queda como esté en la cámara.
- [ ] Vinculación del evento (`/ISAPI/Event/triggers/<evento>-<canal>`): sin notificación "center"
      la regla existe pero no avisa. Hoy se asume que ya está configurada.

## Fase 2 (anteproyecto): capacidades y matriz

- [x] Catálogo de 11 funciones, motor de detección (declarada vs verificada) y página de matriz
      con exportación a CSV.
- [x] Seis funciones comunes por ISAPI: estado, hora, OSD, imagen, movimiento y reinicio.
- [x] Las mismas por ONVIF, escritas y sin verificar (falta habilitar ONVIF en las cámaras).
- [ ] **Verificar la columna ONVIF contra hardware.** Es lo único que falta para cerrar la
      comparación estándar vs. propietario, que es la pregunta del anteproyecto.
- [ ] Pantalla de funciones comunes en el detalle de cámara (hoy la API está, la UI no).
- [ ] Exportar la matriz también a Markdown para pegarla en el documento de la tesis.

## Fase 5 (anteproyecto): evidencia

- [x] **Corredor de experimentos** (`backend/tools/experiments`): N repeticiones de cada función
      por protocolo y cámara, con reconocimiento previo para no colgarse con cámaras
      inalcanzables. Exporta CSV y Markdown a `docs/evidencias/experimentos/<fecha>/`.
      `uv run python -m tools.experiments --repeticiones 30`. 15 tests nuevos (6 unitarios de
      percentiles/export, 9 de integración contra el simulador... en realidad son 3 de
      integración + 6 unitarios, revisar conteo exacto en el commit).
- [x] Primera corrida real hecha (30/09, con el simulador y las 3 cámaras reales inalcanzables
      desde esta red): confirma que el mecanismo de "no alcanzable" no cuelga con cámaras que no
      responden, y que la VPN duplica el timeout como corresponde (8s LAN, 16s la de Sarmiento).
- [ ] Cuando haya cámaras reales, correr de nuevo para tener las latencias de verdad (las de
      ahora son solo del simulador, útiles para probar el mecanismo, no para citar en la tesis).

## Simulador

- [x] Cámara simulada con los tres perfiles (`backend/tools/simulator`), con las rarezas del
      hardware reproducidas y 10 tests.
- [ ] El simulador no habla ONVIF ni RTSP: la prueba de conexión marca esas dos en rojo. Si hace
      falta demostrar el vivo sin cámaras, se puede publicar un archivo de video en MediaMTX.
- [x] Grabador de fixtures (`tools/recorder`): barre ~60 endpoints, sanitiza y deja índice.

## Evidencia para cuando haya acceso al hardware

- [x] Grabador de respuestas: `uv run python -m tools.recorder --host <ip> --clave <clave>`.
- [x] Grabación de video continua por cámara (botón en la pestaña "Vivo"), en segmentos de 10 min.
- [ ] **La grabación de video no se pudo probar de punta a punta**: no hay ffmpeg en la máquina ni
      una cámara accesible, así que solo se verificó que MediaMTX acepte y aplique la configuración
      (`record=true`, `sourceOnDemand=false`). Falta confirmarlo con una cámara real y ver el
      archivo en disco.
- [ ] Vincular las grabaciones con los episodios de eventos por rango de tiempo, para poder abrir
      el video del momento exacto de un evento.
- [ ] Cuando vuelvas a tener las cámaras, en este orden: correr el grabador en las dos, encender
      la grabación de video, y recién entonces hacer las pruebas (cruzar la línea, etc.).

## Código

- [ ] **El backend vuelve a colgarse al recargar (`--reload`) si hay un tab con la pantalla de
      Eventos abierto.** Se creía resuelto (el feed SSE escucha `bus.cerrando`), pero volvió a
      pasar el 29/09 al editar `onvif/system.py` con la pestaña de eventos abierta en el
      navegador: quedó en "Waiting for connections to close" indefinidamente. Hay que revisar el
      orden real en que uvicorn dispara el evento de `lifespan: shutdown` durante un reload
      cuando hay una conexión HTTP todavía abierta — puede que dependa de esperar a que la
      conexión cierre antes de correr el shutdown, lo cual sería un candado circular con nuestro
      propio mecanismo. Mientras tanto: cerrar la pestaña de Eventos antes de tocar el backend,
      o reiniciar el proceso a mano si se cuelga.
- [ ] 4 advertencias de lint en `frontend/src/features/events/` (estilo de React, no rompen nada).
- [ ] `GET /api/events/{id}` no existe: hoy el detalle se arma con el listado.
- [ ] Endpoint de estadísticas agregadas (hoy los contadores se calculan en el navegador sobre los
      últimos 300 episodios).
