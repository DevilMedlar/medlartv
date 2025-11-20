@echo off
setlocal
set PRIVATE_REPO=C:\Users\znorr\medlartv
set PUBLIC_REPO=C:\Users\znorr\medlar-commands-site
set OUT_DIR=%PUBLIC_REPO%\docs
set PY=%PRIVATE_REPO%\.venv\Scripts\python.exe
if exist "%PY%" (
  "%PY%" "%PRIVATE_REPO%\MedlarTV\tools\build_commands_site.py" --out "%OUT_DIR%"
) else (
  python "%PRIVATE_REPO%\MedlarTV\tools\build_commands_site.py" --out "%OUT_DIR%"
)
pushd "%PUBLIC_REPO%"
git add docs
set CHANGES=
for /f "delims=" %%A in ('git status --porcelain') do set CHANGES=1
if "%CHANGES%"=="1" (
  git commit -m "Update commands"
  git push
)
popd
endlocal