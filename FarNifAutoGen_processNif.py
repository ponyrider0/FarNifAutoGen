
import logging
import sys
import os
from pyffi.formats.nif import NifFormat
from pyffi.utils.mathutils import matvecMul
import pyffi.spells.nif.modify
import pyffi.spells.nif.fix
import pyffi.spells.nif.optimize

# global variables
model_minx = None
model_miny = None
model_minz = None
model_maxx = None
model_maxy = None
model_maxz = None
model_radius = None
block_count = None
root0 = None
output_filename_path = None

def init_logger():
    global pyffilogger
    global loghandler
    pyffilogger = logging.getLogger("pyffi")
    loghandler = logging.StreamHandler()
    pyffilogger.setLevel(logging.ERROR)
    #loghandler.setLevel(logging.DEBUG)
    #logformatter = logging.Formatter("%(name)s:%(levelname)s:%(message)s")
    #loghandler.setFormatter(logformatter)
    #pyffilogger.addHandler(loghandler)

def shutdown_logger():
    print ""
    #pyffilogger.removeHandler(loghandler)

def init_paths(input_datadir_arg=None, output_datadir_arg=None):
    global output_root
    global output_datadir
    global input_datadir
    if input_datadir_arg is not None:
        input_datadir = input_datadir_arg
    else:
        input_datadir = "./"
    if output_datadir_arg is None:
        output_root = "C:/FarNifAutoGen.output/"
        output_datadir = output_root + "Data/"
    else:
        output_datadir = output_datadir_arg
        if "data/" in output_datadir_arg.lower():
            output_root = output_datadir_arg[:-len("data/")]
        else:
            print "processNIF(): WARNING: output_datadir_arg does not contain a \"Data/\" directory, using output_data for output_root."
            output_root = output_datadir
    if not os.path.exists(output_datadir):
        os.makedirs(output_datadir)

def load_nif(input_filename):
    global input_datadir
#    input_filename = 'meshes/floraUbcUtreeU01.nif'
    fstream = open(input_datadir+input_filename, 'rb')
    x = NifFormat.Data()
    x.read(fstream)
    fstream.close()
    #print x
    return x

def process_NiSourceTexture(block):
    global dds_list
    # get texture filename
    texture_name = block.file_name
    # prefix "/lowres/"
    texture_name1 = texture_name.replace("\\","/").lower()
    if texture_name1.startswith("textures/"):
        texture_name1 = texture_name1[len("textures/"):]
    else:
        print "no textures/ prefix found"
        if texture_name1[0] == '/':
            texture_name1 = texture_name1[1:]
    if "lowres/" in texture_name1:
    #   print "texture filename: " + texture_name1 + " is already lowres"
        return()
    else:
        texture_name1 = "textures/lowres/" + texture_name1
    #   postfix "_lowres.dds"
    #   if texture_name1.endswith(".dds"):
    #       texture_name1 = texture_name1[:-len(".dds")] + "_lowres.dds"
    if (block.use_external is 1):
        if texture_name1 not in dds_list:
            dds_list.append(texture_name1)
        block.file_name = texture_name1
    else:
        print "skipping, internal texture found: " + texture_name

def process_NiTriShapeData(block):
    global model_minx
    global model_miny
    global model_minz
    global model_maxx
    global model_maxy
    global model_maxz
    global root0
    print "TriShapeData at index:" + str(block_count)
    root_chain = root0.find_chain(block)
    refnode = None
    for node in root_chain:
        if isinstance(node, NifFormat.NiNode):
            refnode = node
    #       print "NiNode found in root chain: " + str(refnode.name)
            break
        else:
            print "no NiNodes found in root chain."
    #print "block chain: " + str(root_chain)
    root_transform = root_chain[len(root_chain)-2].get_transform(refnode)
    #print root_transform
    block_maxx = block_minx = block.vertices[0].x
    block_maxy = block_miny = block.vertices[0].y
    block_maxz = block_minz = block.vertices[0].z
    for v in block.vertices:
        block_maxx = max(block_maxx, v.x)
        block_maxy = max(block_maxy, v.y)
        block_maxz = max(block_maxz, v.z)
        block_minx = min(block_minx, v.x)
        block_miny = min(block_miny, v.y)
        block_minz = min(block_minz, v.z)
    # transform coordinates to global model space
    minvec = [block_minx, block_miny, block_minz, 1]
    maxvec = [block_maxx, block_maxy, block_maxz, 1]
    minvec = matvecMul(root_transform.as_list(), minvec)
    maxvec = matvecMul(root_transform.as_list(), maxvec)
    block_minx = minvec[0]
    block_miny = minvec[1]
    block_minz = minvec[2]
    block_maxx = maxvec[0]
    block_maxy = maxvec[1]
    block_maxz = maxvec[2]
    # update model min/max values
    if (model_minx is None):
        #initialize model min/max
        model_minx = block_minx
        model_miny = block_miny
        model_minz = block_minz
        model_maxx = block_maxx
        model_maxy = block_maxy
        model_maxz = block_maxz
    else:
        model_minx = min(model_minx, block_minx)
        model_miny = min(model_miny, block_miny)
        model_minz = min(model_minz, block_minz)
        model_maxx = max(model_maxx, block_maxx)
        model_maxy = max(model_maxy, block_maxy)
        model_maxz = max(model_maxz, block_maxz)

