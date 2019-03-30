@echo off
REM =============================================================
REM Modify the set PYTHONEXE=... line below to point to your
REM python executable. Double-quotes must go around the
REM entire statement. ex: set "PYTHONEXE=C:\python26\python.exe"
REM
REM =============================================================

set "PYTHONEXE=C:\Python26\python.exe"
REM set "BLENDEREXE=C:\Program Files (x86)\Blender Foundation\Blender\blender.exe"
set "BLENDEREXE=C:\Blender\blender.exe"
set "GIMPEXE=C:\Program Files\GIMP 2\bin\gimp-console-2.8.exe"

set "FARNIFAUTOGEN_INPUT_DATADIR=C:\Games\bsacmd\out\"
REM set "FARNIFAUTOGEN_INPUT_DATADIR=C:\SteamLibrary\steamapps\common\Oblivion\Data\"

set "FARNIFAUTOGEN_OUTPUT_DATADIR=C:\FarNifAutoGen.output\Data\"

set "NIF_JOBLIST_FILE=nif_list_morroblivion.job"

set "NIF_REDUCTION_SCALE=1.000"
set "DDS_REDUCTION_SCALE=0.250"
set "MODEL_RADIUS_THRESHOLD=400.0"

"%PYTHONEXE%" FarNifAutoGen_main.py
