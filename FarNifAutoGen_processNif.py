
import logging
import sys
import os
from pyffi.formats.nif import NifFormat
from pyffi.utils.mathutils import matvecMul
import pyffi.spells.nif.modify
import pyffi.spells.nif.fix
import pyffi.spells.nif.optimize

# global variables
##model_minx = None
##model_miny = None
##model_minz = None
##model_maxx = None
##model_maxy = None
##model_maxz = None
##model_radius = None
##block_count = None
##root0 = None
##output_filename_path = None

def init_logger():
#    print "init_logger() entered"
    pyffilogger = logging.getLogger("pyffi")
    loghandler = logging.StreamHandler()
    pyffilogger.setLevel(logging.ERROR)
    #loghandler.setLevel(logging.DEBUG)
    #logformatter = logging.Formatter("%(name)s:%(levelname)s:%(message)s")
    #loghandler.setFormatter(logformatter)
    #pyffilogger.addHandler(loghandler)
    return pyffilogger, loghandler

def shutdown_logger(pyffilogger, loghandler):
#    print "shutdown_logger() entered"
    #pyffilogger.removeHandler(loghandler)
    return

def init_paths(output_datadir_arg):
#    print "init_paths() entered"
    if "data/" in output_datadir_arg.lower() or "data\\" in output_datadir.lower():
        output_root = output_datadir_arg.lower().replace("data/","")
        output_root = output_root.replace("data\\","")
    else:
        output_root = output_datadir
    return output_root

def load_nif(input_filename):
#    print "load_nif() entered"
    fstream = open(input_filename, 'rb')
    x = NifFormat.Data()
    x.read(fstream)
    fstream.close()
    return x

def process_NiSourceTexture(block, dds_list):
#    print "process_NiSourceTexture() entered"
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
#        print "texture filename: " + texture_name1 + " is already lowres"
        return dds_list
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
 #   print "leaving process_NiSourceTexture()"   
    return dds_list

def process_NiTriShapeData(block, root0, model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz):
#    print "process_NiTriShapeData() entered"
    root_chain = root0.find_chain(block)
    refnode = None
    for node in root_chain:
        if isinstance(node, NifFormat.NiNode):
            refnode = node
    #       print "NiNode found in root chain: " + str(refnode.name)
            break
#        else:
#            print "no NiNodes found in root chain."
    #print "block chain: " + str(root_chain)
    if (refnode is None):
        print "process_NiTriShapeData(): ERROR! could not assign reference node in root chain"
        return model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz
    parent_node = root_chain[len(root_chain)-2]
    if isinstance(parent_node, NifFormat.NiAVObject):
        root_transform = root_chain[len(root_chain)-2].get_transform(refnode)
    else:
#        print "process_NiTriShapeData(): parent node does not have transform data, skipping block..."
        return model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz

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
#    print "leaving process_NiTriShapeData()"
    return model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz

def calc_model_minmax(model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz):
#    print "calc_model_minmax() entered"
    dx = abs(model_maxx - model_minx)
    dx2 = dx*dx
    dy = abs(model_maxy - model_miny)
    dy2 = dy*dy
    dz = abs(model_maxz - model_minz)
    dz2 = dz*dz
    model_radius = (dx2 + dy2 + dz2) ** 0.5
    model_radius = model_radius / 2
    print "calc_model_minmax: model radius = " + str(model_radius)
    return float(model_radius)

def optimize_nifdata(x):
#    print "optimize_nifdata() entered"
    print "optimizing Far Nif...."
    pyffi.spells.nif.modify.SpellDelVertexColorProperty(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelBSXFlags(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelStringExtraDatas(data=x).recurse()
    pyffi.spells.nif.fix.SpellDelTangentSpace(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelCollisionData(data=x).recurse()
    pyffi.spells.nif.modify.SpellDisableParallax(data=x).recurse()
    pyffi.spells.nif.optimize.SpellOptimizeGeometry(data=x).recurse()
#    print "leaving optimize_nifdata()"
    
def output_niffile(nifdata, input_filename, output_datadir):
#    print "output_niffile() entered"
    #compose output filename
    #output postfix to filename
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
    print "outputing: " + output_filename
    ostream = open(output_filename_path, 'wb')
    nifdata.write(ostream)
    ostream.close()
#    print "leaving output_niffile()"
    return output_filename_path

def output_ddslist(dds_list, output_root):
#    print "output_ddslist() entered"
#    print "texture list: " + str(dds_list)
    #rename and copy textures to output stem...
    lowres_list_filename = "lowres_list.job"
    ostream = open(output_root + lowres_list_filename, "a")
    for filename in dds_list:
        ostream.write(filename + "\n")
    ostream.close()
#    print "leaving output_ddslist()"
    
def processNif(input_filename, radius_threshold_arg=800.0, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None):
#    print "\n\nprocessNif() entered"
    # intialize globals
    dds_list = list()
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

    print "processNIF(): Processing " + input_filename + " ..."
    pyffilogger, loghandler = init_logger()
    output_root = init_paths(output_datadir_arg)

#    print "load_nif(input_filename)"
    nifdata = load_nif(input_datadir_arg + input_filename)
    index_counter = -1
    root0 = nifdata.roots[0]
    for root in nifdata.roots:
        index_counter = index_counter + 1
        root_count = index_counter
        for block in root.tree():
            index_counter = index_counter + 1
            block_count = index_counter
            if isinstance(block, NifFormat.NiSourceTexture):
#                print "process_NiSourceTexture(block)"
                dds_list = process_NiSourceTexture(block, dds_list)
            if isinstance(block, NifFormat.NiTriShapeData) or isinstance(block,NifFormat.NiTriStripsData):
#                print "process_NiTriShapeData(block)"
                model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz = process_NiTriShapeData(block, root0, model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz)
    if (model_minx is not None):
#        print "calling calc_model_minmax()"
        model_radius = calc_model_minmax(model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz)

    ref_scale = float(ref_scale)
    radius_threshold_arg = float(radius_threshold_arg)
        
#    print "DEBUG: model_radius = " + str(model_radius)
#    print "DEBUG: ref_scale = " + str(ref_scale)
#    print "DEBUG: radius_threshold_arg = " + str(radius_threshold_arg)
    
    # if radius too small, skip
#    print "DEBUG: radius=" + str(model_radius) + ", ref_scale=" + str(ref_scale)
    if (model_radius is None):
#        print "ERROR: no model_radius calculated, unsupported NIF file."
        do_output = -1
    elif (model_radius * ref_scale) < radius_threshold_arg:
#        print "DEBUG: model radius under threshold for [" + input_filename + "]"
        do_output = 0
    else:
        #output file....
        do_output = 1
#        print "calling optimize_nifdata(nifdata)"
        optimize_nifdata(nifdata)
#        print "calling output_niffile(nifdata, input_filename, output_datadir)"
        output_niffile(nifdata, input_filename, output_datadir_arg)
#        print "calling output_ddslist(dds_list)"
        output_ddslist(dds_list, output_root)
#    print "calling shutdown_logger()"
    shutdown_logger(pyffilogger, loghandler)
#    print "processNIF(): complete."
    return do_output

