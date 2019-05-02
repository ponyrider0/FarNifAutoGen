import os

# custom settings
#os.environ["FARNIFAUTOGEN_INPUT_DATADIR"] = "C:/Games/bsacmd/out/"
#os.environ["NIF_JOBLIST_FILE"] = "nif_list_test_vivec_only.job"
#os.environ["NIF_JOBLIST_FILE"] = "nif_list_morroblivion.job"
#os.environ["NIF_JOBLIST_FILE"] = "nif_list_testing.job"
#os.environ["DDS_JOBLIST_FILE"] = "lowres_list.job"
multiprocessing_on = False
os.environ["PYPROGMESH_HOME"] = "C:/dev/PyProgMesh/"

import sys
import os.path
import multiprocessing
import Queue
import subprocess
import time
import glob
import shutil
import tempfile

from os import listdir, makedirs
from os.path import isfile, join

from pyffi.formats.bsa import BsaFormat
import zlib

import FarNifAutoGen_processNif
#from FarNifAutoGen_processNif import processNif
#from FarNifAutoGen_processNif import output_filename_path

# PyProgMesh Path
if (os.environ.get("PYPROGMESH_HOME") is not None):
    progmesh_home = os.environ["PYPROGMESH_HOME"]
else:
    progmesh_home = "/."
sys.path.append(progmesh_home)
import pyprogmesh

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
    nif_reduction_scale = 0.9
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
exclusions_list_file = "exclusions_list.txt"
terrain_threshold_multiplier = 4.0
terrain_reduction_modifier = 0.25
#flora_threshold_multiplier = 4.0
flora_threshold_multiplier = 1.0
flora_reduction_modifier = 0.15

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


user_option_dont_autoread_bsa = False
data_source_list_filename = "data_source_list.txt"
data_source_tempfilename = "lookup_datasources.tmp"
def Initialize_Data_Source_List():
    data_source_list = list()
    data_source_dict = dict()
    cleaned_datadir = os.path.normpath(input_datadir).replace("\\","/").lower() + "/"
    if os.path.exists(cleaned_datadir):
        tags = "+nif+dds"
        print "Adding datasource: " + cleaned_datadir + "," + tags
        data_source_list.append(cleaned_datadir)
        data_source_dict[cleaned_datadir] = tags
    # read in data_sources file to priority_list
    if os.path.exists(data_source_list_filename):
        priority_stream = open(data_source_list_filename, "r")
        for raw_line in priority_stream:
            line = raw_line.lower().rstrip("\r\n")
            line = os.path.normpath(line).replace("\\","/")
            if "/" not in line:
                line = cleaned_datadir + line
            if os.path.exists(line) and line not in data_source_list:
                if os.path.isdir(line):
                    if line[len(line)-1] is not "/":
                        line = line + "/"
                    tags = "+nif+dds"
                    print "Adding datasource: " + line + "," + tags
                    data_source_list.append(line)
                    data_source_dict[line] = tags
                elif os.path.isfile(line):
                    # inspect bsa for nif and dds
                    bsa_stream = open(line, "rb")
                    bsa_data = BsaFormat.Data()
                    bsa_data.inspect(bsa_stream)
                    tags = ""
                    if bsa_data.file_flags.has_nif:
                        tags = "+nif"
                    if bsa_data.file_flags.has_dds:
                        tags = tags + "+dds"
                    if tags is not "":
                        print "Adding datasource: " + line + "," + tags
                        data_source_list.append(line)
                        data_source_dict[line] = tags
        priority_stream.close()
    if user_option_dont_autoread_bsa is True:
        skip_autoread = True
    else:
        for BSAfile in glob.glob(cleaned_datadir + "*.bsa"):
            line = os.path.normpath(BSAfile).lower().replace("\\","/")
            if line not in data_source_list:
                # inspect bsa for nif and dds
                bsa_stream = open(line, "rb")
                bsa_data = BsaFormat.Data()
                bsa_data.inspect(bsa_stream)
                tags = ""
                if bsa_data.file_flags.has_nif:
                    tags = "+nif"
                if bsa_data.file_flags.has_dds:
                    tags = tags + "+dds"
                if tags is not "":
                    print "Adding datasource: " + line + "," + tags
                    data_source_list.append(line)
                    data_source_dict[line] = tags
    # write data_source temp file
    data_source_tempstream = open(data_source_tempfilename,"w")
    for key in data_source_list:
        data_source_tempstream.write(key + "," + data_source_dict[key] + "\n")
    data_source_tempstream.close()

