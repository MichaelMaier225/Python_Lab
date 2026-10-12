@echo off
color 0A
:title
setlocal EnableDelayedExpansion
:loop
set "line="
for /L %%i in (1,1,20) do (
    set /a rand=!random! %% 2
    if !rand! == 1 (
        set "line=!line!!random! "
    ) else (
        set "line=!line!!random:~0,1!!random:~1,1! "
    )
)
echo !line!
goto loop
