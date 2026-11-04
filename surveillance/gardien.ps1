# Gardien de MYFACE (etage 1 de la surveillance) : lance par Windows toutes
# les minutes (tache planifiee « MYFACE Gardien », voir installer-gardien.ps1).
#
# - Docker Desktop arrete -> il le demarre (pannes du 21/10, du 27/10, du 04/11).
# - Un conteneur arrete (backend, frontend, nginx, tunnel) -> il le relance.
# - Le serveur ne repond plus 3 fois de suite -> il le redemarre.
# - Il previent sur Telegram quand quelque chose tombe, puis quand c'est reparti,
#   jamais deux fois pour la meme panne (etat garde dans gardien-etat.json).
#
# Rien n'est supprime, rien n'est reconstruit, aucun code n'est modifie.

$ErrorActionPreference = "SilentlyContinue"
$Racine = Split-Path -Parent $PSScriptRoot
$Journal = Join-Path $PSScriptRoot "gardien.log"
$EtatFichier = Join-Path $PSScriptRoot "gardien-etat.json"
. (Join-Path $PSScriptRoot "telegram.ps1")

function Ecrire($texte) {
    $ligne = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $texte
    Add-Content -Path $Journal -Value $ligne -Encoding utf8
    # le journal reste petit : on garde les 2 000 dernieres lignes
    $lignes = Get-Content $Journal -Encoding utf8
    if ($lignes.Count -gt 2500) { $lignes | Select-Object -Last 2000 | Set-Content $Journal -Encoding utf8 }
}

function Lire-Etat {
    if (Test-Path $EtatFichier) { return Get-Content $EtatFichier -Raw | ConvertFrom-Json }
    return [pscustomobject]@{ panne = ""; echecs_sante = 0 }
}

function Repond($url) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15).StatusCode -eq 200 } catch { return $false }
}

$etat = Lire-Etat
$problemes = @()
$actions = @()
Set-Location $Racine

# 1. Docker Desktop
docker info *> $null
if (-not $?) {
    $problemes += "Docker etait arrete"
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for ($i = 0; $i -lt 36; $i++) { Start-Sleep 5; docker info *> $null; if ($?) { break } }
    docker info *> $null
    if ($?) { $actions += "Docker redemarre" } else { $actions += "Docker ne redemarre pas" }
}

# 2. Conteneurs
$attendus = @{ "myface-backend-1" = "backend"; "myface-frontend-1" = "frontend"; "myface-nginx-1" = "nginx"; "myface-tunnel-domaine-1" = "tunnel-domaine" }
$enMarche = docker ps --format "{{.Names}}"
foreach ($nom in @("myface-backend-1", "myface-frontend-1", "myface-nginx-1", "myface-tunnel-domaine-1")) {
    if ($enMarche -notcontains $nom) {
        $service = $attendus[$nom]
        $problemes += "$service arrete"
        if ($service -eq "tunnel-domaine") { docker compose --profile domaine up -d --no-deps tunnel-domaine *> $null }
        else { docker compose up -d --no-deps $service *> $null }
        $actions += "$service relance"
    }
}

# 3. Le serveur repond-il ? (en local, puis depuis internet)
$local = Repond "http://127.0.0.1:8000/health"
if ($local) {
    $etat.echecs_sante = 0
} else {
    $etat.echecs_sante = [int]$etat.echecs_sante + 1
    if ($etat.echecs_sante -ge 3) {
        $problemes += "le serveur ne repond plus depuis 3 minutes"
        docker compose restart backend *> $null
        Start-Sleep 40
        docker compose restart nginx *> $null
        $actions += "serveur et nginx redemarres"
        $etat.echecs_sante = 0
    }
}
$public = Repond "https://app.myfaceci.online/api/health"
if ($local -and -not $public) { $problemes += "le site ne repond pas depuis internet (tunnel ?)" }

# 4. Prevenir (une seule fois par panne, puis au retour)
$panne = ($problemes -join ", ")
if ($panne) {
    Ecrire "PANNE : $panne | ACTIONS : $($actions -join ', ')"
    if ($etat.panne -ne $panne) {
        $faits = if ($actions.Count) { $actions -join "`n- " } else { "rien (a surveiller)" }
        Envoyer-Telegram ("MYFACE : probleme detecte`n- " + ($problemes -join "`n- ") + "`n`nCe que j'ai fait :`n- " + $faits) | Out-Null
    }
    $etat.panne = $panne
} elseif ($etat.panne) {
    Ecrire "RETOUR A LA NORMALE (avant : $($etat.panne))"
    Envoyer-Telegram "MYFACE est de nouveau en ligne. Le site et le serveur repondent." | Out-Null
    $etat.panne = ""
}

$etat | ConvertTo-Json | Set-Content $EtatFichier -Encoding utf8