def GetInputFileStream(filename):
    # load lookup_datasource tempfile
    data_source_tempstream = open(data_source_tempfilename,"r")
    for raw_line in data_source_tempstream:
        line, tags = raw_line.rstrip("\r\n").split(",",1)
#        print "datasource: " + line
        if os.path.isdir(line):
            # search for filename directly from path
            if os.path.exists(line + filename):
                # copy to tempfile and return tempfile_object
                in_stream = open(line + filename, "rb")
                tempfile_stream = tempfile.TemporaryFile()                
                data = in_stream.read()
                tempfile_stream.write(data)
                in_stream.close()
                tempfile_stream.seek(0)
                data_source_tempstream.close()
                return tempfile_stream
            else:
                continue
        elif os.path.isfile(line):
            # search for filename in BSA
            # load bsa
            bsa_stream = open(line, "rb")
            bsa_data = BsaFormat.Data()
            bsa_data.inspect(bsa_stream)
            if ".nif" in filename.lower() and "nif" not in tags:
#                if bsa_data.file_flags.has_nif is False:
                    continue
            elif ".dds" in filename.lower() and "dds" not in tags:
#                if bsa_data.file_flags.has_dds is False:
                    continue
            bsa_is_compressed = bsa_data.archive_flags.is_compressed
            bsa_data.read(bsa_stream)
            for folder_block in bsa_data.folders:
                for file_block in folder_block.files:
                    bsa_filepath = folder_block.name + "/" + file_block.name
                    bsa_filepath = os.path.normpath(bsa_filepath).replace("\\","/").lower()
                    if bsa_filepath == filename:
                        # get stream to filepath
                        file_offset = file_block.offset
                        file_size = file_block.file_size.num_bytes
                        bsa_stream.seek(file_offset)
                        if file_block.file_size.is_compressed_override:
                            fileblock_is_compressed = not bsa_is_compressed
                        else:
                            fileblock_is_compressed = bsa_is_compressed
                        if fileblock_is_compressed:
                            file_originalsize = bsa_stream.read(4)
                            z_data = bsa_stream.read(file_size)
                            file_data = zlib.decompress(z_data)
                        else:
                            file_data = bsa_stream.read(file_size)
                        tempfile_stream = tempfile.TemporaryFile()
                        tempfile_stream.write(file_data)
                        bsa_stream.close()
                        tempfile_stream.seek(0)
                        data_source_tempstream.close()
                        return tempfile_stream
                    else:
                        continue
            bsa_stream.close()

    data_source_tempstream.close()
    # assume load failed
    debug_print("GetInputFileStream(" + filename + ") ERROR: could not load file from any data_source.")
    return None


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


def perform_job_processNif_safe(args):
    filename, ref_scale, mqueue = args[0][0], args[0][1], args[1]    
    try:
        perform_job_processNif(args)
    except Exception as e:
        # pass error back in queue
        mqueue.put(e)


#def perform_job_processNif(filename):
def perform_job_processNif(args):
#    print "perform_job_processNif() called: " + str(args)
    filename, ref_scale, mqueue = args[0][0], args[0][1], args[1]
    
    global input_datadir
    global output_datadir
    global model_radius_threshold
    global nif_reduction_scale

    tempfile_stream = GetInputFileStream(filename)
    if tempfile_stream is not None:

        keep_border = False
        if "terrain" in filename or "rock" in filename:
            mod_threshold = model_radius_threshold * terrain_threshold_multiplier
            mod_reduction = nif_reduction_scale - terrain_reduction_modifier
        elif "flora" in filename or "tree" in filename:
            mod_threshold = model_radius_threshold * flora_threshold_multiplier
            mod_reduction = nif_reduction_scale - flora_reduction_modifier
        else:
            mod_threshold = model_radius_threshold
            mod_reduction = nif_reduction_scale
            keep_border = True

        if nif_reduction_scale <= 0.50:
            mod_reduction = nif_reduction_scale
        
        do_output = FarNifAutoGen_processNif.processNifStream(tempfile_stream, filename, radius_threshold_arg=mod_threshold, ref_scale=ref_scale, input_datadir_arg=input_datadir, output_datadir_arg=output_datadir, decimation_ratio=mod_reduction, keep_border=keep_border)
        tempfile_stream.close()
        #... call blender polyreducer
        if do_output == 1:
            debug_print("DEBUG: processNif(" + filename + "): function successful.")
            mqueue.put(filename[:-4] + "_far.nif")
        elif do_output == 0:
            debug_print("processNif(" + filename + "): model radius below autogeneration threshold (" + str(mod_threshold) + "), skipping.")
        elif do_output == -1:
            debug_print("processNif(" + filename + "): unsupported file.  Skipping.")
    else:
        debug_print("processNif(" + filename + ") ERROR: file not found.")


