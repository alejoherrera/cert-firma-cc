@echo off
REM Arrancar la app local cert-firma-cc.
REM Doble-click sobre este archivo para correr.
cd /d "%~dp0"
echo Iniciando cert-firma-cc...
echo Se abrira el navegador en http://localhost:8501
echo (cerrar esta ventana detiene la app)
python -m streamlit run app/app.py --browser.gatherUsageStats false --server.headless false
pause
