# /assets — archivos que debes reemplazar

| Archivo | Qué es | Formato y dimensiones |
|---|---|---|
| `demo.mp4` | Recorrido del producto que se reproduce dentro del marco de laptop del hero. Se reproduce en loop, sin sonido. | MP4 (H.264 + AAC o sin pista de audio), **1600×1000 px** (relación exacta **16:10**), 10–20 s, 30 fps, ≤ 4 MB. Opcional: `demo.webm` con la misma duración para mejor compresión. |
| `demo-poster.jpg` | Primer fotograma que se ve mientras el video carga. | JPG o WebP, **1600×1000 px** (16:10), ≤ 250 KB. |
| `favicon.svg` | Ícono de pestaña. Ya incluido, reemplázalo sólo si cambia la marca. | SVG cuadrado, 32×32 de viewBox. |

## Notas

- La relación **16:10** no es negociable: el marco de laptop usa `aspect-ratio: 16 / 10`.
  Si el video tiene otra relación se recorta con `object-fit: cover`.
- Mientras `demo.mp4` no exista, el hero muestra automáticamente el **mockup del panel
  hecho en HTML/CSS** (mismo encuadre y proporciones). En cuanto el archivo cargue
  correctamente, el video aparece encima sin que haya que tocar nada más.
- Graba el video sin texto legal ni datos reales de candidatos: lo que se vea en pantalla
  es público.
- Fotos de fundadores: si las subes aquí, usa `gabriel.jpg` y `diego.jpg` a **800×800 px**
  (se recortan a 4:3 en la tarjeta) y reemplaza los bloques `ph-box` de la sección
  "Quiénes somos" por `<img src="assets/gabriel.jpg" alt="Gabriel Llanos" />`.
