[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$sources = @(
    @{ Year = '2025'; Url = 'https://www.mcm.edu.cn/upload_cn/node/759/SvpohSGacdffe718bcaa3b6e835c03ae3461cab1.zip'; Extension = 'zip'; Sha256 = 'cef6262c24ee3017bdab4ca255299c7b47b2700ad89fd773addde7e241e7e4de' },
    @{ Year = '2024'; Url = 'https://www.mcm.edu.cn/upload_cn/node/725/pmkWxf8H9cfe9984c1a1a5b1263e5dd3b5596ed5.zip'; Extension = 'zip'; Sha256 = '38d9effcede947354f9e9a9c2b4fc68947d83a77c2ff75737e9a662888158726' },
    @{ Year = '2023'; Url = 'https://www.mcm.edu.cn/upload_cn/node/690/Y20WPner9fa62862794e6dc82731a5561ce1132f.rar'; Extension = 'rar'; Sha256 = '37b1010672adcf35831e798264cc69db616027f2287cfeae3c4ee6daf03ae4e6' },
    @{ Year = '2022'; Url = 'https://www.mcm.edu.cn/upload_cn/node/670/5eWlbmTt28f88a0815a79d555da8b7072f971633.rar'; Extension = 'rar'; Sha256 = 'c27eb1b665f070341e134f5dc13bb2af469230424ff2eedabf594eee708bfee4' },
    @{ Year = '2021'; Url = 'https://www.mcm.edu.cn/upload_cn/node/669/HtbJEt9Nb655e46bebfa2a66ec63f940e2da156b.rar'; Extension = 'rar'; Sha256 = '3391573f546fce4511e9a99c24c386e28203d8fee3d29bb2dccada5921cefe7b' }
)

$libraryRoot = Join-Path $PSScriptRoot 'library'
$cacheRoot = Join-Path $PSScriptRoot '.cache'
$archiveRoot = Join-Path $cacheRoot 'archives'
$extractRoot = Join-Path $cacheRoot 'extracted'

New-Item -ItemType Directory -Force -Path $libraryRoot, $archiveRoot, $extractRoot | Out-Null

if (-not (Get-Command tar.exe -ErrorAction SilentlyContinue)) {
    throw 'Windows tar.exe (libarchive) is required to extract ZIP/RAR archives.'
}

$questionCharacter = [char]0x9898

foreach ($source in $sources) {
    $archivePath = Join-Path $archiveRoot ("{0}.{1}" -f $source.Year, $source.Extension)
    $yearRoot = Join-Path $extractRoot $source.Year

    if ($Force -or -not (Test-Path -LiteralPath $archivePath)) {
        Write-Host "Downloading $($source.Year) from the official website..."
        Invoke-WebRequest -Uri $source.Url -OutFile $archivePath -Headers @{ 'User-Agent' = 'Mozilla/5.0' }
    }

    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $source.Sha256) {
        throw "SHA256 mismatch for $archivePath. Expected $($source.Sha256), got $actualHash."
    }

    if ($Force -or -not (Test-Path -LiteralPath $yearRoot)) {
        New-Item -ItemType Directory -Force -Path $yearRoot | Out-Null
        tar.exe -xf $archivePath -C $yearRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to extract $archivePath"
        }
    }

    foreach ($nestedArchive in Get-ChildItem -LiteralPath $yearRoot -Recurse -File -Filter '*.rar') {
        if ($nestedArchive.BaseName -match '^([A-E])') {
            $letter = $Matches[1]
            $nestedRoot = Join-Path $yearRoot ("__nested\{0}" -f $letter)
            if ($Force -or -not (Test-Path -LiteralPath $nestedRoot)) {
                New-Item -ItemType Directory -Force -Path $nestedRoot | Out-Null
                tar.exe -xf $nestedArchive.FullName -C $nestedRoot
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to extract $($nestedArchive.FullName)"
                }
            }
        }
    }

    foreach ($letter in 'A', 'B', 'C', 'D', 'E') {
        $destination = Join-Path $libraryRoot ("{0}\{1}" -f $letter, $source.Year)
        New-Item -ItemType Directory -Force -Path $destination | Out-Null

        $nestedProblem = Join-Path $yearRoot ("__nested\{0}" -f $letter)
        if (Test-Path -LiteralPath $nestedProblem) {
            Copy-Item -Path (Join-Path $nestedProblem '*') -Destination $destination -Recurse -Force
        } else {
            $problemDirectory = Get-ChildItem -LiteralPath $yearRoot -Recurse -Directory |
                Where-Object {
                    $_.Name -eq $letter -or
                    $_.Name -eq ("{0}{1}" -f $letter, $questionCharacter)
                } |
                Sort-Object { $_.FullName.Length } |
                Select-Object -First 1

            if ($problemDirectory) {
                Copy-Item -Path (Join-Path $problemDirectory.FullName '*') -Destination $destination -Recurse -Force
            } else {
                $problemFile = Get-ChildItem -LiteralPath $yearRoot -Recurse -File |
                    Where-Object {
                        $_.Name -eq ("{0}{1}.pdf" -f $letter, $questionCharacter) -or
                        $_.Name -match ("^CUMCM{0}-{1}\.pdf$" -f $source.Year, $letter)
                    } |
                    Select-Object -First 1

                if ($problemFile) {
                    Copy-Item -LiteralPath $problemFile.FullName -Destination $destination -Force
                } else {
                    Write-Warning "Could not identify problem $letter for $($source.Year). Inspect $yearRoot manually."
                }
            }
        }

        $canonicalName = "{0}-{1}.pdf" -f $source.Year, $letter
        $mainPdf = Get-ChildItem -LiteralPath $destination -File -Filter '*.pdf' |
            Where-Object {
                $_.BaseName -match ("^{0}" -f $letter) -or
                $_.BaseName -match ("^CUMCM{0}-{1}$" -f $source.Year, $letter)
            } |
            Select-Object -First 1

        if ($mainPdf -and $mainPdf.Name -ne $canonicalName) {
            $canonicalPath = Join-Path $destination $canonicalName
            if (Test-Path -LiteralPath $canonicalPath) {
                if ($Force) {
                    Copy-Item -LiteralPath $mainPdf.FullName -Destination $canonicalPath -Force
                }
                Remove-Item -LiteralPath $mainPdf.FullName -Force
            } else {
                Rename-Item -LiteralPath $mainPdf.FullName -NewName $canonicalName
            }
        }
    }
}

Write-Host "Official files are available under: $libraryRoot"
Write-Host "Download and extraction caches are stored under: $cacheRoot"
