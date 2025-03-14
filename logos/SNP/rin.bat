@echo off
setlocal enabledelayedexpansion
for %%f in (* *) do (
    set "newname=%%f"
    set "newname=!newname: =-!"
    ren "%%f" "!newname!"
)
