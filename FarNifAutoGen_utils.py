
import os
import sys
import os.path
import glob
import tempfile

from pyffi.formats.bsa import BsaFormat
import zlib

## ============ DISABLED until rewritten as class ===============
def log_error(err_string, error_filename="error_list.txt"):
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
#    with open(error_filename, writemode) as error_file:
#        error_file.write(err_string + "\n")
def debug_print(err_string, error_filename="error_list.txt"):
    print "=======> FarNifAutoGen_processNif.debug_print(): " + err_string + " <========="
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
#    with open(error_filename, writemode) as error_file:
#        error_file.write(err_string + "\n")
#        error_file.close()


user_option_dont_autoread_bsa = False
data_source_list_filename = "data_source_list.txt"
data_source_tempfilename = "lookup_datasources.tmp"
def Initialize_Data_Source_List(input_datadir):
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
