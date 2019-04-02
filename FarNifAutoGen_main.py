import sys
import os.path
import multiprocessing
import subprocess
import time
import glob
import shutil

from os import listdir, makedirs
from os.path import isfile, join

import FarNifAutoGen_processNif
#from FarNifAutoGen_processNif import processNif
#from FarNifAutoGen_processNif import output_filename_path

# custom settings
#os.environ["BLENDEREXE"] = "C:/Blender/blender.exe"
#os.environ["FARNIFAUTOGEN_INPUT_DATADIR"] = "C:/Games/bsacmd/out/"
#os.environ["NIF_JOBLIST_FILE"] = "nif_list_vivec.job"
#os.environ["DDS_JOBLIST_FILE"] = "lowres_list.job"
multiprocessing_on = True

# set up user-defined settings
if (os.environ.get("NIF_JOBLIST_FILE") is not None):
    nif_list_jobfile = os.environ["NIF_JOBLIST_FILE"]
else:
    nif_list_jobfile = "nif_list.job"
if (os.environ.get("DDS_JOBLIST_FILE") is not None):
    dds_list_jobfile = os.environ["DDS_JOBLIST_FILE"]
else:
    dds_list_jobfile = "lowres_list.job"
if (os.environ.get("NIF_REDUCTION_SCALE") is not None):
    nif_reduction_scale = float(os.environ["NIF_REDUCTION_SCALE"])
else:
    nif_reduction_scale = 1.0
if (os.environ.get("DDS_REDUCTION_SCALE") is not None):
    dds_reduction_scale = float(os.environ["DDS_REDUCTION_SCALE"])
else:
    dds_reduction_scale = 0.5
if (os.environ.get("MODEL_RADIUS_THRESHOLD") is not None):
    model_radius_threshold = float(os.environ["MODEL_RADIUS_THRESHOLD"])
else:
    model_radius_threshold = 400.0
##print "DEBUG: nif_reduction_scale = " + str(nif_reduction_scale)
##print "DEBUG: dds_reduction_scale = " + str(dds_reduction_scale)
##print "DEBUG: model_radius_threshold = " + str(model_radius_threshold)
##raw_input("Press ENTER to continue...")

# global variables
nif_joblist = dict()
dds_joblist = list()
temp_lookup_file = "lookup_table.tmp"
exclusions_list_file = "exclusions_list_test.txt"

# set up input/output path variables
#input_root = "./"
#input_path = input_root + ""
if (os.environ.get("FARNIFAUTOGEN_INPUT_DATADIR") is not None):
    input_datadir = os.environ["FARNIFAUTOGEN_INPUT_DATADIR"]
    input_datadir = str(os.path.normpath(input_datadir)).replace("\\","/")
    last_char = input_datadir[-1:]
    if last_char is not '/' and last_char is not '\\':
        input_datadir = input_datadir + "/"
else:
#    input_datadir = "./data/"
    input_datadir = "C:/SteamLibrary/steamapps/common/Oblivion/Data/"
if "data/" in input_datadir.lower() or "data\\" in input_datadir.lower():
    input_root = input_datadir.lower().replace("data/","")
    input_root = input_root.replace("data\\","")
else:
    input_root = input_datadir

if (os.environ.get("FARNIFAUTOGEN_OUTPUT_DATADIR") is not None):
    output_datadir = os.environ["FARNIFAUTOGEN_OUTPUT_DATADIR"]
    output_datadir = str(os.path.normpath(output_datadir)).replace("\\","/")
    last_char = output_datadir[-1:]
    if last_char is not '/' and last_char is not '\\':
        output_datadir = output_datadir + "/"
else:
    output_datadir = "C:/FarNifAutoGen.output/data/"
if "data/" in output_datadir.lower() or "data\\" in output_datadir.lower():
    output_root = output_datadir.lower().replace("data/","")
    output_root = output_root.replace("data\\","")
else:
    output_root = output_datadir
#output_root = outputRoot + "FarNifAutoGen.output/"
#output_datadir = output_root + "data/"
##print "DEBUG: input_datadir = " + input_datadir
##print "DEBUG: input_root = " + input_root
##print "DEBUG: output_datadir = " + output_datadir
##print "DEBUG: output_root = " + output_root
##raw_input()
    
# set up executable path variables
if (os.environ.get("BLENDEREXE") is not None):
    blenderPath = os.environ["BLENDEREXE"]
else:
    blenderPath = "C:/Program Files (x86)/Blender Foundation/Blender/blender.exe"
