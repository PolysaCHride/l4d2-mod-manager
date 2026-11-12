param(
    [string]$Version = "1.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot "release"))
$buildDir = [IO.Path]::GetFullPath((Join-Path $projectRoot "build"))
$rawDistDir = [IO.Path]::GetFullPath((Join-Path $releaseRoot ".build"))
$packageName = "L4D2 Mod Manager-v$Version-win64"
$packageDir = [IO.Path]::GetFullPath((Join-Path $releaseRoot $packageName))
$zipPath = [IO.Path]::GetFullPath((Join-Path $releaseRoot "$packageName.zip"))
$rawPackageDir = [IO.Path]::GetFullPath((Join-Path $rawDistDir "L4D2 Mod Manager"))

function Assert-InRelease([string]$Path) {
    $prefix = $releaseRoot.TrimEnd("\") + "\"
    if (-not $Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "拒绝操作 release 目录之外的路径: $Path"
    }
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "未找到项目虚拟环境: $python"
}

Assert-InRelease $rawDistDir
Assert-InRelease $packageDir
Assert-InRelease $zipPath

if (-not (Test-Path -LiteralPath $releaseRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $releaseRoot | Out-Null
}

& $python -m PyInstaller --noconfirm --clean `
    --distpath $rawDistDir --workpath $buildDir `
    (Join-Path $projectRoot "L4D2ModManager.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 打包失败，退出码: $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $rawPackageDir -PathType Container)) {
    throw "PyInstaller 未生成预期目录: $rawPackageDir"
}

if (Test-Path -LiteralPath $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Move-Item -LiteralPath $rawPackageDir -Destination $packageDir

# The app creates this directory on first run. It can contain the local game
# path, mod list and settings, so it must never be included in a public build.
$runtimeDataDir = Join-Path $packageDir "data"
Assert-InRelease $runtimeDataDir
if (Test-Path -LiteralPath $runtimeDataDir) {
    Remove-Item -LiteralPath $runtimeDataDir -Recurse -Force
}

foreach ($name in @(
        "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md",
        "image.png", "image-1.png", "image-2.png", "image-3.png")) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $name) `
        -Destination (Join-Path $packageDir $name)
}
Remove-Item -LiteralPath $rawDistDir -Recurse -Force

Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal

$sizeMB = [math]::Round((Get-ChildItem -LiteralPath $packageDir -Recurse -File |
    Measure-Object -Property Length -Sum).Sum / 1MB, 1)
$zipMB = [math]::Round((Get-Item -LiteralPath $zipPath).Length / 1MB, 1)

Write-Host ""
Write-Host "Release 已生成:" -ForegroundColor Green
Write-Host "  目录: $packageDir ($sizeMB MB)"
Write-Host "  ZIP : $zipPath ($zipMB MB)"
