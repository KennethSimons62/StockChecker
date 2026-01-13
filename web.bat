@echo off
title Launching LEGO Master Auditor
echo Opening your StockChecker Dashboard in Google Chrome...

:: Try to launch Chrome directly
start chrome "https://kennethsimons62.github.io/StockChecker/"

:: If the above doesn't work (e.g., Chrome isn't your default), 
:: the next line ensures it opens in whatever browser is available.
if %ERRORLEVEL% NEQ 0 start https://kennethsimons62.github.io/StockChecker/

exit