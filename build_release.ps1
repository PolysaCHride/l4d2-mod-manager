param(
    [string]$Version = "",
    # legacy = PySide6 旧栈；web = pywebview + WebView2 新栈（主线）
    [ValidateSet("legacy", "web", "both")]
    [string]$Target = "web",
    # 跳过打包，只校验现有产物（用于 CI 的 verify 阶段）
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot "release"))
$buildDir = [IO.Path]::GetFullPath((Join-Path $projectRoot "build"))
$rawDistDir = [IO.Path]::GetFullPath((Join-Path $releaseRoot ".build"))
$versionInfo = Join-Path $projectRoot "packaging\version_info.txt"

# 两套栈的产物名必须不同 —— 同名会静默互相覆盖（见 HANDOFF §6.7）。
# 变量名不要叫 $stacks：PowerShell 变量名不区分大小写，
# 会和下面 main 段里同名的 $stacks（目标数组）互相覆盖。
$STACK_CONFIG = @{
    legacy = @{
        Spec     = "L4D2ModManager.spec"
        Product  = "L4D2 Mod Manager"
        Suffix   = ""
        Entry    = "main.py"
    }
    web    = @{
        Spec     = "L4D2ModManagerWeb.spec"
        Product  = "L4D2 Mod Manager (WebUI)"
        Suffix   = "-web"
        Entry    = "main_web.py"
    }
}

function Assert-InRelease([string]$Path) {
    $prefix = $releaseRoot.TrimEnd("\") + "\"
    if (-not $Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "拒绝操作 release 目录之外的路径: $Path"
    }
}

# 从 version_info.txt 读主版本号，避免版本号在三个地方各写一遍。
function Get-ProjectVersion {
    $text = Get-Content -LiteralPath $versionInfo -Raw
    $m = [regex]::Match($text, 'filevers=\((\d+),\s*(\d+),\s*(\d+)')
    if (-not $m.Success) {
        throw "无法从 packaging/version_info.txt 解析版本号"
    }
    return "$($m.Groups[1].Value).$($m.Groups[2].Value).$($m.Groups[3].Value)"
}

# 7-Zip 是必需组件：干净 clone 里 third_party/7zip/ 不存在（被 gitignore 忽略），
# 必须显式确保它存在，否则打出的包缺 7z.exe，用户导入压缩包会全部失败。
function Assert-7Zip {
    $fetchZip = Join-Path $projectRoot "packaging\fetch_7zip.ps1"
    if (-not (Test-Path -LiteralPath $fetchZip -PathType Leaf)) {
        throw "缺少 packaging/fetch_7zip.ps1，无法确保 7-Zip 组件"
    }
    & $fetchZip
    if ($LASTEXITCODE -ne 0) {
        throw "获取 7-Zip 组件失败，退出码: $LASTEXITCODE"
    }
    $zipDir = Join-Path $projectRoot "third_party\7zip"
    foreach ($name in @("7z.exe", "7z.dll", "License.txt")) {
        if (-not (Test-Path -LiteralPath (Join-Path $zipDir $name) -PathType Leaf)) {
            throw "third_party/7zip 缺少必需文件: $name"
        }
    }
}

# 校验一个已打好的包：必须含 7-Zip，且不能夹带运行时数据与文档文件。
function Test-Package([string]$Dir, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Dir -PathType Container)) {
        throw "[$Label] 打包产物不存在: $Dir"
    }

    $bundledZip = Join-Path $Dir "_internal\7zip"
    foreach ($name in @("7z.exe", "7z.dll", "License.txt")) {
        if (-not (Test-Path -LiteralPath (Join-Path $bundledZip $name) -PathType Leaf)) {
            throw "[$Label] 发布包缺少 7-Zip 组件文件: $name"
        }
    }

    # The app creates this directory on first run. It can contain the local game
    # path, mod list and settings, so it must never be included in a public build.
    $runtimeDataDir = Join-Path $Dir "data"
    if (Test-Path -LiteralPath $runtimeDataDir) {
        Assert-InRelease $runtimeDataDir
        Remove-Item -LiteralPath $runtimeDataDir -Recurse -Force
    }

    # 发行包只保留运行所需的程序与组件；README、许可/声明、更新日志、预览图
    # 等文档类文件随仓库分发，不进入 release 目录和最终 zip。
    $forbidden = @(
        "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md",
        "image.png", "image-1.png", "image-2.png", "image-3.png")
    foreach ($name in $forbidden) {
        if (Test-Path -LiteralPath (Join-Path $Dir $name)) {
            throw "[$Label] 发布包包含不应分发的文件: $name"
        }
    }
    $stray = @(Get-ChildItem -LiteralPath $Dir -File |
        Where-Object { $_.Extension -match '^\.(md|png|jpe?g|webp|txt)$' })
    if ($stray.Count -gt 0) {
        throw "[$Label] 发布包顶层包含非功能性文件: $($stray.Name -join ', ')"
    }
}

