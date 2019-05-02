
import logging
import sys
import os
from pyffi.formats.nif import NifFormat
from pyffi.utils.mathutils import matvecMul
from pyffi.utils.mathutils import vecscalarMul
from pyffi.utils.mathutils import matMul
import pyffi.spells.nif.modify
import pyffi.spells.nif.fix
import pyffi.spells.nif.optimize
import pyffi.spells.nif

from pyffi.utils.tristrip import triangulate
from pyffi.utils.tristrip import stripify

# PyProgMesh Path
if (os.environ.get("PYPROGMESH_HOME") is not None):
    progmesh_home = os.environ["PYPROGMESH_HOME"]
else:
    progmesh_home = "/."
sys.path.append(progmesh_home)
import pyprogmesh

class SpellDelTextures(pyffi.spells.nif.modify._SpellDelBranchClasses):
    SPELLNAME = "modify_deltextures"
    BRANCH_CLASSES_TO_BE_DELETED = (NifFormat.NiSourceTexture,
                                    NifFormat.NiTexturingProperty,)

def init_logger():
#    print "init_logger() entered"
    pyffilogger = logging.getLogger("pyffi.toaster")
    loghandler = logging.StreamHandler()
    pyffilogger.setLevel(logging.ERROR)
    #loghandler.setLevel(logging.DEBUG)
    #logformatter = logging.Formatter("%(name)s:%(levelname)s:%(message)s")
    #loghandler.setFormatter(logformatter)
    pyffilogger.addHandler(loghandler)
    return pyffilogger, loghandler

def shutdown_logger(pyffilogger, loghandler):
#    print "shutdown_logger() entered"
    pyffilogger.removeHandler(loghandler)
    return

def init_paths(output_datadir_arg):
#    print "init_paths() entered"
    if "data/" in output_datadir_arg.lower() or "data\\" in output_datadir.lower():
        output_root = output_datadir_arg.lower().replace("data/","")
        output_root = output_root.replace("data\\","")
    else:
        output_root = output_datadir
    return output_root

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

def load_nif(input_filename):
#    print "load_nif() entered"
    fstream = open(input_filename, 'rb')
    x = NifFormat.Data()
    x.read(fstream)
    fstream.close()
    return x

def load_nifstream(stream):
    x = NifFormat.Data()
    x.read(stream)
    return x

def process_NiSourceTexture(block, dds_list, has_alpha=False):
    dds_has_alpha = has_alpha
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
        dds_list[texture_name1] = dds_has_alpha
        block.file_name = texture_name1
    else:
        print "skipping, internal texture found: " + texture_name
 #   print "leaving process_NiSourceTexture()"   
    return dds_list

def process_NiTriShapeData(block, root0, model_minmax_list):
#    print "process_NiTriShapeData() entered"

    model_minx = model_minmax_list[0]
    model_miny = model_minmax_list[1]
    model_minz = model_minmax_list[2]
    model_maxx = model_minmax_list[3]
    model_maxy = model_minmax_list[4]
    model_maxz = model_minmax_list[5]

#    if model_minx is not None:
#        print "DEBUG: entering values...\nmodel_min: [%2f, %2f, %2f]\nmodel_max: [%2f, %2f, %2f]" % (model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz)
#        raw_input("Press ENTER...")

