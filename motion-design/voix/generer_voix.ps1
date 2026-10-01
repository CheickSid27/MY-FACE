# Voix off temoin du motion design : une phrase par fichier WAV (48 kHz, mono).
# Voix Windows installees : Hortense (fr-FR) et Zira (en-US, pour « My Face »).
#   powershell -ExecutionPolicy Bypass -File motion-design/voix/generer_voix.ps1
Add-Type -AssemblyName System.Speech
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$lignes = Get-Content -Path (Join-Path $ici 'voix-off.txt') -Encoding UTF8
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
foreach ($l in $lignes) {
    if (-not $l.Trim()) { continue }
    $parts = $l.Split('|', 3)
    $id = $parts[0]; $langue = $parts[1]; $texte = $parts[2]
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    if ($langue -eq 'en') { $s.SelectVoice('Microsoft Zira Desktop'); $s.Rate = 0 }
    else { $s.SelectVoice('Microsoft Hortense Desktop'); $s.Rate = 2 }
    $sortie = Join-Path $ici ($id + '.wav')
    $s.SetOutputToWaveFile($sortie, $format)
    $s.Speak($texte)
    $s.Dispose()
    Write-Output ($id + ' ok')
}
