<#
.SYNOPSIS
  Enciende VAEL en AWS (DEP-C-01): base permanente, imagen del backend, entorno temporal,
  roles + migraciones + semillas, y publicación del panel y de la landing.
.DESCRIPTION
  El entorno se crea solo para usarlo (demos, E3, sustentación) y se destruye con
  .\scripts\aws-apagar.ps1 (decisión de operación del 2026-10-25). Costo aproximado del entorno
  encendido: 0,09 USD por hora (infra/aws/README.md).
  Lee GEMINI_API_KEY y SEED_PASSWORD de backend/.env; nunca los imprime.
.EXAMPLE
  .\scripts\aws-encender.ps1
#>
param([string]$Perfil = "vael", [string]$Region = "us-east-1")

$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""  # sin paginador: el script no debe quedarse esperando una tecla
$raiz = Split-Path $PSScriptRoot -Parent
$inicio = Get-Date

function Aws {
  & aws @args --profile $Perfil --region $Region
  if ($LASTEXITCODE -ne 0) { throw "Falló: aws $($args[0]) $($args[1])" }
}

# Devuelve $null en vez de fallar (para consultar si algo existe)
function AwsOpcional {
  $previa = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $salida = & aws @args --profile $Perfil --region $Region 2>$null
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

function LeerEnv([string]$nombre) {
  $linea = Get-Content (Join-Path $raiz "backend\.env") | Where-Object { $_ -match "^$nombre=(.+)$" } | Select-Object -First 1
  if (-not $linea) { throw "Falta $nombre en backend/.env" }
  return ($linea -replace "^$nombre=", "").Trim()
}

function Salidas([string]$pila) {
  $json = Aws cloudformation describe-stacks --stack-name $pila --query "Stacks[0].Outputs" --output json | Out-String
  $mapa = @{}
  ($json | ConvertFrom-Json) | ForEach-Object { $mapa[$_.OutputKey] = $_.OutputValue }
  return $mapa
}

function Paso([string]$texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# --- 1. Base permanente ---
Paso "Base permanente (ECR, sitios y CloudFront)"
$certificado = Aws acm list-certificates --query "CertificateSummaryList[?DomainName=='vael.work' && Status=='ISSUED'].CertificateArn | [0]" --output text
if (-not $certificado -or $certificado -eq "None") { throw "No hay un certificado emitido para vael.work en ACM (us-east-1)" }

$origenSecreto = AwsOpcional ssm get-parameter --name /vael/origen-secreto --with-decryption --query Parameter.Value --output text
if (-not $origenSecreto) {
  $origenSecreto = NuevaClave
  Aws ssm put-parameter --name /vael/origen-secreto --type SecureString --value $origenSecreto | Out-Null
}
Aws cloudformation deploy --stack-name vael-base --template-file (Join-Path $raiz "infra\aws\base.yaml") `
  --parameter-overrides "CertificadoArn=$certificado" "OrigenSecreto=$origenSecreto" --no-fail-on-empty-changeset
$base = Salidas "vael-base"

# --- 2. Imagen del backend ---
Paso "Imagen del backend"
$etiqueta = "$(git -C $raiz rev-parse --short HEAD)-$(Get-Date -Format yyyyMMddHHmm)"
$imagen = "$($base.RepositorioUri):$etiqueta"
docker build --target production -t $imagen (Join-Path $raiz "backend")
if ($LASTEXITCODE -ne 0) { throw "Falló docker build" }
$registro = $base.RepositorioUri.Split("/")[0]
Aws ecr get-login-password | docker login --username AWS --password-stdin $registro
if ($LASTEXITCODE -ne 0) { throw "Falló docker login en ECR" }
docker push $imagen
if ($LASTEXITCODE -ne 0) { throw "Falló docker push" }

# --- 3. Entorno temporal ---
Paso "Entorno temporal (red, RDS, ALB, ECS); la primera vez tarda unos 15 minutos"
$plantilla = Join-Path $raiz "infra\aws\entorno.yaml"
$existe = AwsOpcional cloudformation describe-stacks --stack-name vael-entorno --query "Stacks[0].StackStatus" --output text
if ($existe) {
  # Entorno ya encendido: solo cambia la imagen; el resto conserva sus valores
  Aws cloudformation deploy --stack-name vael-entorno --template-file $plantilla --capabilities CAPABILITY_IAM `
    --parameter-overrides "ImagenUri=$imagen" --no-fail-on-empty-changeset
} else {
  $prefijos = Aws ec2 describe-managed-prefix-lists --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing `
    --query "PrefixLists[0].PrefixListId" --output text
  Aws cloudformation deploy --stack-name vael-entorno --template-file $plantilla --capabilities CAPABILITY_IAM `
    --parameter-overrides "ImagenUri=$imagen" "PrefixListCloudFront=$prefijos" "OrigenSecreto=$origenSecreto" `
      "ClaveJwt=$(NuevaClave 64)" "ClaveInterna=$(NuevaClave 64)" "PassMaestra=$(NuevaClave 32)" `
      "PassOwner=$(NuevaClave 32)" "PassApp=$(NuevaClave 32)" "PassSystem=$(NuevaClave 32)" `
      "GeminiApiKey=$(LeerEnv 'GEMINI_API_KEY')" "SeedPassword=$(LeerEnv 'SEED_PASSWORD')"
}
$entorno = Salidas "vael-entorno"

Paso "CloudFront apunta /api al nuevo balanceador"
Aws cloudformation deploy --stack-name vael-base --template-file (Join-Path $raiz "infra\aws\base.yaml") `
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
Aws s3 sync (Join-Path $raiz "frontend\dist") "s3://$($base.BucketApp)" --delete
Aws s3 cp (Join-Path $raiz "frontend\dist\index.html") "s3://$($base.BucketApp)/index.html" --cache-control "no-cache"
Aws cloudfront create-invalidation --distribution-id $base.DistribucionAppId --paths "/*" | Out-Null

Paso "Landing (www.vael.work)"
$pendientes = Select-String -Path (Join-Path $raiz "landing\*.html") -Pattern "DATO_PENDIENTE" -List
if ($pendientes) {
  Write-Warning "La landing tiene datos pendientes ({{DATO_PENDIENTE}}) en: $($pendientes.Filename -join ', '). No se publica."
} else {
  Aws s3 sync (Join-Path $raiz "landing") "s3://$($base.BucketLanding)" --delete
  Aws cloudfront create-invalidation --distribution-id $base.DistribucionLandingId --paths "/*" | Out-Null
}

$minutos = [math]::Round(((Get-Date) - $inicio).TotalMinutes)
Write-Host "`nVAEL encendido en $minutos min." -ForegroundColor Green
Write-Host "  Panel:   https://app.vael.work"
Write-Host "  Landing: https://www.vael.work"
Write-Host "  Registros CNAME en GoDaddy (una sola vez): app -> $($base.DistribucionAppDominio) ; www -> $($base.DistribucionLandingDominio)"
Write-Host "  Costo aproximado: 0,09 USD por hora. Al terminar: .\scripts\aws-apagar.ps1" -ForegroundColor Yellow
