<#
.SYNOPSIS
  Apaga VAEL en AWS (DEP-C-01): destruye el entorno temporal (RDS, ALB, ECS, red, CV) y deja el
  panel mostrando un aviso. Se conservan la base permanente (ECR, sitios, CloudFront) y el
  certificado, que no tienen costo fijo; la landing sigue publicada.
.EXAMPLE
  .\scripts\aws-apagar.ps1
#>
param([string]$Perfil = "vael", [string]$Region = "us-east-1")

$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""  # sin paginador: el script no debe quedarse esperando una tecla
$raiz = Split-Path $PSScriptRoot -Parent

function Aws {
  & aws.exe @args --profile $Perfil --region $Region
  if ($LASTEXITCODE -ne 0) { throw "Falló: aws $($args[0]) $($args[1])" }
}

function AwsOpcional {
  $previa = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $salida = & aws.exe @args --profile $Perfil --region $Region 2>$null
  $ok = $LASTEXITCODE -eq 0
  $ErrorActionPreference = $previa
  if ($ok) { return ($salida -join "`n").Trim() } else { return $null }
}

$bucketArchivos = AwsOpcional cloudformation describe-stacks --stack-name vael-entorno `
  --query "Stacks[0].Outputs[?OutputKey=='BucketArchivos'].OutputValue | [0]" --output text
if ($bucketArchivos) {
  Write-Host "== Vaciando el bucket de los CV y destruyendo el entorno (unos 10 minutos)" -ForegroundColor Cyan
  # Los CV son datos de prueba del entorno temporal: se borran con él
  Aws s3 rm "s3://$bucketArchivos" --recursive | Out-Null
  Aws cloudformation delete-stack --stack-name vael-entorno
  Aws cloudformation wait stack-delete-complete --stack-name vael-entorno
} else {
  Write-Host "El entorno temporal ya estaba apagado."
}

$bucketApp = AwsOpcional cloudformation describe-stacks --stack-name vael-base `
  --query "Stacks[0].Outputs[?OutputKey=='BucketApp'].OutputValue | [0]" --output text
if ($bucketApp) {
  Write-Host "== El panel muestra el aviso de entorno apagado" -ForegroundColor Cyan
  Aws cloudformation deploy --stack-name vael-base --template-file (Join-Path $raiz "infra\aws\base.yaml") `
    --parameter-overrides "OrigenApi=api-apagada.vael.work" --no-fail-on-empty-changeset
  Aws s3 rm "s3://$bucketApp" --recursive | Out-Null
  Aws s3 cp (Join-Path $raiz "infra\aws\apagado.html") "s3://$bucketApp/index.html" --cache-control "no-cache" | Out-Null
  $distribucion = Aws cloudformation describe-stacks --stack-name vael-base `
    --query "Stacks[0].Outputs[?OutputKey=='DistribucionAppId'].OutputValue | [0]" --output text
  Aws cloudfront create-invalidation --distribution-id $distribucion --paths "/*" | Out-Null
}

Write-Host "`nVAEL apagado. Sin costo por hora; sigue publicada la landing." -ForegroundColor Green
