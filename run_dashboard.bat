@echo off
REM Launch the Blackjack Bet-Spread dashboard.
REM Double-click this file, then open http://127.0.0.1:8050 in your browser.
cd /d "%~dp0"
python -m app.app
pause
