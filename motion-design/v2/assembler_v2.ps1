# Assemble le film muet et la bande son en MP4 (H.264 + AAC), avec le
# montage video integre a Windows (Windows.Media.Editing), sans ffmpeg.
#   powershell -ExecutionPolicy Bypass -File motion-design/v2/assembler_v2.ps1
$ErrorActionPreference = 'Stop'
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$methodes = [System.WindowsRuntimeSystemExtensions].GetMethods()
$asTaskOp = $methodes | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$asTaskProg = $methodes | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2' } | Select-Object -First 1
function Attendre($op, [Type]$type) {
    $t = $asTaskOp.MakeGenericMethod($type).Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    return $t.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFolder, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Editing.MediaComposition, Windows.Media.Editing, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Editing.MediaClip, Windows.Media.Editing, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Editing.BackgroundAudioTrack, Windows.Media.Editing, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.MediaProperties.MediaEncodingProfile, Windows.Media.MediaProperties, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Transcoding.TranscodeFailureReason, Windows.Media.Transcoding, ContentType = WindowsRuntime] | Out-Null

$video = Attendre ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Join-Path $ici 'myface-motion-design-v2.mp4'))) ([Windows.Storage.StorageFile])
$son = Attendre ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Join-Path $ici 'son-motion-design-v2.wav'))) ([Windows.Storage.StorageFile])
$dossier = Attendre ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($ici)) ([Windows.Storage.StorageFolder])

foreach ($sortie in @(@('myface-motion-design-v2-son.mp4', 1080, 1920, 12000000), @('myface-motion-design-v2-son-leger.mp4', 720, 1280, 4000000))) {
    $clip = Attendre ([Windows.Media.Editing.MediaClip]::CreateFromFileAsync($video)) ([Windows.Media.Editing.MediaClip])
    $piste = Attendre ([Windows.Media.Editing.BackgroundAudioTrack]::CreateFromFileAsync($son)) ([Windows.Media.Editing.BackgroundAudioTrack])
    $compo = New-Object Windows.Media.Editing.MediaComposition
    # les listes WinRT ne montrent pas Add a PowerShell : on passe par l'interface
    [System.Collections.Generic.ICollection[Windows.Media.Editing.MediaClip]].GetMethod('Add').Invoke($compo.Clips, @($clip)) | Out-Null
    [System.Collections.Generic.ICollection[Windows.Media.Editing.BackgroundAudioTrack]].GetMethod('Add').Invoke($compo.BackgroundAudioTracks, @($piste)) | Out-Null

    $profil = [Windows.Media.MediaProperties.MediaEncodingProfile]::CreateMp4([Windows.Media.MediaProperties.VideoEncodingQuality]::HD1080p)
    $profil.Video.Width = $sortie[1]
    $profil.Video.Height = $sortie[2]
    $profil.Video.Bitrate = $sortie[3]
    $profil.Video.FrameRate.Numerator = 30
    $profil.Video.FrameRate.Denominator = 1

    $fichier = Attendre ($dossier.CreateFileAsync($sortie[0], [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
    $op = $compo.RenderToFileAsync($fichier, [Windows.Media.Editing.MediaTrimmingPreference]::Precise, $profil)
    $t = $asTaskProg.MakeGenericMethod([Windows.Media.Transcoding.TranscodeFailureReason], [double]).Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    Write-Output ($sortie[0] + ' : ' + $t.Result)
}