def perform_job_prepareDDS(filename):
    line = filename
    output_filename, tags = line.split(",", 1)
    input_filename = output_filename.replace("lowres/", "")
    tempfile_stream = GetInputFileStream(input_filename)
    if tempfile_stream is not None:
        folderPath = os.path.dirname(output_datadir + output_filename)
        if os.path.exists(folderPath) == False:
            os.makedirs(folderPath)
        output_stream = open(output_datadir + output_filename, "wb")
        data = tempfile_stream.read()
        output_stream.write(data)
        output_stream.close()
        tempfile_stream.close()    
        debug_print("perform_job_prepareDDS(" + input_filename + "): DEBUG: extraction complete.")
    else:
#        print "perform_job_prepareDDS(" + input_filename + "): ERROR: file not found, skipping"
        debug_print("perform_job_prepareDDS(" + input_filename + ") ERROR: file not found.")

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

    # set up data_sources tempfile
    Initialize_Data_Source_List()

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
            debug_print("Exlusions List(" + nif_filename + "): exclusion detected, skipping.")
            continue
        if nif_joblist.get(nif_filename) == None:
            nif_joblist[nif_filename] = float(ref_scale)
        else:
            if ref_scale > nif_joblist[nif_filename]:
                nif_joblist[nif_filename] = float(ref_scale)
    nifjob_stream.close()

    if multiprocessing_on:
        #===== Multi-threaded processNif() =======
        manager = multiprocessing.Manager()
        mqueue = manager.Queue()
        print "DEBUG: CPU_COUNT = " + str(CPU_COUNT)
        print "DEBUG: jobpool size = " + str(len(nif_joblist))
        pool = multiprocessing.Pool(processes=CPU_COUNT)
        map_async_result = pool.map_async(perform_job_processNif_safe, [(x, mqueue) for x in nif_joblist.iteritems()])

        while not map_async_result.ready() or mqueue.qsize() > 0:
            try:
                mqueue_result = mqueue.get_nowait()
            except Queue.Empty:
                time.sleep(1)
                continue
            print "mqueue size = " + str(mqueue.qsize())

            if isinstance(mqueue_result, Exception):
                raise mqueue_result
            else:
                out_filename = mqueue_result
                if "terrain" in out_filename or "rock" in out_filename:
                    mod_reduction = nif_reduction_scale - terrain_reduction_modifier
                elif "flora" in out_filename or "tree" in out_filename:
                    mod_reduction = nif_reduction_scale - flora_reduction_modifier
                else:
                    mod_reduction = nif_reduction_scale
                FarNifAutoGen_processNif.postprocessNif(output_datadir + out_filename)
                
        try:
            map_async_result.wait(timeout=99999999)
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            print "ERROR: jobpool processNif() interrupted."

        while True:
            try:
                mqueue_result = mqueue.get_nowait()
            except Queue.Empty:
                break

            if isinstance(mqueue_result, Exception):
                raise mqueue_result
            else:
                out_filename = mqueue_result
                if "terrain" in out_filename or "rock" in out_filename:
                    mod_reduction = nif_reduction_scale - terrain_reduction_modifier
                elif "flora" in out_filename or "tree" in out_filename:
                    mod_reduction = nif_reduction_scale - flora_reduction_modifier
                else:
                    mod_reduction = nif_reduction_scale
                FarNifAutoGen_processNif.postprocessNif(output_datadir + out_filename)

    else:
        #======= Single-threaded processNif() ========
        for filename in nif_joblist:
            tempfile_stream = GetInputFileStream(filename)
            if tempfile_stream is not None:
                keep_border = False
                if "terrain" in filename or "rock" in filename:
                    mod_threshold = model_radius_threshold * terrain_threshold_multiplier
                    mod_reduction = nif_reduction_scale - terrain_reduction_modifier
                elif "flora" in filename or "tree" in filename:
                    mod_threshold = model_radius_threshold * flora_threshold_multiplier
                    mod_reduction = nif_reduction_scale - flora_reduction_modifier
                else:
                    mod_threshold = model_radius_threshold
                    mod_reduction = nif_reduction_scale
                    keep_border = True

                if nif_reduction_scale <= 0.50:
                    mod_reduction = nif_reduction_scale
                    
                do_output = FarNifAutoGen_processNif.processNifStream(tempfile_stream, filename, radius_threshold_arg=mod_threshold, ref_scale=nif_joblist[filename], input_datadir_arg=input_datadir, output_datadir_arg=output_datadir, decimation_ratio=mod_reduction, keep_border=keep_border)
                tempfile_stream.close()
                if do_output == 1:
                    out_filename = filename[:-4] + "_far.nif"
                elif do_output == 0:
                    debug_print("processNif(" + filename + "): below autogeneration threshold(" + str(mod_threshold) + ") : skipping polyreduce().")
                elif do_output == -1:
                    debug_print("processNif(" + filename + "): unsupported file : skipping polyreduce().")                    
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
                output_filename, tags = dds_filename.split(",", 1)
                input_filename = output_filename.replace("lowres/", "")
                if input_filename in exclusions_list:
                    debug_print("Exlusions List(" + input_filename + "): exclusion detected, skipping.")