##    root_chain = root0.find_chain(block)
##    refnode = None
##    for node in root_chain:
##        if isinstance(node, NifFormat.NiNode):
##            refnode = node
##    #       print "NiNode found in root chain: " + str(refnode.name)
##            break
###        else:
###            print "no NiNodes found in root chain."
##    #print "block chain: " + str(root_chain)
##    if refnode is None:
##        print "process_NiTriShapeData(): WARNING: could not assign reference node in root chain"
###        return model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz
##    else:
##        parent_node = root_chain[len(root_chain)-2]
##        if isinstance(parent_node, NifFormat.NiAVObject):
##            root_transform = root_chain[len(root_chain)-2].get_transform(refnode)
##        else:
##            print "process_NiTriShapeData(): parent node does not have transform data, skipping block..."
##            return [model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz]

    root_chain = root0.find_chain(block)
    if not root_chain:
        raise Exception("ERROR: can't find root_chain")
    global_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
    # start with identity matrix
    for node in root_chain:
        if not isinstance(node, NifFormat.NiAVObject):
            continue
        rotation_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
        for i in range(3):
            for j in range(3):
                rotation_matrix[i][j] = node.rotation.as_list()[j][i]
        scale_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
        for i in range(3):
            scale_matrix[i][i] = node.scale
        translation_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
        for i in range(3):
            translation_matrix[i][3] = node.translation.as_list()[i]
        global_matrix = matMul(scale_matrix, global_matrix)
        global_matrix = matMul(rotation_matrix, global_matrix)
        global_matrix = matMul(translation_matrix, global_matrix)
        
##        local_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
##        for i in range(3):
##            for j in range(3):
##                local_matrix[i][j] = node.rotation.as_list()[i][j] * node.scale
##        for i in range(3):
##            local_matrix[i][3] = node.translation.as_list()[i]
##        # mulitply with root_matrix
##        global_matrix = matMul(global_matrix, local_matrix)        

    #print root_transform
#    print "DEBUG: transform matrix:\n %s" % (str(root_transform.get_inverse()))
##    print "global matrix = "
##    for i in range(4):
##        print "[ %2f, %2f, %2f, %2f ]" % (global_matrix[i][0], global_matrix[i][1], global_matrix[i][2], global_matrix[i][3])
##    raw_input("Press ENTER...")

    vert = block.vertices[0]
    v = matvecMul(global_matrix, [vert.x, vert.y, vert.z, 1.0])
    block_maxx = v[0]
    block_minx = v[0]
    block_maxy = v[1]
    block_miny = v[1]
    block_maxz = v[2]
    block_minz = v[2]
    for vert in block.vertices:
        v = matvecMul(global_matrix, [vert.x, vert.y, vert.z, 1.0])        
        block_maxx = max(block_maxx, v[0])
        block_maxy = max(block_maxy, v[1])
        block_maxz = max(block_maxz, v[2])
        block_minx = min(block_minx, v[0])
        block_miny = min(block_miny, v[1])
        block_minz = min(block_minz, v[2])

##    # transform coordinates to global model space
##    minvec = [block_minx, block_miny, block_minz, 1.0]
##    maxvec = [block_maxx, block_maxy, block_maxz, 1.0]
##    if refnode is not None:
##        print "DEBUG: multiplying bounds by transformation matrix"
##        minvec = matvecMul(root_transform.as_list(), minvec)
##        maxvec = matvecMul(root_transform.as_list(), maxvec)
##    if global_matrix is not None:
##        print "DEBUG: multiplying bounds by transformation matrix"
##        minvec = matvecMul(global_matrix, minvec)
##        maxvec = matvecMul(global_matrix, maxvec)

##    if (abs(minvec[3]-1.0) > 0.001) or (abs(maxvec[3]-1.0) > 0.001):
##        raise Exception("Scale of min/max vector is not 1, after matrix multiply by transform")
##        print "Dividing min/max vector by scale: %f, %f ..." % (minvec[3], maxvec[3])
##        minvec = vecscalarMul(minvec, 1/minvec[3])
##        maxvec = vecscalarMul(maxvec, 1/maxvec[3])
##        if (abs(minvec[3]-1) > 0.001) or (abs(maxvec[3]-1) > 0.001):
##            raise Exception("Scale of min/max vector is not 1, after matrix multiply by transform")
            
##    print "DEBUG: min/max block vectors:\nblock_minvec: %s\nblock_maxvec: %s" % (str(minvec), str(maxvec))
##    block_minx = minvec[0]
##    block_miny = minvec[1]
##    block_minz = minvec[2]
##    block_maxx = maxvec[0]
##    block_maxy = maxvec[1]
##    block_maxz = maxvec[2]
    
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
#    print "DEBUG: exiting values...\nmodel_min: [%2f, %2f, %2f]\nmodel_max: [%2f, %2f, %2f]" % (model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz)
#    raw_input("Press ENTER...")

    return [model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz]

