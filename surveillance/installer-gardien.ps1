# Installe (ou reinstalle) la tache planifiee « MYFACE Gardien » : toutes les
# minutes, pour le compte Windows connecte, sans fenetre.
#   powershell -ExecutionPolicy Bypass -File surveillance\installer-gardien.ps1
# Pour la retirer : Unregister-ScheduledTask -TaskName "MYFACE Gardien" -Confirm:$false
$vbs = Join-Path $PSScriptRoot "lancer-cache.vbs"
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbs`""
$declencheur = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$demarrage = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "MYFACE Gardien" -Action $action -Trigger @($declencheur, $demarrage) -Settings $reglages `
    -Description "Surveille MYFACE toutes les minutes, relance ce qui est tombe et previent sur Telegram." -Force | Out-Null
"Tache « MYFACE Gardien » installee."
