' Lance le gardien sans ouvrir de fenetre (la tache planifiee appelle ce fichier).
dossier = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dossier & "\gardien.ps1""", 0, True
