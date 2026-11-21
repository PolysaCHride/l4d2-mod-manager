param(
    [string]$Version = "",
    # web = pywebview + WebView2 新界面，**唯一发布路径**（默认）
    # legacy = PySide6 旧界面，2026-11-21 已归档：仍能构建，但不保证可用、
    #          不再发版，只用于查阅/对照。存档标签 archive/legacy-ui-2026-11-21
    [ValidateSet("legacy", "web")]
    [string]$Target = "web",
    # 跳过打包，只校验现有产物（用于 CI 的 verify 阶段）
    [switch]$VerifyOnly,
    # 冒烟（真的把 exe 启动一次）**默认开启**，因为它是唯一能抓到
    # 「spec 少带一个模块」这类问题的手段。无 GUI 的环境传 -NoSmoke 关掉。
    [switch]$NoSmoke,
    # 历史参数，保留只为不破坏旧命令行（现在不传也是开的）
    [switch]$Smoke
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

# 冒烟：真的把打包好的 exe 启动一次。
# 为什么值得做：spec / hiddenimports 少带了一个模块时，构建成功、包也完整，
# 只有**双击运行**才会崩 —— 静态检查抓不到这类问题。
# 依赖 main_web.py 的 L4D2_SHOT 钩子：等界面稳定、截图、然后由我们负责收掉进程。
function Invoke-SmokeTest([string]$Dir, [string]$Label) {
    $exe = @(Get-ChildItem -LiteralPath $Dir -Filter *.exe -File)
    if ($exe.Count -ne 1) {
        throw "[$Label] 冒烟测试：包顶层应恰好有 1 个 exe，实际 $($exe.Count) 个"
    }

    $shot = Join-Path $env:TEMP ("l4d2-smoke-" + [guid]::NewGuid().ToString("N") + ".bmp")
    $log = "$shot.out.log"
    $errLog = "$shot.err.log"
    $proc = $null
    $prevShot = $env:L4D2_SHOT
    try {
        $env:L4D2_SHOT = $shot
        $proc = Start-Process -FilePath $exe[0].FullName -PassThru `
            -RedirectStandardOutput $log -RedirectStandardError $errLog

        $deadline = (Get-Date).AddSeconds(90)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 500
            if ((Test-Path -LiteralPath $shot) -and
                (Get-Item -LiteralPath $shot).Length -gt 100KB) { break }
            if ($proc.HasExited) { break }
        }
        # 截图只是钩子，进程不会自己退出，必须收掉
        if (-not $proc.HasExited) {
            $proc.Kill()
            $proc.WaitForExit(5000) | Out-Null
        }

        $text = ""
        if (Test-Path -LiteralPath $log) { $text = Get-Content -LiteralPath $log -Raw }
        $errText = ""
        if (Test-Path -LiteralPath $errLog) { $errText = Get-Content -LiteralPath $errLog -Raw }

        if (-not (Test-Path -LiteralPath $shot)) {
            throw "[$Label] 冒烟测试：exe 退出了但没截到图。日志：`n$text`n$errText"
        }
        # 关键断言：桥接层真的起来了。只有窗口不算 —— 空壳窗口也能截图。
        if ($text -notmatch "boot .*ok=true") {
            throw "[$Label] 冒烟测试：前端 boot 未成功（桥接层没起来）。日志：`n$text`n$errText"
        }
    }
    finally {
        if ($proc -and -not $proc.HasExited) { $proc.Kill() }
        if ($null -eq $prevShot) { Remove-Item Env:L4D2_SHOT -ErrorAction SilentlyContinue }
        else { $env:L4D2_SHOT = $prevShot }
        foreach ($f in @($shot, $log, $errLog)) {
            if (Test-Path -LiteralPath $f) {
                Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
            }
        }
        # 跑一次就会在包内留下 data/（里面有本地游戏路径），不清掉会被打进 zip
        $runtimeData = Join-Path $Dir "data"
        if (Test-Path -LiteralPath $runtimeData) {
            Assert-InRelease $runtimeData
            Remove-Item -LiteralPath $runtimeData -Recurse -Force
        }
    }
    Write-Host "  冒烟通过：exe 能启动，桥接 ok=true" -ForegroundColor Green
}

# 刚写完的文件常被 Defender / 索引器短暂独占，Move-Item / Remove-Item
# 会抛 "Access to the path ... is denied"。这不是真错误，等一会儿重试就好；
# 但失败一次就会毁掉整次构建（产物停在 release\.build 里，zip 还是旧的）。
function Invoke-WithRetry([scriptblock]$Action, [string]$What, [int]$Tries = 6) {
    for ($i = 1; $i -le $Tries; $i++) {
        try {
            & $Action
            return
        }
        catch {
            if ($i -eq $Tries) {
                throw "[$What] 重试 $Tries 次仍然失败：$($_.Exception.Message)"
            }
            Start-Sleep -Milliseconds (250 * $i)
        }
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
            Invoke-WithRetry { Remove-Item -LiteralPath $packageDir -Recurse -Force } `
                "删除旧产物"
        }
        Invoke-WithRetry { Move-Item -LiteralPath $rawPackageDir -Destination $packageDir } `
            "移动产物到 release"
        if (-not (Test-Path -LiteralPath $packageDir -PathType Container)) {
            throw "[$Stack] 产物没有被搬到预期位置: $packageDir"
        }
    }

    Test-Package $packageDir $Stack

    if ($cfg.Entry -eq "main_web.py") {
        if ($NoSmoke) {
            # 不静默跳过：CI 日志里要能一眼看出来「这次没验过启动」
            Write-Host "  已跳过冒烟（-NoSmoke）" -ForegroundColor DarkYellow
        }
        else {
            Invoke-SmokeTest $packageDir $Stack
            # 冒烟会在包里创建 data/，再查一遍，别把运行时数据打进 zip
            Test-Package $packageDir $Stack
        }
    }
    else {
        Write-Host "  跳过冒烟：$Stack 栈没有 L4D2_SHOT 钩子" -ForegroundColor DarkYellow
    }

    if ($VerifyOnly) {
        Write-Host "  校验通过（未重新打包）: $packageDir" -ForegroundColor Green
        return
    }

    if (Test-Path -LiteralPath $zipPath) {
        Invoke-WithRetry { Remove-Item -LiteralPath $zipPath -Force } "删除旧 zip"
    }
    Invoke-WithRetry {
        Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal
    } "压缩产物" 3

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

if ($Target -eq "legacy") {
    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Yellow
    Write-Host " 警告：legacy（PySide6 旧界面）已于 2026-11-21 归档" -ForegroundColor Yellow
    Write-Host "       不保证可用，不再发版 —— 只用于查阅/对照。" -ForegroundColor Yellow
    Write-Host "       存档标签：archive/legacy-ui-2026-11-21" -ForegroundColor Yellow
    Write-Host "       新界面请用：.\build_release.ps1" -ForegroundColor Yellow
    Write-Host "==============================================================" -ForegroundColor Yellow
    Write-Host ""
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
}

foreach ($stack in $stacks) {
    New-Release $stack $Version
}

if (Test-Path -LiteralPath $rawDistDir) {
    Remove-Item -LiteralPath $rawDistDir -Recurse -Force
}

Write-Host ""
Write-Host "全部完成（$($stacks -join ', ')）。" -ForegroundColor Green
