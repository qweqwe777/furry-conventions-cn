@echo off
rem FEC incremental scrape (ASCII only; CRLF; %~dp0 resolves the CJK path)
rem The scraper writes raw/ and data/ next to itself, so run it from its own dir.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist logs mkdir logs
python 00_scrape.py >> logs\scrape.log 2>&1
exit /b %ERRORLEVEL%
