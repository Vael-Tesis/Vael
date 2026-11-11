<#
.SYNOPSIS
  Enciende VAEL en AWS (DEP-C-01): base permanente, imágenes del backend y de la Lambda, entorno
  temporal, roles + migraciones + semillas, y publicación del panel y de la landing.
.DESCRIPTION
  El entorno se crea solo para usarlo (demos, E3, sustentación) y se destruye con
  .\scripts\aws-apagar.ps1 (decisión de operación del 2026-10-25). Costo aproximado del entorno
  encendido: 0,09 USD por hora (infra/aws/README.md).

  Corre en Windows PowerShell 5.1 (laptop) y en PowerShell 7 sobre Linux (GitHub Actions, DEP-C-05).
  GEMINI_API_KEY y SEED_PASSWORD se leen de las variables de entorno o, si no están, de
  backend/.env; nunca se imprimen. Con la variable VAEL_ROL_CFN, CloudFormation usa ese rol de
  servicio (infra/aws/acceso.yaml).
.EXAMPLE
  .\scripts\aws-encender.ps1
.EXAMPLE
  .\scripts\aws-encender.ps1 -CorreoAlarmas equipo@ejemplo.com   # ese correo recibe las alarmas (HU-22)
.EXAMPLE
  ./scripts/aws-encender.ps1 -Perfil "" -SoloSiEncendido   # deploy.yml al integrar en main
.EXAMPLE
  .\scripts\aws-encender.ps1 -SoloQwen   # todo el análisis con Qwen, sin esperar a Gemini (DEC-025)
#>
param(
  [string]$Perfil = "vael",
  [string]$Region = "us-east-1",
  [string]$CorreoAlarmas = "",
  [switch]$ConQwen,
  # Usa siempre Qwen (IA_PROVEEDOR=qwen), sin pasar por Gemini; incluye los datos de -ConQwen
  [switch]$SoloQwen,
  # Publica las imágenes y la landing; actualiza el entorno solo si ya está encendido (no lo crea)
  [switch]$SoloSiEncendido
)

$ErrorActionPreference = "Stop"
# La CLI de AWS lee las plantillas con la codificación del sistema en Windows: sin esto, el código
# inline de la Lambda de contacto (DEC-027) se sube con las tildes rotas
$env:AWS_CLI_FILE_ENCODING = "UTF-8"
$env:AWS_PAGER = ""  # sin paginador: el script no debe quedarse esperando una tecla
$raiz = Split-Path $PSScriptRoot -Parent
$inicio = Get-Date
# En Windows PowerShell 5.1, $IsWindows no existe (es $null): ahí también es Windows
$enWindows = ($null -eq $IsWindows) -or $IsWindows
$awsExe = if ($enWindows) { "aws.exe" } else { "aws" }
$perfilArgs = if ($Perfil) { @("--profile", $Perfil) } else { @() }
$rolCfn = if ($env:VAEL_ROL_CFN) { @("--role-arn", $env:VAEL_ROL_CFN) } else { @() }

function Aws {
  & $awsExe @args @perfilArgs --region $Region
  if ($LASTEXITCODE -ne 0) { throw "Falló: aws $($args[0]) $($args[1])" }
}

# Devuelve $null en vez de fallar (para consultar si algo existe)
function AwsOpcional {
  $previa = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $salida = & $awsExe @args @perfilArgs --region $Region 2>$null
  $ok = $LASTEXITCODE -eq 0
  $ErrorActionPreference = $previa
  if ($ok) { return ($salida -join "`n").Trim() } else { return $null }
}

function NuevaClave([int]$largo = 40) {
  $letras = [char[]]"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  $bytes = New-Object byte[] $largo
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  -join ($bytes | ForEach-Object { $letras[$_ % $letras.Length] })
}

# Valor de una variable de entorno o, si no está, de backend/.env ("" si no existe en ninguno)
function LeerEnvOpcional([string]$nombre) {
  $valor = [Environment]::GetEnvironmentVariable($nombre)
  if ($valor) { return $valor.Trim() }
  $archivo = Join-Path $raiz "backend/.env"
  if (-not (Test-Path $archivo)) { return "" }
  $linea = Get-Content $archivo | Where-Object { $_ -match "^$nombre=(.+)$" } | Select-Object -First 1
  if (-not $linea) { return "" }
  return ($linea -replace "^$nombre=", "").Trim()
}

function LeerEnv([string]$nombre) {
  $valor = LeerEnvOpcional $nombre
  if (-not $valor) { throw "Falta $nombre (variable de entorno o backend/.env)" }
  return $valor
}

function Salidas([string]$pila) {
  $json = Aws cloudformation describe-stacks --stack-name $pila --query "Stacks[0].Outputs" --output json | Out-String
  $mapa = @{}
  ($json | ConvertFrom-Json) | ForEach-Object { $mapa[$_.OutputKey] = $_.OutputValue }
  return $mapa
}