def calc_model_minmax():
    global model_radius
    global model_minx
    global model_miny
    global model_minz
    global model_maxx
    global model_maxy
    global model_maxz
    #print "model min-max:"
    #print "(%s, %s, %s)" %(model_minx, model_miny, model_minz)
    #print "(%s, %s, %s)" % (model_maxx, model_maxy, model_maxz)
    dx = abs(model_maxx - model_minx)
    dx2 = dx*dx
    dy = abs(model_maxy - model_miny)
    dy2 = dy*dy
    dz = abs(model_maxz - model_minz)
    dz2 = dz*dz
    model_radius = (dx2 + dy2 + dz2) ** 0.5
    model_radius = model_radius / 2
    print "model radius = " + str(model_radius)

def optimize_nifdata(nifdata):
    print "optimizing Far Nif...."
    x = nifdata
    pyffi.spells.nif.modify.SpellDelVertexColorProperty(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelBSXFlags(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelStringExtraDatas(data=x).recurse()
    pyffi.spells.nif.fix.SpellDelTangentSpace(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelCollisionData(data=x).recurse()
    pyffi.spells.nif.modify.SpellDisableParallax(data=x).recurse()
    pyffi.spells.nif.optimize.SpellOptimizeGeometry(data=x).recurse()

def output_niffile(nifdata, input_filename):
    #compose output filename
    #output postfix to filename
    global output_path
    global output_filename_path
    x = nifdata
    output_filename = input_filename[:-4] + "_far.nif"
    output_filename_path = output_datadir + output_filename
#    print "output local path: " + output_filename
#    print "output file path: " + output_filename_path
    folderPath = os.path.dirname(output_filename_path)
    try:
        if os.path.exists(folderPath) == False:
            os.makedirs(folderPath)
    except:
        print "processNif() ERROR: could not create destination directory: " + folderPath
#        error_list(in_file + "Export ERROR: could not create destination directory: " + folderPath)    
##    output_dirs = output_filename.split("/")
##    output_string_path = output_datadir
##    for dir_string in output_dirs:
##        if "_far.nif" in dir_string:
##            break
##        else:
##            output_string_path = output_string_path + dir_string + "/"
##            if not os.path.exists(output_string_path):
##                os.mkdir(output_string_path)
    #print output filename
    #export to output filename
    print "outputing: " + output_filename
    ostream = open(output_filename_path, 'wb')
    x.write(ostream)
    ostream.close()

def output_ddslist():
    global dds_list
    global output_root
    print "texture list: " + str(dds_list)
    #rename and copy textures to output stem...
    lowres_list_filename = "lowres_list.job"
    ostream = open(output_root + lowres_list_filename, "a")
    for filename in dds_list:
        ostream.write(filename + "\n")
    ostream.close()

def processNif(input_filename, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None):
    global dds_list
    global model_radius
    global block_count
    global root0
    dds_list = list()
    print ""
    print "\nprocessNIF(): Processing " + input_filename + "..."
    print ""
    #global variables
    init_logger()
    init_paths(input_datadir_arg=input_datadir_arg, output_datadir_arg=output_datadir_arg)
    nifdata = load_nif(input_filename)
    index_counter = -1
    root0 = nifdata.roots[0]
    for root in nifdata.roots:
        index_counter = index_counter + 1
        root_count = index_counter
        for block in root.tree():
            index_counter = index_counter + 1
            block_count = index_counter
            if isinstance(block, NifFormat.NiSourceTexture):
                process_NiSourceTexture(block)
            if isinstance(block, NifFormat.NiTriShapeData):
                process_NiTriShapeData(block)
                calc_model_minmax()
    # if radius too small, skip
    if (model_radius * ref_scale) < 400.0:
        #don't output
        print "model radius under threshold, skipping"
        do_output = False
    else:
        #output file....
        do_output = True
        optimize_nifdata(nifdata)
        output_niffile(nifdata, input_filename)
        output_ddslist()
    shutdown_logger()
    print ""
    print "processNIF(): complete."
    print ""
    return do_output
