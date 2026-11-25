$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$root = 'C:\Users\Emsta\Desktop\workflow\stadia-archive'
$log = Join-Path $root 'download-log.txt'
function Log($msg) {
  $line = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Add-Content -Path $log -Value $line -Encoding utf8
  Write-Output $line
}
function Fetch($url, $out, $timeout = 600, $referer = '') {
  $name = Split-Path $out -Leaf
  if (Test-Path $out) { $len = (Get-Item $out).Length; if ($len -gt 0) { Log "SKIP $name"; return } }
  try {
    $h = @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36' }
    if ($referer) { $h['Referer'] = $referer }
    Invoke-WebRequest -Uri $url -OutFile $out -TimeoutSec $timeout -Headers $h
    Log ("OK   {0,-52} {1,12} bytes" -f $name, (Get-Item $out).Length)
  } catch {
    Log ("ERR  {0,-52} {1}" -f $name, $_.Exception.Message)
    if (Test-Path $out) { Remove-Item $out -Force }
  }
}

Log "=== phase2 start ==="

# FCC exhibits
$idx = Join-Path $root 'hardware\fcc\_index.html'
if (Test-Path $idx) {
  $html = Get-Content $idx -Raw
  $ex = [regex]::Matches($html, 'href="(/A4RH2B/[^"]+?)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
  Log ("FCC exhibits: " + $ex.Count)
  foreach ($e in $ex) {
    $pdf = "https://fccid.io$e.pdf"
    $safe = (($e -replace '^/A4RH2B/', '') -replace '/', '_') + '.pdf'
    Fetch $pdf (Join-Path $root ('hardware\fcc\' + $safe)) 600 'https://fccid.io/A4R-H2B'
  }
} else {
  Log "FCC index missing"
}

# NXP reference manual, several mirrors
$nxp = Join-Path $root 'hardware\nxp\IMXRT1060RM.pdf'
$cands = @(
  'https://www.nxp.com.cn/docs/en/reference-manual/IMXRT1060RM.pdf',
  'https://www.nxp.com/docs/en/reference-manual/IMXRT1060RM.pdf',
  'https://cache.nxp.com/docs/en/reference-manual/IMXRT1060RM.pdf',
  'https://www.nxp.com/docs/en/reference-manual/IMXRT1060RM.pdf?fsrch=1&sr=1'
)
foreach ($u in $cands) {
  if (Test-Path $nxp) { break }
  Fetch $u $nxp 900 'https://www.nxp.com/products/IMX-RT1060'
}

Log "=== phase2 done ==="
