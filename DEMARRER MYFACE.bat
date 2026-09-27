@echo off
chcp 65001 >nul
title MYFACE - Demarrage
cd /d "D:\MY FACE"

echo ============================================
echo   DEMARRAGE DE MYFACE
echo ============================================
echo.

echo [1/5] Verification de Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
  echo       Docker n'est pas demarre. Je le lance, patiente...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
)
:attente_docker
docker info >nul 2>&1
if errorlevel 1 (
  timeout /t 5 /nobreak >nul
  goto attente_docker
)
echo       Docker est pret.

echo [2/5] Demarrage de MYFACE...
docker compose up -d backend frontend nginx
if errorlevel 1 goto erreur

echo [3/5] Chargement du modele de reconnaissance faciale ^(1 a 2 minutes^)...
:attente_api
curl -s -f -o nul http://localhost:8000/health
if errorlevel 1 (
  timeout /t 5 /nobreak >nul
  goto attente_api
)
echo       Le moteur est pret.

echo [4/5] Redemarrage de nginx...
docker restart myface-nginx-1 >nul

echo [5/5] Ouverture de l'acces public...
docker compose --profile domaine up -d tunnel-domaine >nul 2>&1
echo       Tunnel Cloudflare demarre.

echo.
echo ============================================
echo   MYFACE EST EN LIGNE
echo.
echo   Sur ce PC       : http://localhost
echo   Administration  : http://localhost/admin/login
echo   Depuis dehors   : https://myfaceci.online
echo ============================================
echo.
start "" http://localhost
pause
exit /b 0

:erreur
echo.
echo !!! Le demarrage a echoue. Note le message ci-dessus et envoie-le a Claude.
pause
exit /b 1