def calc_model_radius_from_minmax(model_minmax_list):
#    print "calc_model_minmax() entered"
    model_minx = model_minmax_list[0]
    model_miny = model_minmax_list[1]
    model_minz = model_minmax_list[2]
    model_maxx = model_minmax_list[3]
    model_maxy = model_minmax_list[4]
    model_maxz = model_minmax_list[5]
    
    dx = abs(model_maxx - model_minx)
    dx2 = dx*dx
    dy = abs(model_maxy - model_miny)
    dy2 = dy*dy
    dz = abs(model_maxz - model_minz)
    dz2 = dz*dz
    model_radius = (dx2 + dy2 + dz2) ** 0.5
    model_radius = model_radius / 2
#    print "calc_model_minmax: model radius = " + str(model_radius)
    return float(model_radius)

def cull_nifdata(x):
#    print "culling Far Nif...."
    pyffi.spells.nif.modify.SpellDelVertexColorProperty(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelSpecularProperty(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelBSXFlags(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelStringExtraDatas(data=x).recurse()
    pyffi.spells.nif.fix.SpellDelTangentSpace(data=x).recurse()
#    pyffi.spells.nif.modify.SpellDelAnimation(data=x).recurse()
    pyffi.spells.nif.modify.SpellDelCollisionData(data=x).recurse()
    pyffi.spells.nif.modify.SpellDisableParallax(data=x).recurse()
    return x

def optimize_nifdata(x):
#    print "optimize_nifdata() entered"
#    pyffi.spells.nif.optimize.SpellOptimizeGeometry(data=x).recurse()
    toaster = pyffi.spells.nif.NifToaster()
    toaster.options["arg"] = -0.1
    spell = pyffi.spells.nif.optimize.SpellReduceGeometry(data=x, toaster=toaster)
#    spell.VERTEXPRECISION = -0.1
    spell.recurse()
#    print "leaving optimize_nifdata()"
    return x
    
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
        debug_print("processNif() ERROR: could not create destination directory: " + str(folderPath))
    print "outputing: " + output_filename
#    debug_print("outputting: " + output_filename)
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
    for filename, has_alpha in dds_list.items():
        if has_alpha is True:
            alpha_tag = "alpha=1"
        else:
            alpha_tag = "alpha=0"
        ostream.write(filename + "," + alpha_tag + "\n")
    ostream.close()
#    print "leaving output_ddslist()"

def postprocessNif(filename):
#    pyffilogger, loghandler = init_logger()
    input_stream = open(filename, "rb")
    nifdata = NifFormat.Data()
    nifdata.read(input_stream)
    input_stream.close()
    nifdata = cull_nifdata(nifdata)
    nifdata = optimize_nifdata(nifdata)
    output_stream = open(filename, "wb")
    nifdata.write(output_stream)
    output_stream.close()
#    shutdown_logger(pyffilogger, loghandler)
    print "PostProcessing(" + filename + ") complete."
    

def processNif(input_filename, radius_threshold_arg=800.0, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None, decimation_ratio=0.8):
    input_stream = open(input_filename, "rb")
    returnval = processNifStream(input_stream, input_filename, radius_threshold_arg, ref_scale, input_datadir_arg, output_datadir_arg, decimation_ratio)
    input_stream.close()
    return returnval

def processNifStream(input_stream, input_filename, radius_threshold_arg=800.0, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None, decimation_ratio=0.8, keep_border=False):
#    print "\n\nprocessNif() entered"
    # intialize globals
    model_has_alpha_prop = False
#    dds_list = list()
    dds_list = dict()

##    model_minx = None
##    model_miny = None
##    model_minz = None
##    model_maxx = None
##    model_maxy = None
##    model_maxz = None
    model_minmax_list = [None, None, None, None, None, None]

    model_radius = None
    block_count = None
    root0 = None
    output_filename_path = None

#    print "processNIF(): Processing " + input_filename + " ..."
#    pyffilogger, loghandler = init_logger()
    output_root = init_paths(output_datadir_arg)

#=========== DISABLED until rewritten as class ===========
#    error_filename = output_root + "error_list.txt"

    UVController_workaround = False

    # global AlphaProperty sharable by all blocks in model
    alphablock = NifFormat.NiAlphaProperty()
    alphablock.flags = 4844
    alphablock.threshold = 0

    block_decimation_list = list()

#    print "load_nif(input_filename)"
#    nifdata = load_nif(input_datadir_arg + input_filename)
    nifdata = load_nifstream(input_stream)
    nifdata = cull_nifdata(nifdata)
    index_counter = -1
    root0 = nifdata.roots[0]
    current_transform = None
    for root in nifdata.roots:
        index_counter = index_counter + 1
        root_count = index_counter
        current_transform = root.get_transform()
        for block in root.tree():
            index_counter = index_counter + 1
            block_count = index_counter
            if isinstance(block, NifFormat.NiBillboardNode):
                # do not autogen, unsupported NIF
                return -1
            if isinstance(block, NifFormat.NiUVController):
                # do not autogen, unsupported NIF
                print "processNIF(): WARNING: unsupported block type: NiUVController; removing texture as workaround...."
                UVController_workaround = True
            if isinstance(block, NifFormat.NiTextureTransformController):
                print "processNIF(): WARNING: unsupported block type: NiTextureTransformController; removing texture as workaround...."
                UVController_workaround = True
            if isinstance(block, NifFormat.NiTriShape) or isinstance(block, NifFormat.NiTriStrips):
                block_has_alpha_prop = False
                sourcetextures_list = list()
                # 1. check for alpha property first
                for prop in block.get_properties():
                    if isinstance(prop, NifFormat.NiAlphaProperty):
                        block_has_alpha_prop = True
                    if isinstance(prop, NifFormat.NiTexturingProperty):
                        if prop.has_base_texture:
                            if prop.base_texture is not None:
                                sourcetextures_list.append(prop.base_texture.source)
                        if prop.has_bump_map_texture:
                            if prop.bump_map_texture is not None:
                                sourcetextures_list.append(prop.bump_map_texture.source)
                        if prop.has_dark_texture:
                            if prop.dark_texture is not None:
                                sourcetextures_list.append(prop.dark_texture.source)
                        if prop.has_decal_0_texture:
                            if prop.decal_0_texture is not None:
                                sourcetextures_list.append(prop.decal_0_texture.source)
                        if prop.has_decal_1_texture:
                            if prop.decal_1_texture is not None:
                                sourcetextures_list.append(prop.decal_1_texture.source)
                        if prop.has_decal_2_texture:
                            if prop.decal_2_texture is not None:
                                sourcetextures_list.append(prop.decal_2_texture.source)
                        if prop.has_decal_3_texture:
                            if prop.decal_3_texture is not None:
                                sourcetextures_list.append(prop.decal_3_texture.source)
                        if prop.has_detail_texture:
                            if prop.detail_texture is not None:
                                sourcetextures_list.append(prop.detail_texture.source)
                        if prop.has_gloss_texture:
                            if prop.gloss_texture is not None:
                                sourcetextures_list.append(prop.gloss_texture.source)
                        if prop.has_glow_texture:
                            if prop.glow_texture is not None:
                                sourcetextures_list.append(prop.glow_texture.source)
                        if prop.has_normal_texture:
                            if prop.normal_texture is not None:
                                sourcetextures_list.append(prop.normal_texture.source)                                
                # 2. then process any texture properties
                for sourcetexture in sourcetextures_list:
                    if sourcetexture is not None:
                        do_nothing = True
#                        dds_list = process_NiSourceTexture(sourcetexture, dds_list, block_has_alpha_prop)
                # 3. now add alpha property if not preset
                if block_has_alpha_prop is False:
                    block.add_property(alphablock)
                # check for VertexData, calculate model_min/max if present
                if block.data is not None:
#                    model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz = process_NiTriShapeData(block.data, root0, model_minx, model_miny, model_minz, model_maxx, model_maxy, model_maxz)
                    model_minmax_list = process_NiTriShapeData(block.data, root0, model_minmax_list)
                    block_decimation_list.append(block)

    if (model_minmax_list[0] is not None):
#        print "calling calc_model_minmax()"
        model_radius = calc_model_radius_from_minmax(model_minmax_list)

    ref_scale = float(ref_scale)
    radius_threshold_arg = float(radius_threshold_arg)

#    nifdata = cull_nifdata(nifdata)
    if UVController_workaround is True:
        SpellDelTextures(data=nifdata).recurse()

    pyffi.spells.nif.modify.SpellDelAnimation(data=nifdata).recurse()
    pyffi.spells.nif.optimize.SpellCleanRefLists(data=nifdata).recurse()
    
    # if radius too small, skip
    print "DEBUG: radius=" + str(model_radius) + ", ref_scale=" + str(ref_scale)
    if (model_radius is None):
#        print "ERROR: no model_radius calculated, unsupported NIF file."
        do_output = -1
    elif (model_radius * ref_scale) < radius_threshold_arg:
        print "DEBUG: model radius under threshold for [" + input_filename + "]"
        do_output = 0
    else:
        #output file....
        do_output = 1

    do_output = 1
    if do_output == 1:
#        if "tree" in input_filename:
        if True:
            do_nothing = True
            newroot = NifFormat.NiNode()
            nifdata.roots.append(newroot)
            BillboardAutoGen(input_filename, newroot, model_minmax_list, alphablock)
        else:
            # decimate blocks (NiTriShape(Data) and NiTriStrips(Data) 
            for block in block_decimation_list:
                print "DEBUG: Decimating file[%s] block[#%s]..." % (input_filename, block.name)
                PMBlock(block.data, decimation_ratio, keep_border)
        
#        print "calling optimize_nifdata(nifdata)"
        nifdata = optimize_nifdata(nifdata)
#        print "calling output_niffile(nifdata, input_filename, output_datadir)"
        output_niffile(nifdata, input_filename, output_datadir_arg)
#        print "calling output_ddslist(dds_list)"
        output_ddslist(dds_list, output_root)
        
#    print "calling shutdown_logger()"
#    shutdown_logger(pyffilogger, loghandler)
#    print "processNIF(): complete."
    return do_output


def makeTriShape(verts, triangles, normals=None, uv_set=None, texture_name=None, alphablock=None):
    # Make NiTriShape Node
    shape = NifFormat.NiTriShape()
    # Add NiTriShapeData Node
    shape_data = NifFormat.NiTriShapeData()
    shape.data = shape_data
    shape_data.num_vertices = len(verts)
    shape_data.has_vertices = True
    shape_data.vertices.update_size()
    for i, v in enumerate(shape_data.vertices):
        v.x = verts[i][0]
        v.y = verts[i][1]
        v.z = verts[i][2]
    shape_data.update_center_radius()
    shape_data.num_triangles = len(triangles)
    shape_data.triangles.update_size()
    shape_data.set_triangles(triangles)
    if uv_set is not None:
        shape_data.num_uv_sets = 1
        shape_data.has_uv = True
        shape_data.uv_sets.update_size()
        for i,v in enumerate(shape_data.uv_sets[0]):
            v.u = uv_set[i][0]
            v.v = uv_set[i][1]
    if normals is not None:
        shape_data.has_normals = True
        shape_data.normals.update_size()
        for i, v in enumerate(shape_data.normals):
            v.x = normals[i][0]
            v.y = normals[i][1]
            v.z = normals[i][2]
    # Use existing? NiAlphaProperty
    if alphablock is not None:
        shape.add_property(alphablock)

    # Add NiTexturingProperty
    if texture_name is not None:
        textureprop = NifFormat.NiTexturingProperty()
        # Add Placeholder NiSourceTexture
        source = NifFormat.NiSourceTexture()
        source.use_external = 1
        source.file_name = texture_name
        textureprop.has_base_texture = True
        textureprop.base_texture.source = source
        shape.add_property(textureprop)

    return shape

def BillboardAutoGen(input_filename, root0, model_minmax_list, alphablock, trunk_center=[0,0]):
    model_minx = model_minmax_list[0]
    model_miny = model_minmax_list[1]
    model_minz = model_minmax_list[2]
    model_maxx = model_minmax_list[3]
    model_maxy = model_minmax_list[4]
    model_maxz = model_minmax_list[5]

    # Billboard A: X-Z Plane, Y=0
    VertsA = []
    #front
    VertsA.append( [model_minx, trunk_center[1], model_minz])
    VertsA.append( [model_maxx, trunk_center[1], model_minz])
    VertsA.append( [model_maxx, trunk_center[1], model_maxz])
    VertsA.append( [model_minx, trunk_center[1], model_maxz])
    #back (for use with reversed normals)
    VertsA.append( [model_minx, trunk_center[1], model_minz])
    VertsA.append( [model_maxx, trunk_center[1], model_minz])
    VertsA.append( [model_maxx, trunk_center[1], model_maxz])
    VertsA.append( [model_minx, trunk_center[1], model_maxz])

    TrianglesA = []
    TrianglesA.append( [0, 1, 2]) # front
    TrianglesA.append( [0, 2, 3] )# front
    TrianglesA.append( [4, 6, 5]) # back
    TrianglesA.append( [4, 7, 6] )# back
#    Normalset = []
    normals = []
    #front
    normals.append([0, -1, 0])
    normals.append([0, -1, 0])
    normals.append([0, -1, 0])
    normals.append( [0, -1, 0])
    #back
    normals.append([0, 1, 0])
    normals.append([0, 1, 0])
    normals.append([0, 1, 0])
    normals.append( [0, 1, 0])
#    UVset = []
    uv_set = []
    #front
    uv_set.append([0, 0])
    uv_set.append([-1, 0])
    uv_set.append([-1, 1])
    uv_set.append([0, 1])
    #back
    uv_set.append([0, 0])
    uv_set.append([1, 0])
    uv_set.append([1, 1])
    uv_set.append([0, 1])

    texture_name = input_filename.lower().replace("\\", "/").replace(".nif", "_billboard_front.dds").replace("meshes/", "textures/lowres/")
    shape = makeTriShape(VertsA, TrianglesA, normals, uv_set, texture_name, alphablock)
    root0.add_child(shape)
    
    # Billboard B: Y-Z Plane, X=0
    VertsB = []
    VertsB.append([trunk_center[0], model_miny, model_minz])
    VertsB.append([trunk_center[0], model_maxy, model_minz])
    VertsB.append([trunk_center[0], model_maxy, model_maxz])
    VertsB.append([trunk_center[0], model_miny, model_maxz])
    VertsB.append([trunk_center[0], model_miny, model_minz])
    VertsB.append([trunk_center[0], model_maxy, model_minz])
    VertsB.append([trunk_center[0], model_maxy, model_maxz])
    VertsB.append([trunk_center[0], model_miny, model_maxz])
    # Reuse Triangles
#    Normalset = []
    normals[0] = [1, 0, 0]
    normals[1] = [1, 0, 0]
    normals[2] = [1, 0, 0]
    normals[3] = [1, 0, 0]
    normals[4] = [-1, 0, 0]
    normals[5] = [-1, 0, 0]
    normals[6] = [-1, 0, 0]
    normals[7] = [-1, 0, 0]
#    UVset = []
    # Reuse UVset

    texture_name = texture_name.replace("_billboard_front.dds", "_billboard_back.dds")
    shape = makeTriShape(VertsB, TrianglesA, normals, uv_set, texture_name, alphablock)
    root0.add_child(shape)

def PMBlock(block, decimation_ratio, keep_border=False):
#    print "========================NEW BLOCK========================="
    verts = list()
    faces = list()
    PMSettings = pyprogmesh.ProgMeshSettings()
    if block.num_uv_sets > 0 or block.has_uv:
        PMSettings.ProtectTexture = True
#    if block.has_vertex_colors:
#        PMSettings.ProtectColor = True
    PMSettings.RemoveDuplicate = True
    PMSettings.KeepBorder = keep_border

    for i in range(0, len(block.vertices)):
        _v = block.vertices[i]
#        print "vertex: (%f, %f, %f)" % (_v.x, _v.y, _v.z)
        v = [_v.x, _v.y, _v.z]
        if block.num_uv_sets > 0 or block.has_uv:
            _uv = [block.uv_sets[0][i].u, block.uv_sets[0][i].v]
        else:
            _uv = None
        if block.has_normals:
            _normal = [block.normals[i].x, block.normals[i].y, block.normals[i].z]
        else:
            _normal = None
        if block.has_vertex_colors:
            _vc = [block.vertex_colors[i].r, block.vertex_colors[i].g, block.vertex_colors[i].b, block.vertex_colors[i].a]
        else:
            _vc = None
        verts.append(pyprogmesh.RawVertex(Position=v, UV=_uv, Normal=_normal, RGBA=_vc))

##    if isinstance(block, NifFormat.NiTriShapeData):
##        triangles = block.triangles
##    else:
    triangles = block.get_triangles()
        
    for i in range(0, len(triangles)):
        _t = triangles[i]
#        print "triangle: [%d, %d, %d]" % (_t.v_1, _t.v_2, _t.v_3)
#        f = [_t.v_1, _t.v_2, _t.v_3]
        faces.append(_t)
    print "PREP: old verts = %d, old faces = %d" % (len(verts), len(faces))
    print "Decimation Ratio: %f" % (decimation_ratio)
    pm = pyprogmesh.ProgMesh(len(verts), len(faces), verts, faces, PMSettings)
#    raw_input("Press ENTER to compute progressive mesh.")
    pm.ComputeProgressiveMesh()
#    raw_input("Press ENTER to perform decimation.")
    result = pm.DoProgressiveMesh(decimation_ratio)
    if result == 0:
        print "Decimation failed"
        return
    else:
        numVerts, verts, numFaces, faces = result[0], result[1], result[2], result[3]
        print "RESULTS: new verts = %d, new faces = %d" % (numVerts, numFaces)
        block.num_vertices = numVerts
        block.vertices.update_size()
        if block.num_uv_sets > 0 or block.has_uv:
            block.uv_sets.update_size()
        if block.has_normals:
            block.normals.update_size()
        if block.has_vertex_colors:
            block.vertex_colors.update_size()
        for i in range(0, numVerts):
            rawVert = verts[i]
            v = block.vertices[i]
            v.x = rawVert.Position[0]
            v.y = rawVert.Position[1]
            v.z = rawVert.Position[2]
            if block.num_uv_sets > 0 or block.has_uv:
                uv = block.uv_sets[0][i]
                uv.u = rawVert.UV[0]
                uv.v = rawVert.UV[1]
            if block.has_normals:
                normals = block.normals[i]
                normals.x = rawVert.Normal[0]
                normals.y = rawVert.Normal[1]
                normals.z = rawVert.Normal[2]
            if block.has_vertex_colors:
                vc = block.vertex_colors[i]
                vc.r = rawVert.RGBA[0]
                vc.g = rawVert.RGBA[1]
                vc.b = rawVert.RGBA[2]
                vc.a = rawVert.RGBA[3]

        if isinstance(block, NifFormat.NiTriShapeData):
            print "DEBUG: triangulating..."
            block.num_triangles = numFaces
            block.triangles.update_size()
            block.set_triangles(faces)
##            for i in range(0, numFaces):
##                triangle = faces[i]
##                t = block.triangles[i]
##                t.v_1 = triangle[0]
##                t.v_2 = triangle[1]
##                t.v_3 = triangle[2]
        else:
            print "DEBUG: stripifying..."
            strips = stripify(faces)
            block.num_strips = len(strips)
#            block.strips.update_size()
            block.set_strips(strips)
            
