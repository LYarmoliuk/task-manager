$bad = git ls-files "*.py" | Where-Object { $_ -notlike "experiments/reliability/*" } | Where-Object {
  $b = [IO.File]::ReadAllBytes($_); $b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF }
if ($bad) { "BOM found (radon cannot parse):"; $bad; exit 1 } else { "OK: no BOM in tracked .py files" }
