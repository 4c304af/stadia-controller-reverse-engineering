$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = 'C:\Users\Emsta\Desktop\workflow\stadia-archive'
$log = Join-Path $root 'download-log.txt'
function Log($m) { $l = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content $log $l -Encoding utf8; Write-Output $l }

$zipPath = Join-Path $root 'repos\vouiren__StadiaFW.zip'
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$map = @(
  @{ prefix = 'StadiaFW-HEAD/ota/';       dest = 'firmware\gotham-ota' },
  @{ prefix = 'StadiaFW-HEAD/bluetooth/'; dest = 'firmware\bruce' },
  @{ prefix = 'StadiaFW-HEAD/flashloader/'; dest = 'firmware\flashloader' },
  @{ prefix = 'StadiaFW-HEAD/hashes/';    dest = 'firmware\hashes' }
)
foreach ($m in $map) {
  $dest = Join-Path $root $m.dest
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  $entries = $zip.Entries | Where-Object { $_.FullName.StartsWith($m.prefix) -and $_.Name -ne '' }
  foreach ($e in $entries) {
    $target = Join-Path $dest $e.Name
    if (Test-Path $target) {
      if ((Get-Item $target).Length -eq $e.Length) { continue }
    }
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $target, $true)
  }
  Log ("extracted {0} files -> {1}" -f $entries.Count, $m.dest)
}
$zip.Dispose()

# 在线抓到的 282115 与仓库内同名文件比对，避免重复
$live = Join-Path $root 'firmware\gotham\ota.282115.gotham-pvt-a.bin'
$repoCopy = Get-ChildItem (Join-Path $root 'firmware\gotham-ota') -Filter 'ota.282115*' | Select-Object -First 1
if ((Test-Path $live) -and $repoCopy) {
  $h1 = (Get-FileHash $live -Algorithm SHA256).Hash
  $h2 = (Get-FileHash $repoCopy.FullName -Algorithm SHA256).Hash
  if ($h1 -eq $h2) { Remove-Item $live -Force; Log "live OTA identical to repo copy, deduped" }
  else { Log "WARN live OTA differs from repo copy" }
}
