@echo off
setlocal
cd /d "%~dp0"
set "DZONE_PYTHON="
set "DZONE_ARGS="
if exist ".venv\Scripts\python.exe" (
  set "DZONE_PYTHON=.venv\Scripts\python.exe"
  goto comprobar
)
py -3 --version >nul 2>&1
if %errorlevel%==0 (
  set "DZONE_PYTHON=py"
  set "DZONE_ARGS=-3"
  goto comprobar
)
python --version >nul 2>&1
if %errorlevel%==0 (
  set "DZONE_PYTHON=python"
  goto comprobar
)
rem Detectar instalaciones locales no registradas en PATH o py.
for /d %%P in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
  if exist "%%~fP\python.exe" set "DZONE_PYTHON=%%~fP\python.exe"
)
if defined DZONE_PYTHON goto comprobar
rem Alternativa para esta demo cuando se ejecuta desde Codex sin Python instalado.
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  set "DZONE_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  goto comprobar
)
echo No se encontro Python. Instala Python 3.10 o superior con Tkinter.
pause
exit /b 1
:comprobar
"%DZONE_PYTHON%" %DZONE_ARGS% -c "import tkinter, reportlab" >nul 2>&1
if errorlevel 1 (
  echo El Python seleccionado no tiene todas las dependencias de Dzone.
  echo Interprete: %DZONE_PYTHON% %DZONE_ARGS%
  echo Para instalar ReportLab en ese mismo entorno ejecuta:
  echo "%DZONE_PYTHON%" %DZONE_ARGS% -m pip install -r requirements.txt
  echo Si falta Tkinter, modifica la instalacion de Python para incluir Tcl/Tk.
  pause
  exit /b 1
)
"%DZONE_PYTHON%" %DZONE_ARGS% dzone.py
if errorlevel 1 pause
endlocal