function New-Release([string]$Stack, [string]$Ver) {
    if (-not $STACK_CONFIG.ContainsKey($Stack)) { throw "未知的打包目标: $Stack" }
    $cfg = $STACK_CONFIG[$Stack]

    $packageName = "L4D2 Mod Manager-v$Ver-win64$($cfg.Suffix)"
    $packageDir = [IO.Path]::GetFullPath((Join-Path $releaseRoot $packageName))
    $zipPath = [IO.Path]::GetFullPath((Join-Path $releaseRoot "$packageName.zip"))
    $rawPackageDir = [IO.Path]::GetFullPath((Join-Path $rawDistDir $cfg.Product))
    $specPath = Join-Path $projectRoot $cfg.Spec

    Write-Host ""
    Write-Host "=== 打包 [$Stack] $packageName ===" -ForegroundColor Cyan

    if (-not (Test-Path -LiteralPath $specPath -PathType Leaf)) {
        throw "缺少 spec 文件: $specPath"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $cfg.Entry) -PathType Leaf)) {
        throw "缺少入口文件: $($cfg.Entry)"
    }

    Assert-InRelease $rawDistDir
    Assert-InRelease $packageDir
    Assert-InRelease $zipPath

    if (-not $VerifyOnly) {
        # --clean 会清掉 build 目录；每个栈单独一个 workpath，避免互相清缓存。
        $stackBuildDir = Join-Path $buildDir $Stack
        & $python -m PyInstaller --noconfirm --clean `
            --distpath $rawDistDir --workpath $stackBuildDir $specPath
        if ($LASTEXITCODE -ne 0) {
            throw "[$Stack] PyInstaller 打包失败，退出码: $LASTEXITCODE"
        }
        if (-not (Test-Path -LiteralPath $rawPackageDir -PathType Container)) {
            throw "[$Stack] PyInstaller 未生成预期目录: $rawPackageDir"
        }
        if (Test-Path -LiteralPath $packageDir) {
            Remove-Item -LiteralPath $packageDir -Recurse -Force
        }
        Move-Item -LiteralPath $rawPackageDir -Destination $packageDir
    }

    Test-Package $packageDir $Stack

    if ($VerifyOnly) {
        Write-Host "  校验通过（未重新打包）: $packageDir" -ForegroundColor Green
        return
    }

    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal

    $sizeMB = [math]::Round((Get-ChildItem -LiteralPath $packageDir -Recurse -File |
        Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    $zipMB = [math]::Round((Get-Item -LiteralPath $zipPath).Length / 1MB, 1)

    Write-Host "  Release 已生成:" -ForegroundColor Green
    Write-Host "    目录: $packageDir ($sizeMB MB)"
    Write-Host "    ZIP : $zipPath ($zipMB MB)"
}

# ---------------------------------------------------------------- main

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "未找到项目虚拟环境: $python"
}

if (-not $Version) {
    $Version = Get-ProjectVersion
    Write-Host "版本号取自 packaging/version_info.txt: $Version"
}

if (-not (Test-Path -LiteralPath $releaseRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $releaseRoot | Out-Null
}

# 7-Zip 先备好，再进构建。spec 里也有一道同样的检查（双保险）。
Assert-7Zip

$stacks = switch ($Target) {
    "legacy" { @("legacy") }
    "web"    { @("web") }
    "both"   { @("legacy", "web") }
}

foreach ($stack in $stacks) {
    New-Release $stack $Version
}

if (Test-Path -LiteralPath $rawDistDir) {
    Remove-Item -LiteralPath $rawDistDir -Recurse -Force
}

Write-Host ""
Write-Host "全部完成（$($stacks -join ', ')）。" -ForegroundColor Green
