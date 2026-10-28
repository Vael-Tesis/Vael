<#
.SYNOPSIS
  Copia los documentos de diseño descargados del Drive a docs/diseno/ con el encabezado de DEC-019.
.PARAMETER Origen
  Carpeta donde están los .md descargados del Drive (por defecto, Descargas).
.EXAMPLE
  .\scripts\sincronizar-diseno.ps1
  .\scripts\sincronizar-diseno.ps1 -Origen "C:\temp\drive"
#>
param([string]$Origen = "$env:USERPROFILE\Downloads")

$docs = @(
  "05_modelos_bd.md", "06_api_endpoints.md", "07_flujo_proceso.md", "08_servicios_negocio.md",
  "13_datos_semilla.md", "14_plan_metricas.md", "15_matriz_admin_y_endpoints.md", "16_requerimientos_admin.md"
)
$destino = Join-Path $PSScriptRoot "..\docs\diseno"
New-Item -ItemType Directory -Force -Path $destino | Out-Null
$fecha = Get-Date -Format "yyyy-MM-dd"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$faltan = 0

foreach ($d in $docs) {
  $src = Join-Path $Origen $d
  if (-not (Test-Path $src)) { Write-Warning "No se encontró $src"; $faltan++; continue }
  $texto = [System.IO.File]::ReadAllText($src, $utf8)
  $m = [regex]::Match($texto, '\|\s*Versi.n\s*\|\s*([^|]+?)\s*\|')
  $version = if ($m.Success) { $m.Groups[1].Value } else { "sin versión" }
  $encabezado = "> COPIA del documento del Drive ``VAEL/Docs/$d``, versión $version, copiada el $fecha.`n" +
                "> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.`n`n"
  [System.IO.File]::WriteAllText((Join-Path $destino $d), $encabezado + $texto, $utf8)
  Write-Host "OK  $d  (versión $version)"
}

if ($faltan -gt 0) { Write-Warning "$faltan documento(s) sin copiar. Descárgalos del Drive y vuelve a ejecutar."; exit 1 }
Write-Host "Listo: $($docs.Count) documentos en docs/diseno/"
