$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$root = 'C:\Users\Emsta\Desktop\workflow\stadia-archive'
$log = Join-Path $root 'download-log.txt'
function Log($msg) {
  $line = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Add-Content -Path $log -Value $line -Encoding utf8
  Write-Output $line
}
function Fetch($url, $out, $timeout = 600) {
  $name = Split-Path $out -Leaf
  try {
    if (Test-Path $out) { Log "SKIP $name (exists)"; return }
    Invoke-WebRequest -Uri $url -OutFile $out -TimeoutSec $timeout -Headers @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36' }
    $len = (Get-Item $out).Length
    Log ("OK   {0,-58} {1,12} bytes" -f $name, $len)
  } catch {
    Log ("ERR  {0,-58} {1}" -f $name, $_.Exception.Message)
    if (Test-Path $out) { Remove-Item $out -Force }
  }
}

Log "=== start ==="
Log ("PS " + $PSVersionTable.PSVersion)

# 1) GitHub repos
$repos = @(
  'Scyne/stadiaRawBtFw','71/stadiacontroller','luigimannoni/stadia-controller-flasher','ChristopherKlay/stadiacontroller',
  'jkfran/stadiacast','hazrpg/stadia-flasher','MWisBest/StadiEm','merlinschumacher/Stadia-Controller-Bluetooth-Firmware-Bin',
  'vouiren/StadiaFW','ricky8k/Stadia-Controller-Firmware','StadiaMemories/firmware','berge472/stadia-ble-dongle',
  'O-IceDawn-O/stadia-stick','JaimeDelgadoNaya/stadia-controller-research','gomezluisj/stadia-controller-re',
  'helloparthshah/StadiaWireless','pjburnhill/stadia-controller-support','sebastiansam55/stadia-bluetooth','aisk/WinStadia',
  'DJm00n/ControllersInfo','JayHeng/NXP-MCUBootUtility'
)
foreach ($r in $repos) {
  $file = Join-Path (Join-Path $root 'repos') (($r -replace '/', '__') + '.zip')
  Fetch "https://codeload.github.com/$r/zip/HEAD" $file 900
}

# 2) Firmware from Scyne repo (raw, fallback jsdelivr)
$fw = @(
  @{ n = 'bruce_pvt_a_prod_signed.bin'; d = 'firmware\bruce' },
  @{ n = 'bruce_dvt_a_dev_signed.bin'; d = 'firmware\bruce' },
  @{ n = 'bruce_dvt_a_stage_signed.bin'; d = 'firmware\bruce' },
  @{ n = 'restricted_ivt_flashloader.bin'; d = 'firmware\flashloader' },
  @{ n = 'flashloader_fcb_get_vendor_id.bin'; d = 'firmware\flashloader' },
  @{ n = 'flashloader_fcb_w25q128jw.bin'; d = 'firmware\flashloader' }
)
foreach ($f in $fw) {
  $out = Join-Path (Join-Path $root $f.d) $f.n
  Fetch "https://raw.githubusercontent.com/Scyne/stadiaRawBtFw/HEAD/$($f.n)" $out 300
  if (-not (Test-Path $out)) { Fetch "https://cdn.jsdelivr.net/gh/Scyne/stadiaRawBtFw@main/$($f.n)" $out 300 }
}

# 3) NXP reference manual
New-Item -ItemType Directory -Force -Path (Join-Path $root 'hardware\nxp') | Out-Null
Fetch 'https://www.nxp.com/docs/en/reference-manual/IMXRT1060RM.pdf' (Join-Path $root 'hardware\nxp\IMXRT1060RM.pdf') 900

# 4) FCC documents
try {
  $r = Invoke-WebRequest -Uri 'https://fccid.io/A4R-H2B' -UseBasicParsing -TimeoutSec 60 -Headers @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36' }
  Set-Content -Path (Join-Path $root 'hardware\fcc\_index.html') -Value $r.Content -Encoding utf8
  $links = [regex]::Matches($r.Content, 'href="([^"]+\.pdf)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
  Log ("FCC html ok, pdf links found: " + $links.Count)
  $i = 0
  foreach ($l in $links) {
    $i++
    if ($i -gt 12) { break }
    $u = if ($l -like 'http*') { $l } else { 'https://fccid.io' + $l }
    $safe = ($l -split '/')[-1]
    Fetch $u (Join-Path $root ('hardware\fcc\' + $safe)) 300
  }
} catch { Log ("FCC ERR " + $_.Exception.Message) }

Log "=== done ==="