if os.path.exists(blenderPath) == False:
    print "==================="
    print "ERROR: Blender was not found. Please set the BLENDEREXE variable to the path of your blender executable."
    print "==================="
    raw_input("Press ENTER to quit.")
    quit(-1)
if (os.environ.get("GIMPEXE") is not None):
    gimpPath = os.environ["GIMPEXE"]
else:
    gimpPath = "C:/Program Files/GIMP 2/bin/gimp-console-2.8.exe"
if os.path.exists(gimpPath) == False:
    print "==================="
    print "ERROR: GIMP was not found. Please set the GIMPEXE variable to the path of your blender executable."
    print "==================="
    raw_input("Press ENTER to quit.")
    quit(-1)

# set up helper-file variables
blenderFilename = "empty.blend"

# set up multiprocessing settings
try:
#    CPU_COUNT = 1
    CPU_COUNT = multiprocessing.cpu_count()
except NotImplementedError:
    CPU_COUNT = 1

# error reporting
error_filename = output_root + "error_list.txt"
def log_error(err_string):
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
    with open(error_filename, writemode) as error_file:
        error_file.write(err_string + "\n")
def debug_print(err_string):
    global error_filename
    print err_string
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
    with open(error_filename, writemode) as error_file:
        error_file.write(err_string + "\n")
        error_file.close()

# launch blender
def launchBlender(filename, reduction_scale_arg=0.95):
    if (reduction_scale_arg >= 1.0):
        debug_print("Blender PolyReduce(" + filename + "): reduction_scale >= 1.0.  Skipping file...")
        return -1
    in_file = filename
    conversion_script = "FarNifAutoGen_blender_polyreduce.py"
    ## LOAD BLENDER HERE....
    print "==================="
    print "starting blender..." + in_file
    print "==================="
    #raw_input("DEBUG: PRESS ENTER TO BEGIN")
    rc = subprocess.call([blenderPath, blenderFilename, "-p", "0", "0", "1", "1", "-P", conversion_script, "--", in_file,"--reduction_scale",str(reduction_scale_arg)])
    if (rc != 0):
        print "Unable to launch blender, logging error and skipping file..."
        # log error and continue
        error_list(in_file + " (launch error) could not start blender.")
        return -1
    else:
        return 0

# launch gimp
def launchGIMP(filename, reduction_scale_arg=0.125):
    scriptfile = "FarNifAutoGen_gimp_lowres"
    bootstrap = "import sys;sys.path=['.']+sys.path;import " + scriptfile + ";" + scriptfile + ".run('" + filename + "')"
#    bootstrap = "import sys;sys.path=['.']+sys.path;import " + scriptfile + ";" + scriptfile + ".run('" + filename + "', reduction_scale=" + reduction_scale_arg + ")"
    #debug_print("bootstrap=" + bootstrap)
    #print "====GIMP script bootstrap:=======\n" + bootstrap + "\n================\n"
    resultcode = subprocess.call([gimpPath, \
                          "-idf", "--batch-interpreter=python-fu-eval", \
                          "-b", bootstrap])
    if (resultcode != 0):
        debug_print("GIMP (" + filename + ") ERROR: function failed.")
        #print "ERROR: failed with resultcode=(" + str(resultcode) + ")"
        # log error and continue
#        debug_print(joblist + " failed: resultcode=(" + str(format(resultcode, '08x')) + ")\n")
        return -1
    else:
#        debug_print(joblist + " success.\n")
        return 0  

# launch gimp
def launchGIMP_jobpool(joblist_file, reduction_scale_arg=0.125):
    scriptfile = "FarNifAutoGen_gimp_lowres"
#    bootstrap = "import sys;sys.path=['.']+sys.path;import " + scriptfile + ";" + scriptfile + ".run_jobpool('" + joblist_file + "')"
    bootstrap = "import sys;sys.path=['.']+sys.path;import " + scriptfile + ";" + scriptfile + ".run_jobpool('" + joblist_file + "',reduction_scale=" + str(reduction_scale_arg) + ")"
    debug_print("bootstrap=" + bootstrap)
    #print "====GIMP script bootstrap:=======\n" + bootstrap + "\n================\n"
    resultcode = subprocess.call([gimpPath, \
                          "-idf", "--batch-interpreter=python-fu-eval", \
                          "-b", bootstrap])
    try:
        os.remove(joblist_file)
    except OSError:
        debug_print("OSError occured while trying to remove:" + output_root + temp_jobfile)
        raw_input("Press ENTER to continue.")

    if (resultcode != 0):
        debug_print("GIMP process_jobpool(" + joblist_file + ") ERROR: function failed.")
        #print "ERROR: failed with resultcode=(" + str(resultcode) + ")"
        # log error and continue
