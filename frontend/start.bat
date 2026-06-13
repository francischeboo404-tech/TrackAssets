@echo off
cd /d "%~dp0"
set DEBUG=vite:*
npx vite --port 5173 --host 127.0.0.1
