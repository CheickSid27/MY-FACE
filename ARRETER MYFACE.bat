@echo off
chcp 65001 >nul
title MYFACE - Arret
cd /d "D:\MY FACE"

echo Fermeture de l'acces public...
docker compose --profile domaine stop tunnel-domaine >nul 2>&1

echo Arret de MYFACE...
docker compose stop

echo.
echo MYFACE est arrete. Plus rien n'est accessible, ni ici ni sur Internet.
echo.
pause