#        debug_print(joblist + " failed: resultcode=(" + str(format(resultcode, '08x')) + ")\n")
        return -1
    else:
#        debug_print(joblist + " success.\n")
        return 0  

def perform_job_processNif(filename):
    global input_datadir
    global output_datadir
    global model_radius_threshold
    global nif_reduction_scale

#    print "perform_job_test: filename = " + str(filename)
#    print "DEBUG: input_datadir= " + str(input_datadir)
#    print "DEBUG: output_datadir= " + str(output_datadir)
#    print "DEBUG: opening temp lookup table: " + temp_lookup_file
#    print "DEBUG: model_radius_threshold=" + str(model_radius_threshold)
#    print "DEBUG: nif_reduction_scale=" + str(nif_reduction_scale)
    lookup_stream = open(temp_lookup_file, "r")
    ref_scale = None
    for line in lookup_stream:
        if filename in line:
            key,ref_scale = line.split(':',1)
            break
    lookup_stream.close()    
    if ref_scale is None:
        print "ERROR: Could not parse lookup table! Quitting..."
        return
    if os.path.exists(input_datadir + filename):
#        print " file found, calling processNif()..."
        do_output = FarNifAutoGen_processNif.processNif(filename, radius_threshold_arg=model_radius_threshold, ref_scale=ref_scale, input_datadir_arg=input_datadir, output_datadir_arg=output_datadir)
        #... call blender polyreducer
        if do_output == 1:
            debug_print(" DEBUG: spawn Blender polyreducer... (placeholder)")
            ## ====== leave a TODO file to polyreduce file ======= ##
#            launchBlender(FarNifAutoGen_processNif.output_filename_path, reduction_scale_arg=nif_reduction_scale)
#                raw_input("Press ENTER to continue.")
        elif do_output == 0:
            debug_print("processNif(" + filename + "): model radius below user-defined threshold, skipping.")
#                print "processNIF failed."
        elif do_output == -1:
            debug_print("processNif(" + filename + "): unsupported file.  Skipping.")
    else:
        debug_print("processNif(" + filename + ") ERROR: file not found.")
    print "perform_job_processNif() complete. <============== "

def perform_job_test(filename):
    global input_datadir
    global nif_joblist
    global model_radius_threshold
    global output_datadir
    global nif_reduction_scale
    print "perform_job_test: filename = " + str(filename)
    print "DEBUG: " + str(input_datadir) + "," + str(len(nif_joblist)) + "," + str(model_radius_threshold) + "," + str(output_datadir)
    return


# main
def main():
    global nif_joblist
    
    print "Starting FarNifAutoGen..."

    # set up output_dir
    if os.path.exists(output_datadir) == False:
        os.makedirs(output_datadir)

    # reset dds_joblist
    if (os.path.exists(output_root + dds_list_jobfile)):
        os.remove(output_root + dds_list_jobfile)
        ddsjob_stream = open(output_root + dds_list_jobfile, "wb")
        ddsjob_stream.close()

    # read exclusions list file
    exclusions_list = list()
    if os.path.exists(exclusions_list_file):
        exclusions_list_stream = open(exclusions_list_file, "r")
        for line in exclusions_list_stream:
            line = line.lower().rstrip("\r\n")
            line = str(os.path.normpath(line))
            line = line.replace("\\","/")
            if line not in exclusions_list:
                exclusions_list.append(line)
        exclusions_list_stream.close()

    # read niflist.job
#    print "\n1a. Read the nif_list.job file"
    if not os.path.exists(nif_list_jobfile):
        print "joblist not found: " + nif_list_jobfile + ". Exiting."
        return()
    else:
        print "joblist found: " + nif_list_jobfile
    nifjob_stream = open(nif_list_jobfile, "r")
    for line in nifjob_stream:
        line = line.lower().rstrip("\r\n")
        nif_filename, ref_scale = line.split(',')
        nif_filename = str(os.path.normpath(nif_filename))
        nif_filename = nif_filename.replace("\\","/")
        if nif_filename in exclusions_list:
