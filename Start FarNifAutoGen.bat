@echo off
REM =============================================================
REM Modify the set PYTHONEXE=... line below to point to your
REM python executable. Double-quotes must go around the
REM entire statement. ex: set "PYTHONEXE=C:\python26\python.exe"
REM
REM =============================================================

set "PYTHONEXE=C:\Python26\python.exe"
REM set "BLENDEREXE=C:\Program Files (x86)\Blender Foundation\Blender\blender.exe"
set "GIMPEXE=C:\Program Files\GIMP 2\bin\gimp-console-2.8.exe"
set "BLENDEREXE=C:\Blender\blender.exe"

set "FARNIFAUTOGEN_INPUT_DATADIR=C:\SteamLibrary\steamapps\common\Oblivion\Data\"
set "FARNIFAUTOGEN_OUTPUT_DATADIR=C:\FarNifAutoGen.output\"

"%PYTHONEXE%" FarNifAutoGen_main.py
