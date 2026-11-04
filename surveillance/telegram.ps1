# Envoi d'un message Telegram a l'utilisateur. Le jeton du robot et le numero
# de la conversation sont lus dans le fichier .env (TELEGRAM_BOT_TOKEN,
# TELEGRAM_CHAT_ID), jamais ecrits ici ni envoyes sur GitHub.
#
#   powershell -File surveillance\telegram.ps1 "Bonjour"     (envoi direct)
#   . surveillance\telegram.ps1 ; Envoyer-Telegram "texte"   (depuis un script)

function Lire-Env($cle) {
    $fichier = Join-Path (Split-Path -Parent $PSScriptRoot) ".env"
    $ligne = Get-Content $fichier -Encoding utf8 | Where-Object { $_ -match "^$cle=" } | Select-Object -First 1
    if ($ligne) { return $ligne.Substring($cle.Length + 1).Trim() }
    return $null
}

function Envoyer-Telegram([string]$texte) {
    $jeton = Lire-Env "TELEGRAM_BOT_TOKEN"
    $chat = Lire-Env "TELEGRAM_CHAT_ID"
    if (-not $jeton -or -not $chat) { return $false }
    $corps = @{ chat_id = $chat; text = $texte } | ConvertTo-Json -Compress
    try {
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$jeton/sendMessage" -Method Post `
            -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($corps)) -TimeoutSec 20 | Out-Null
        return $true
    } catch { return $false }
}

if ($MyInvocation.InvocationName -ne "." -and $args.Count -gt 0) {
    if (Envoyer-Telegram ($args -join " ")) { "envoye" } else { "echec (jeton ou numero de conversation manquant dans .env ?)" }
}
