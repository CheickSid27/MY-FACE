# Voix off v2 : une phrase entiere par fichier, en SSML (pauses et intonation
# naturelles, « MYFACE » prononce par la voix francaise). WAV 48 kHz mono.
#   powershell -ExecutionPolicy Bypass -File motion-design/v2/voix/generer_voix.ps1
param([string]$Voix = 'Microsoft Hortense Desktop')
Add-Type -AssemblyName System.Speech
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$marque = '<phoneme alphabet="ipa" ph="maj.fejs">MYFACE</phoneme>'
foreach ($l in (Get-Content -Path (Join-Path $ici 'texte.txt') -Encoding UTF8)) {
    if (-not $l.Trim() -or $l.StartsWith('#')) { continue }
    $p = $l.Split('|')
    $id = $p[0]; $vitesse = [int]$p[3]; $texte = $p[4]
    $texte = [System.Security.SecurityElement]::Escape($texte).Replace('{MYFACE}', $marque)
    # une respiration un peu plus marquee apres les deux-points et les points d'interrogation
    $texte = $texte.Replace(' : ', ' : <break time="160ms"/>')
    $taux = '{0:+0;-0;+0}%' -f ($vitesse * 3)
    $ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fr-FR">' +
            "<voice name=""$Voix""><prosody rate=""$taux"" pitch=""+2%"">$texte</prosody></voice></speak>"
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SetOutputToWaveFile((Join-Path $ici ($id + '.wav')), $format)
    $s.SpeakSsml($ssml)
    $s.Dispose()
    Write-Output ($id + ' ok')
}