#                    raw_input("EXCLUSIONS LIST TRIGGERED (DDS), press ENTER to continue.")
                    continue
                dds_joblist.append(dds_filename)
        ddsjob_stream.close()

        # copy source DDS files to output folder
        if not multiprocessing_on:
            # single-process
            for line in dds_joblist:
                output_filename, tags = line.split(",", 1)
                input_filename = output_filename.replace("lowres/", "")
    #            print "process dds file: " + input_datadir + input_filename
                tempfile_stream = GetInputFileStream(input_filename)
                if tempfile_stream is not None:
                    folderPath = os.path.dirname(output_datadir + output_filename)
                    if os.path.exists(folderPath) == False:
                        os.makedirs(folderPath)
                    output_stream = open(output_datadir + output_filename, "wb")
                    data = tempfile_stream.read()
                    output_stream.write(data)
                    output_stream.close()
                    tempfile_stream.close()
                    print "prepareDDS(" + input_filename + "): complete."
                else:
    #                print "  file not found, skipping"
                    debug_print("processDDS_joblist(" + input_filename + ") ERROR: file not found.")
                    continue
        else:
            # multi-threaded
            # use dds_joblist as jobpool
            dds_jobpool = list()
            for line in dds_joblist:
                dds_jobpool.append(line)
            dds_pool = multiprocessing.Pool(processes=CPU_COUNT)
            dds_result = dds_pool.map_async(perform_job_prepareDDS, dds_jobpool)
            try:
                dds_result.wait(timeout=99999999)
                dds_pool.close()
                dds_pool.join()
            except KeyboardInterrupt:
                print "ERROR: jobpool processNif() interrupted."

        temp_jobfile = dds_list_jobfile.replace(".job","-temp.job")
        ddsjob_stream = open(output_root + temp_jobfile, "w")
        for line in dds_joblist:
            ddsjob_stream.write(output_datadir + line + "\n")
        ddsjob_stream.close()
#        raw_input("Launching GIMP_jobpool....")
        normalized_filepath = str(os.path.normpath(output_root + temp_jobfile)).replace("\\","/")
#        print "DEBUG: normalized_filepath=" + normalized_filepath
        launchGIMP_jobpool(normalized_filepath,reduction_scale_arg=dds_reduction_scale)
    # complete
    print "\nFarNifAutoGen complete.\n"
    raw_input("Press ENTER to close window.")

if __name__ == "__main__":
    main()