function Paso([string]$texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

function PublicarLanding($base) {
  Paso "Landing (www.vael.work)"
  $pendientes = Select-String -Path (Join-Path $raiz "landing/*.html") -Pattern "DATO_PENDIENTE" -List
  if ($pendientes) {
    Write-Warning "La landing tiene datos pendientes ({{DATO_PENDIENTE}}) en: $($pendientes.Filename -join ', '). No se publica."
    return
  }
  Aws s3 sync (Join-Path $raiz "landing") "s3://$($base.BucketLanding)" --delete --exclude "README.md" --exclude "assets/README.md" --exclude "config.js"
  # config.js: URL del formulario de demo (DEC-027); sin ella, la landing abre el correo del visitante
  $config = Join-Path ([System.IO.Path]::GetTempPath()) "vael-landing-config.js"
  $url = if ($base.ContactoUrl) { $base.ContactoUrl } else { "" }
  [System.IO.File]::WriteAllText($config, "window.VAEL_CONTACTO_URL = '$url';`n", (New-Object System.Text.UTF8Encoding($false)))
  Aws s3 cp $config "s3://$($base.BucketLanding)/config.js" --content-type "application/javascript; charset=utf-8" --cache-control "no-cache" | Out-Null
  Remove-Item $config -Force -Confirm:$false
  Aws cloudfront create-invalidation --distribution-id $base.DistribucionLandingId --paths "/*" | Out-Null
}

# --- 1. Base permanente ---
Paso "Base permanente (ECR, sitios y CloudFront)"
$certificado = Aws acm list-certificates --query "CertificateSummaryList[?DomainName=='vael.work' && Status=='ISSUED'].CertificateArn | [0]" --output text
if (-not $certificado -or $certificado -eq "None") { throw "No hay un certificado emitido para vael.work en ACM (us-east-1)" }

$origenSecreto = AwsOpcional ssm get-parameter --name /vael/origen-secreto --with-decryption --query Parameter.Value --output text
if (-not $origenSecreto) {
  $origenSecreto = NuevaClave
  Aws ssm put-parameter --name /vael/origen-secreto --type SecureString --value $origenSecreto | Out-Null
}
Aws cloudformation deploy --stack-name vael-base --template-file (Join-Path $raiz "infra/aws/base.yaml") --capabilities CAPABILITY_IAM @rolCfn `
  --parameter-overrides "CertificadoArn=$certificado" "OrigenSecreto=$origenSecreto" --no-fail-on-empty-changeset
$base = Salidas "vael-base"

# --- 2. Imágenes del backend y de la Lambda ---
Paso "Imagen del backend"
$etiqueta = "$(git -C $raiz rev-parse --short HEAD)-$(Get-Date -Format yyyyMMddHHmm)"
$imagen = "$($base.RepositorioUri):$etiqueta"
docker build --target production -t $imagen (Join-Path $raiz "backend")
if ($LASTEXITCODE -ne 0) { throw "Falló docker build" }
$registro = $base.RepositorioUri.Split("/")[0]
if ($enWindows) {
  # La tubería va por cmd: Windows PowerShell 5.1 altera el texto que pasa a docker y ECR responde
  # 400 (Bad Request) al login
  cmd /c "aws.exe ecr get-login-password $($perfilArgs -join ' ') --region $Region | docker login --username AWS --password-stdin $registro"
} else {
  & $awsExe ecr get-login-password @perfilArgs --region $Region | docker login --username AWS --password-stdin $registro
}
if ($LASTEXITCODE -ne 0) { throw "Falló docker login en ECR" }
docker push $imagen
if ($LASTEXITCODE -ne 0) { throw "Falló docker push" }

Paso "Imagen de la Lambda de análisis (HU-23)"
# --provenance=false: Lambda no acepta índices de imagen con atestaciones
$imagenLambda = "$($base.RepositorioLambdaUri):$etiqueta"
docker build --provenance=false -f (Join-Path $raiz "backend/Dockerfile.lambda") -t $imagenLambda (Join-Path $raiz "backend")
if ($LASTEXITCODE -ne 0) { throw "Falló docker build de la Lambda" }
docker push $imagenLambda
if ($LASTEXITCODE -ne 0) { throw "Falló docker push de la Lambda" }

# --- 3. Entorno temporal ---
$plantilla = Join-Path $raiz "infra/aws/entorno.yaml"
$existe = AwsOpcional cloudformation describe-stacks --stack-name vael-entorno --query "Stacks[0].StackStatus" --output text
if ($SoloSiEncendido -and -not $existe) {
  # Entorno apagado: las imágenes quedan listas en ECR para el próximo encendido; no se crea nada
  PublicarLanding $base
  Write-Host "`nEntorno apagado: imágenes $etiqueta publicadas en ECR y landing actualizada. No se encendió nada." -ForegroundColor Green
  return
}
Paso "Entorno temporal (red, RDS, ALB, ECS, SQS y Lambda); la primera vez tarda unos 15 minutos"
# Sin -CorreoAlarmas, las alarmas existen igual y se ven en CloudWatch, pero no notifican a nadie
$correo = @(); if ($CorreoAlarmas) { $correo = @("CorreoAlarmas=$CorreoAlarmas") }
# IA de respaldo (DEC-025): solo con -ConQwen se pasan a la pila los datos de Qwen de backend/.env
# (la clave va a Secrets Manager). El Qwen de Tecsup está en una IP privada que AWS no alcanza: sin
# -ConQwen, el entorno usa solo Gemini y no espera a un servidor inalcanzable.
# Con -SoloQwen, el análisis va siempre a Qwen (IA_PROVEEDOR=qwen): útil cuando Gemini está saturado
# o sin cuota, porque los reintentos de Gemini demoran cada análisis de 2 a 3 minutos.
$ia = @("IaProveedor=gemini", "IaRespaldo=", "QwenBaseUrl=", "QwenModelo=", "QwenApiKey=")
if ($ConQwen -or $SoloQwen) {
  $proveedor = if ($SoloQwen) { "qwen" } else { "gemini" }
  $ia = @("IaProveedor=$proveedor", "IaRespaldo=qwen", "QwenBaseUrl=$(LeerEnvOpcional 'QWEN_BASE_URL')",
    "QwenModelo=$(LeerEnvOpcional 'QWEN_MODEL')", "QwenApiKey=$(LeerEnvOpcional 'QWEN_API_KEY')")
}
if ($existe) {
  # Entorno ya encendido: solo cambia la imagen; el resto conserva sus valores
  Aws cloudformation deploy --stack-name vael-entorno --template-file $plantilla --capabilities CAPABILITY_IAM @rolCfn `
    --parameter-overrides "ImagenUri=$imagen" "ImagenLambdaUri=$imagenLambda" @correo @ia --no-fail-on-empty-changeset
} else {
  $prefijos = Aws ec2 describe-managed-prefix-lists --filters "Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing" `
    --query "PrefixLists[0].PrefixListId" --output text
  Aws cloudformation deploy --stack-name vael-entorno --template-file $plantilla --capabilities CAPABILITY_IAM @rolCfn `
    --parameter-overrides "ImagenUri=$imagen" "ImagenLambdaUri=$imagenLambda" "PrefixListCloudFront=$prefijos" "OrigenSecreto=$origenSecreto" `
      "ClaveJwt=$(NuevaClave 64)" "ClaveInterna=$(NuevaClave 64)" "PassMaestra=$(NuevaClave 32)" `
      "PassOwner=$(NuevaClave 32)" "PassApp=$(NuevaClave 32)" "PassSystem=$(NuevaClave 32)" `
      "GeminiApiKey=$(LeerEnv 'GEMINI_API_KEY')" "SeedPassword=$(LeerEnv 'SEED_PASSWORD')" @correo @ia
}
$entorno = Salidas "vael-entorno"

