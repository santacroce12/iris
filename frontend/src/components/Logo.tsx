// Iris: tres arcos con los colores de ISAPI, ONVIF y RTSP que forman un solo ojo.
// Es el mismo dibujo que public/favicon.svg; si se cambia uno, cambiar el otro.
const arcs = ['var(--color-isapi)', 'var(--color-onvif)', 'var(--color-rtsp)']

export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={className}>
      <g transform="rotate(-90 16 16)">
        {arcs.map((color, i) => (
          <circle
            key={color}
            cx="16"
            cy="16"
            r="12"
            stroke={color}
            strokeWidth="4"
            pathLength="300"
            strokeDasharray="88 212"
            strokeDashoffset={-100 * i - 6}
          />
        ))}
      </g>
      <circle cx="16" cy="16" r="5.5" fill="var(--color-accent)" />
      <circle cx="18" cy="14" r="1.6" fill="var(--color-bg)" opacity="0.85" />
    </svg>
  )
}
