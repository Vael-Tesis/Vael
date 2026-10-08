import { useRef, useState } from 'react'
import { toast } from 'sonner'

const MAX_MB = 5

export default function FileDrop({ multiple = false, onFiles, hint = 'Arrastra tu PDF aquí o haz clic para seleccionar' }) {
  const inputRef = useRef(null)
  const [over, setOver] = useState(false)

  function procesar(lista) {
    const validos = []
    for (const f of Array.from(lista)) {
      if (f.type !== 'application/pdf') {
        toast.error(`${f.name}: solo se aceptan archivos PDF`)
        continue
      }
      if (f.size > MAX_MB * 1024 * 1024) {
        toast.error(`${f.name}: supera los ${MAX_MB} MB`)
        continue
      }
      validos.push(f)
    }
    if (validos.length) onFiles(multiple ? validos : [validos[0]])
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={e => { e.preventDefault(); setOver(false); procesar(e.dataTransfer.files) }}
      style={{
        border: `1.5px dashed ${over ? 'var(--text-primary)' : 'var(--border-hover)'}`,
        background: over ? 'var(--bg-page)' : 'var(--bg-card)',
        borderRadius: 8, padding: '22px 16px', textAlign: 'center',
        cursor: 'pointer', transition: 'all 150ms ease',
      }}
    >
      <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{hint}</p>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>PDF · máx. {MAX_MB} MB</p>
      <input
        ref={inputRef} type="file" accept="application/pdf"
        multiple={multiple} hidden
        onChange={e => { procesar(e.target.files); e.target.value = '' }}
      />
    </div>
  )
}