Paso "CloudFront apunta /api al nuevo balanceador"
Aws cloudformation deploy --stack-name vael-base --template-file (Join-Path $raiz "infra/aws/base.yaml") --capabilities CAPABILITY_IAM @rolCfn `
  --parameter-overrides "OrigenApi=$($entorno.BalanceadorDns)" --no-fail-on-empty-changeset

# --- 4. Roles, migraciones y semillas ---
Paso "Roles de la base (DEC-010), migraciones y datos semilla (doc 13)"
$red = "awsvpcConfiguration={subnets=[$($entorno.SubredPublicaA)],securityGroups=[$($entorno.GrupoApp)],assignPublicIp=ENABLED}"
$tarea = Aws ecs run-task --cluster $entorno.Cluster --task-definition $entorno.TareaPreparar --launch-type FARGATE `
  --network-configuration $red --query "tasks[0].taskArn" --output text
Aws ecs wait tasks-stopped --cluster $entorno.Cluster --tasks $tarea
$codigo = Aws ecs describe-tasks --cluster $entorno.Cluster --tasks $tarea --query "tasks[0].containers[0].exitCode" --output text
Aws logs tail /ecs/vael --log-stream-name-prefix preparar --since 30m
if ($codigo -ne "0") { throw "La preparación de la base terminó con código $codigo (ver el log de arriba)" }

# --- 5. Panel Admin y landing ---
Paso "Panel Admin (app.vael.work)"
Push-Location (Join-Path $raiz "frontend")
try {
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "Falló el build del frontend" }
} finally { Pop-Location }
Aws s3 sync (Join-Path $raiz "frontend/dist") "s3://$($base.BucketApp)" --delete
Aws s3 cp (Join-Path $raiz "frontend/dist/index.html") "s3://$($base.BucketApp)/index.html" --cache-control "no-cache"
Aws cloudfront create-invalidation --distribution-id $base.DistribucionAppId --paths "/*" | Out-Null

PublicarLanding $base

$minutos = [math]::Round(((Get-Date) - $inicio).TotalMinutes)
Write-Host "`nVAEL encendido en $minutos min." -ForegroundColor Green
Write-Host "  Panel:   https://app.vael.work"
Write-Host "  Landing: https://www.vael.work"
Write-Host "  Registros CNAME en GoDaddy (una sola vez): app -> $($base.DistribucionAppDominio) ; www -> $($base.DistribucionLandingDominio)"
Write-Host "  Costo aproximado: 0,09 USD por hora. Al terminar: .\scripts\aws-apagar.ps1" -ForegroundColor Yellow
