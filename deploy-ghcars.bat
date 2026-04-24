@echo off
echo.
echo  ================================
echo   GH Cars — Deploy a Vercel
echo  ================================
echo.

cd /d C:\Users\kuaji\Documents\roker_nexus

echo [1/3] Eliminando rama temporal anterior...
git branch -D concesionaria-deploy 2>nul

echo [2/3] Extrayendo subtree gh-cars-web...
git subtree split --prefix=sistemas/concesionaria/gh-cars-web -b concesionaria-deploy
if errorlevel 1 (
    echo ERROR: Fallo al crear subtree. Abortando.
    pause
    exit /b 1
)

echo [3/3] Pusheando a GitHub (Vercel auto-deploy en ~30 seg)...
git push concesionaria concesionaria-deploy:main --force
if errorlevel 1 (
    echo ERROR: Fallo el push. Verificar conexion o credenciales.
    pause
    exit /b 1
)

echo.
echo  Deploy enviado OK
echo  Ver build en: https://vercel.com/kuaji28/gh-cars-web
echo  App en:       https://gh-cars-web.vercel.app
echo.
pause
