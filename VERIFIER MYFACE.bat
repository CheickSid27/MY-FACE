@echo off
chcp 65001 >nul
title MYFACE - Verification avant commit
cd /d "%~dp0"

echo ============================================
echo   VERIFICATION DE MYFACE
echo ============================================
echo.
echo Les memes controles que la CI GitHub, mais sur ce PC.
echo Aucune modification n'est faite : ce script ne fait que verifier.
echo.

echo [1/4] Verification de Docker Desktop...
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
echo.

echo [2/4] Base de donnees de test...
docker compose up -d db
if errorlevel 1 goto erreur_docker
echo.

echo [3/4] Tests du backend ^(pytest, vrai PostgreSQL^)...
echo       La suite tourne contre myface_test, jamais contre Neon.
docker compose run --rm --no-deps -w /app backend python3 -m pytest -q
if errorlevel 1 goto tests_rouges
echo.
echo       Tests OK.
echo.

echo [4/4] Verification des types du frontend...
echo       Premier lancement un peu long ^(installation des dependances^).
docker run --rm -v "%cd%\frontend":/app -w /app node:20-alpine sh -c "npm ci --silent && npx tsc --noEmit"
if errorlevel 1 goto types_rouges
echo       Types OK.
echo.

echo ============================================
echo   TOUT EST VERT - vous pouvez committer
echo ============================================
echo.
echo Rapport de style ^(informatif, n'empeche rien^) :
docker compose run --rm --no-deps -w /app backend python3 -m ruff check . --statistics
echo.
pause
exit /b 0

:tests_rouges
echo.
echo ============================================
echo   DES TESTS ECHOUENT
echo ============================================
echo Lisez les lignes FAILED ci-dessus. Ne committez pas en l'etat.
echo.
pause
exit /b 1

:types_rouges
echo.
echo ============================================
echo   ERREURS DE TYPES DANS LE FRONTEND
echo ============================================
echo Chaque ligne indique le fichier et la ligne en cause.
echo.
pause
exit /b 1

:erreur_docker
echo.
echo Impossible de demarrer la base de donnees. Docker Desktop tourne-t-il ?
echo.
pause
exit /b 1
