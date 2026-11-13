param(
    [string]$Destination = ""
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not $Destination) {
    $Destination = Join-Path $projectRoot "third_party\7zip"
}
$destinationPath = [IO.Path]::GetFullPath($Destination)
$required = @("7z.exe", "7z.dll")
$complete = $true
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $destinationPath $name) -PathType Leaf)) {
        $complete = $false
        break
    }
}
if ($complete -and (Test-Path -LiteralPath (Join-Path $destinationPath "License.txt"))) {
    Write-Host "7-Zip 组件已存在: $destinationPath"
    exit 0
}

$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$work = Join-Path $tempRoot ("l4d2-7zip-" + [Guid]::NewGuid().ToString("N"))
$workPath = [IO.Path]::GetFullPath($work)
$workPrefix = $tempRoot.TrimEnd("\") + "\"
if (-not $workPath.StartsWith($workPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Split-Path -Leaf $workPath).StartsWith("l4d2-7zip-")) {
    throw "拒绝使用临时目录之外的路径: $workPath"
}

try {
    New-Item -ItemType Directory -Path $workPath | Out-Null
    $page = Invoke-WebRequest -Uri "https://www.7-zip.org/download.html" -UseBasicParsing
    $match = [regex]::Match(
        [string]$page.Content,
        'href=["'']([^"'']*?7z[0-9.]+-x64\.msi)["'']',
        [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) {
        throw "无法从 7-Zip 官方下载页找到 x64 MSI"
    }

    $relativeUrl = [Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
    $installerUrl = [Uri]::new([Uri]"https://www.7-zip.org/download.html", $relativeUrl)
    $officialHost = $installerUrl.Host -in @(
        "7-zip.org", "www.7-zip.org", "sourceforge.net")
    $officialGitHub = (
        $installerUrl.Host -eq "github.com" -and
        $installerUrl.AbsolutePath.StartsWith(
            "/ip7z/7zip/releases/download/",
            [StringComparison]::OrdinalIgnoreCase))
    if (-not $officialHost -and -not $officialGitHub) {
        throw "7-Zip 下载地址不是官方域名: $installerUrl"
    }

    $msiPath = Join-Path $workPath "7zip-x64.msi"
    Write-Host "下载 7-Zip: $installerUrl"
    Invoke-WebRequest -Uri $installerUrl.AbsoluteUri -OutFile $msiPath -UseBasicParsing
    if ($officialGitHub) {
        $segments = $installerUrl.AbsolutePath.Split(
            "/", [StringSplitOptions]::RemoveEmptyEntries)
        $tag = $segments[4]
        $fileName = [regex]::Escape($segments[5])
        $assetPage = Invoke-WebRequest `
            -Uri "https://github.com/ip7z/7zip/releases/expanded_assets/$tag" `
            -UseBasicParsing
        $digestMatch = [regex]::Match(
            [string]$assetPage.Content,
            "href=[`"'][^`"']*/$fileName[`"'][\s\S]{0,5000}?sha256:([0-9a-f]{64})",
            [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $digestMatch.Success) {
            throw "7-Zip 官方发布页未提供安装包 SHA-256"
        }
        $expectedHash = $digestMatch.Groups[1].Value.ToLowerInvariant()
        $actualHash = (Get-FileHash -LiteralPath $msiPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            throw "7-Zip 安装包 SHA-256 校验失败"
        }
        Write-Host "SHA-256 校验通过: $actualHash"
    }
    else {
        $signature = Get-AuthenticodeSignature -LiteralPath $msiPath
        if ($signature.Status -ne "Valid") {
            throw "7-Zip 安装包数字签名校验失败: $($signature.Status)"
        }
        Write-Host "数字签名有效: $($signature.SignerCertificate.Subject)"
    }

    $extractDir = Join-Path $workPath "extracted"
    New-Item -ItemType Directory -Path $extractDir | Out-Null
    $arguments = @(
        "/a",
        "`"$msiPath`"",
        "/qn",
        "TARGETDIR=`"$extractDir`""
    )
    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList $arguments `
        -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "7-Zip MSI 解包失败，退出码: $($process.ExitCode)"
    }

    $exe = Get-ChildItem -LiteralPath $extractDir -Recurse -File -Filter "7z.exe" |
        Select-Object -First 1
    if (-not $exe) {
        throw "7-Zip MSI 内未找到 7z.exe"
    }
    $sourceDir = $exe.Directory.FullName
    if (-not (Test-Path -LiteralPath (Join-Path $sourceDir "7z.dll") -PathType Leaf)) {
        throw "7-Zip MSI 内缺少完整的 7z.dll"
    }

    New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
    Copy-Item -Path (Join-Path $sourceDir "*") `
        -Destination $destinationPath -Recurse -Force
    Write-Host "7-Zip 组件已准备: $destinationPath"
}
finally {
    if (Test-Path -LiteralPath $workPath) {
        $resolvedWork = (Resolve-Path -LiteralPath $workPath).Path
        if ($resolvedWork.StartsWith($workPrefix, [StringComparison]::OrdinalIgnoreCase) -and
                (Split-Path -Leaf $resolvedWork).StartsWith("l4d2-7zip-")) {
            Remove-Item -LiteralPath $resolvedWork -Recurse -Force
        }
    }
}
