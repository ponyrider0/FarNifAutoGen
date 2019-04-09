@echo off
REM =============================================================
REM Modify the set PYTHONEXE=... line below to point to your
REM python executable. Double-quotes must go around the
REM entire statement. ex: set "PYTHONEXE=C:\python26\python.exe"
REM
REM =============================================================
set "PYTHONEXE=C:\Python26\python.exe"


REM =============================================================
REM Modify BLENDEREXE=... to point to your blender executable.
REM Remember to place Double-quotes around the entire statement.
REM
REM =============================================================
set "BLENDEREXE=C:\Blender\blender.exe"
REM set "BLENDEREXE=C:\Program Files (x86)\Blender Foundation\Blender\blender.exe"


REM =============================================================
REM Modify GIMPEXE=... to point to your gimp executable.
REM Remember to place Double-quotes around the entire statement.
REM
REM =============================================================
set "GIMPEXE=C:\Program Files\GIMP 2\bin\gimp-console-2.8.exe"


REM =============================================================
REM FARNIFAUTOGEN_INPUT_DATADIR=... points to the folder 
REM which contains the the meshes and textures which you would like
REM to have generated into _Far.NIF files and lowres textures. 
REM
REM =============================================================
set "FARNIFAUTOGEN_INPUT_DATADIR=C:\SteamLibrary\steamapps\common\Oblivion\Data\"
REM set "FARNIFAUTOGEN_INPUT_DATADIR=C:\Games\bsacmd\out\"


REM =============================================================
REM FARNIFAUTOGEN_OUTPUT_DATADIR=... points to the folder 
REM which you would like FarNifAutoGen to place the generated
REM _Far.NIF files and lowres textures.
REM
REM =============================================================
set "FARNIFAUTOGEN_OUTPUT_DATADIR=C:\FarNifAutoGen.output\Data\"


REM =============================================================
REM NIF_JOBLIST_FILE=... points to the text file which contains
REM a list of NIF files which will be read for potential
REM generation into _Far.NIF files.
REM
REM =============================================================
REM set "NIF_JOBLIST_FILE=nif_list_morroblivion.job"
REM set "NIF_JOBLIST_FILE=nif_list_test_vivec_only.job"
set "NIF_JOBLIST_FILE=nif_list_morroblivion_bsa_replacer.job"
REM set "NIF_JOBLIST_FILE=nif_list_oblivion.job"

set "NIF_REDUCTION_SCALE=1.000"
set "DDS_REDUCTION_SCALE=0.250"
set "MODEL_RADIUS_THRESHOLD=400.0"

"%PYTHONEXE%" FarNifAutoGen_main.py
