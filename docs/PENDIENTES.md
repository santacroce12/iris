# Pendientes

Cosas que quedaron para después. Lo más importante para la tesis está arriba.

## Eventos

- [ ] **Fotos en los eventos.** Hoy llegan sin imagen: las cámaras no adjuntan la foto al
      alertStream salvo que se les active "subir imagen de alarma" por evento. Hay que configurarlo
      por API (`/ISAPI/Event/triggers/<evento>-<canal>` y los parámetros de imagen) en la PTZ y en el
      domo, y verificar que el parser las guarde (el soporte de imágenes ya está hecho y testeado).
- [ ] Probar la regla de IA del domo ("manos en alto", `TargetType 5`). En la prueba del 18/09 no
      disparó; su contador quedó en cero. Evaluar bajar umbral de confianza (hoy 800/1000) y
      sensibilidad (hoy 90).
- [ ] Los eventos de `sound_classification` del domo: ver qué sonido clasificó (está en el payload).

## Cámaras y red

- [ ] **Habilitar ONVIF en las dos cámaras** y crear el usuario ONVIF. Sin esto la columna ONVIF de
      la matriz queda vacía y se pierde la comparación estándar vs. propietario.
- [ ] Video del domo en el navegador del usuario: del lado del servidor funciona (MediaMTX lo lee,
      WebRTC y HLS responden). Falta saber qué ve exactamente el usuario para cerrar el tema.
- [ ] El usuario `stmcam` del domo es rechazado por RTSP (401): revisar si existe o sus permisos.
- [ ] La PTZ tiene la zona horaria en +08:00. La plataforma ya lo normaliza, pero conviene
      corregirla en la cámara.
- [ ] Credenciales de la cámara 192.168.239.151 (responde ISAPI pero con otras credenciales).

## Estado que dejamos modificado en las cámaras

- PTZ (192.168.239.189): regla de cruce de línea 1 activa, línea horizontal (150,500)→(850,500),
  filtro persona + vehículo. Respaldo de la configuración original en el scratchpad de la sesión
  del 18/09.
- Domo (192.168.239.101): detección de movimiento encendida (estaba apagada), sensibilidad 80.

## Código

- [ ] 4 advertencias de lint en `frontend/src/features/events/` (estilo de React, no rompen nada).
- [ ] `GET /api/events/{id}` no existe: hoy el detalle se arma con el listado.
- [ ] Endpoint de estadísticas agregadas (hoy los contadores se calculan en el navegador sobre los
      últimos 300 episodios).
