# Run from C:\GitHub\Smart-School-System   (powershell -ExecutionPolicy Bypass -File fix_templates.ps1)
# 1) profile pictures: data:image/jpeg;base64,{{ x }}  ->  {{ x|img_src }}   (works for file names AND base64)
# 2) Images/School logo.jpg -> Images/School Logo.jpg  (same case as the real file)
$utf8 = New-Object System.Text.UTF8Encoding($false)
$pattern = 'data:image/jpeg;base64,\{\{\s*([^}]+?)\s*\}\}'
$total = 0
foreach ($f in Get-ChildItem "web\templates\pages\*.html") {
    $orig = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
    $text = $orig.Replace("Images/School logo.jpg", "Images/School Logo.jpg")
    $count = [regex]::Matches($text, $pattern).Count
    if ($count -gt 0) {
        $text = [regex]::Replace($text, $pattern, '{{ $1|img_src }}')
        if ($text -notmatch '\{%\s*load\s+[^%]*school_tags') {
            $nl = "`n"; if ($text.Contains("`r`n")) { $nl = "`r`n" }
            $rx = New-Object System.Text.RegularExpressions.Regex('(\{%\s*load static\s*%\})')
            if ($rx.IsMatch($text)) {
                $text = $rx.Replace($text, ('$1' + $nl + '{% load school_tags %}'), 1)
            } elseif ($text -notmatch '\{%\s*extends') {
                $text = '{% load school_tags %}' + $nl + $text
            } else {
                Write-Host "CHECK BY HAND (extends, no load): $($f.Name)" -ForegroundColor Yellow
            }
        }
    }
    if ($text -ne $orig) {
        [System.IO.File]::WriteAllText($f.FullName, $text, $utf8)
        Write-Host ("fixed {0,-34} {1} picture(s)" -f $f.Name, $count)
        $total += $count
    }
}
Write-Host "Done. $total picture tags fixed."
# 3) report images that templates use but are missing on disk
$img = "web\Project\static\Images"
Select-String -Path "web\templates\pages\*.html" -Pattern "Images/([^'`"]+\.(jpg|png|webp|jpeg|gif))" -AllMatches |
  ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique |
  ForEach-Object { if (-not (Test-Path (Join-Path $img $_))) { Write-Host "MISSING IMAGE: $_" -ForegroundColor Red } }