#            raw_input("EXCLUSIONS LIST TRIGGERED, press ENTER to continue.")
            continue
        if nif_joblist.get(nif_filename) == None:
            nif_joblist[nif_filename] = float(ref_scale)
        else:
            if ref_scale > nif_joblist[nif_filename]:
                nif_joblist[nif_filename] = float(ref_scale)
    nifjob_stream.close()

    if multiprocessing_on:
        #===== Multi-threaded processNif() =======
        lookup_stream = open(temp_lookup_file, "w")
        for key, value in nif_joblist.items():
            lookup_stream.write('%s:%s\n' % (key, value))
        lookup_stream.close()
        # convert nif_joblist to jobpool
        jobpool = list()
        for line in nif_joblist:
            jobpool.append(line)
        # run jobpool
    #    if jobpool_processNif(jobpool) == -1:
    #        print "ERROR: jobpool processNif() interrupted."
        print "DEBUG: CPU_COUNT = " + str(CPU_COUNT)
        print "DEBUG: jobpool size = " + str(len(jobpool))
        pool = multiprocessing.Pool(processes=CPU_COUNT)
        result = pool.map_async(perform_job_processNif, jobpool)
    #    result = pool.map_async(perform_job_test, jobpool)
        try:
            result.wait(timeout=99999999)
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            print "ERROR: jobpool processNif() interrupted."
    else:
        #======= Single-threaded processNif() ========
        for filename in nif_joblist:
    #        print "processing: " + input_datadir + filename + " ... using ref_scale=" + str(nif_joblist[filename])
            if os.path.exists(input_datadir + filename):
    #           print " file found, calling processNif()..."
                do_output = FarNifAutoGen_processNif.processNif(filename, radius_threshold_arg=model_radius_threshold, ref_scale=nif_joblist[filename], input_datadir_arg=input_datadir, output_datadir_arg=output_datadir)
                #... call blender polyreducer
                if do_output is True:
    #                print " DEBUG: spawn Blender polyreducer"
                    launchBlender(FarNifAutoGen_processNif.output_filename_path, reduction_scale_arg=nif_reduction_scale)
    #                raw_input("Press ENTER to continue.")
                else:
    #                print "processNIF failed."
                    debug_print("processNif(" + filename + "): skipping polyreduce().")
            else:
                debug_print("processNif(" + filename + ") ERROR: file not found.")


    # read ddslist.job (lowres_list.job)
#    print "\n2a. Read the dds job file: " + output_root + dds_list_jobfile
    if not os.path.exists(output_root + dds_list_jobfile):
        print "no dds joblist found. skipping dds processing step."
    else:
        print "dds joblist found."
        ddsjob_stream = open(output_root + dds_list_jobfile, "r")
        for line in ddsjob_stream:
            dds_filename = line.lower().rstrip("\r\n")
            dds_filename = str(os.path.normpath(dds_filename))
            dds_filename = dds_filename.replace("\\","/")
            if dds_filename not in dds_joblist:
                dds_joblist.append(dds_filename)
        ddsjob_stream.close()
        # for each dds, process dds
#        print "\n2b. For each dds, process the dds file"
        # copy source DDS files to output folder
        for line in dds_joblist:
            output_filename, tags = line.split(",", 1)
            output_filename = output_filename.replace("\\","/")
            input_filename = output_filename.replace("lowres/", "")
            if input_filename in exclusions_list:
#                raw_input("EXCLUSIONS LIST TRIGGERED (DDS), press ENTER to continue.")
                continue
#            print "process dds file: " + input_datadir + input_filename
            if os.path.exists(input_datadir + input_filename):
#                print "  file found."
                folderPath = os.path.dirname(output_datadir + output_filename)
                if os.path.exists(folderPath) == False:
                    os.makedirs(folderPath)
                try:
                    shutil.copy(input_datadir + input_filename, output_datadir + output_filename)
                except IOError:
                    debug_print("processDDS_joblist(" + input_filename + ") ERROR: copy file to output_datadir failed. Skipping to next file...")
                # call gimp resizer...
#                launchGIMP(output_datadir + output_filename)
            else:
#                print "  file not found, skipping"
                debug_print("processDDS_joblist(" + input_filename + ") ERROR: file not found.")
                continue
        # launch GIMP with joblist
        # generate temp joblist
        # TODO: split temp joblist into small pieces for multithreading
        temp_jobfile = dds_list_jobfile.replace(".job","-temp.job")
        ddsjob_stream = open(output_root + temp_jobfile, "w")
        for line in dds_joblist:
            ddsjob_stream.write(output_datadir + line + "\n")
        ddsjob_stream.close()
#        raw_input("Launching GIMP_jobpool....")
        normalized_filepath = str(os.path.normpath(output_root + temp_jobfile)).replace("\\","/")
        print "DEBUG: normalized_filepath=" + normalized_filepath
        launchGIMP_jobpool(normalized_filepath,reduction_scale_arg=dds_reduction_scale)
    # complete
    print "\nFarNifAutoGen complete.\n"
    raw_input("Press ENTER to close window.")

if __name__ == "__main__":
    main()



