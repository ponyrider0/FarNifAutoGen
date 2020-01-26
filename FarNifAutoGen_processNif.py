
import logging
import sys
import os
from pyffi.formats.nif import NifFormat
from pyffi.utils.mathutils import matvecMul
from pyffi.utils.mathutils import vecscalarMul
from pyffi.utils.mathutils import matMul
from pyffi.utils.mathutils import matTransposed
import pyffi.spells.nif.modify
import pyffi.spells.nif.fix
import pyffi.spells.nif.optimize
import pyffi.spells.nif

from pyffi.utils.tristrip import triangulate
from pyffi.utils.tristrip import stripify

import FarNifAutoGen_utils

Use_GL_MultiSample = False
SIDE = 1024
MultiSampleRate = 1
window_width = 128
window_height = 128

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


def process_NiTriShapeData(block, root, model_minmax_list):
#    print "process_NiTriShapeData() entered"

    model_minx = model_minmax_list[0]
    model_miny = model_minmax_list[1]
    model_minz = model_minmax_list[2]
    model_maxx = model_minmax_list[3]
    model_maxy = model_minmax_list[4]
    model_maxz = model_minmax_list[5]

    root_chain = root.find_chain(block)
    if not root_chain:
        raise Exception("ERROR: can't find root_chain")
    identity_matrix = [ [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1] ]
    global_matrix = identity_matrix
    # start with identity matrix
    for node in root_chain:
        if not isinstance(node, NifFormat.NiAVObject):
            continue
        local_matrix = node.get_transform()
#        print "Node.name: " + node.name
#        print local_matrix
        global_matrix = matMul(global_matrix, local_matrix.as_list())

    # FIX BUG IN MATVECMUL
    global_matrix = matTransposed(global_matrix)

    vert = block.vertices[0]
#    print "pre-transform"
#    print vert
    v = matvecMul(global_matrix, [vert.x, vert.y, vert.z, 1.0])
#    print "\npost-transform"
#    print v
#    exit(-1)
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
    #compose output filename
    #output postfix to filename
    output_filename = input_filename[:-4] + "_far.nif"
    output_filename_path = output_datadir + output_filename
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
    

##def processNif(input_filename, radius_threshold_arg=800.0, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None, decimation_ratio=0.8):
##    input_stream = open(input_filename, "rb")
##    returnval = processNifStream(input_stream, input_filename, radius_threshold_arg, ref_scale, input_datadir_arg, output_datadir_arg, decimation_ratio)
##    input_stream.close()
##    return returnval

def processNifStream(input_stream, input_filename, radius_threshold_arg=800.0, ref_scale=float(1.0), input_datadir_arg=None, output_datadir_arg=None, decimation_ratio=0.8, keep_border=False):
#    print "\n\nprocessNif() entered"
    # intialize globals
    model_has_alpha_prop = False
#    dds_list = list()
    dds_list = dict()

    model_minmax_list = [None, None, None, None, None, None]

    model_radius = None
    block_count = None
#    root0 = None
    output_filename_path = None

    print "processNIF(): Processing " + input_filename + " ..."
#    pyffilogger, loghandler = init_logger()
    output_root = init_paths(output_datadir_arg)

#=========== DISABLED until rewritten as class ===========
#    error_filename = output_root + "error_list.txt"

    UVController_workaround = False

    # global AlphaProperty sharable by all blocks in model
    alphablock = NifFormat.NiAlphaProperty()
    alphablock.flags = 32
    alphablock.threshold = 0

    block_decimation_list = list()

#    print "load_nif(input_filename)"
#    nifdata = load_nif(input_datadir_arg + input_filename)
    nifdata = load_nifstream(input_stream)

#    nifdata = cull_nifdata(nifdata)

    index_counter = -1
#    root0 = nifdata.roots[0]
#    current_transform = None
    for root in nifdata.roots:
        index_counter = index_counter + 1
        root_count = index_counter
#        current_transform = root.get_transform()
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
                    model_minmax_list = process_NiTriShapeData(block.data, root, model_minmax_list)
                    block_decimation_list.append(block)

    if (model_minmax_list[0] is not None):
#        print "calling calc_model_minmax()"
        model_radius = calc_model_radius_from_minmax(model_minmax_list)

    ref_scale = float(ref_scale)
    radius_threshold_arg = float(radius_threshold_arg)

#    nifdata = cull_nifdata(nifdata)

#    if UVController_workaround is True:
#        SpellDelTextures(data=nifdata).recurse()

#    pyffi.spells.nif.modify.SpellDelAnimation(data=nifdata).recurse()
#    pyffi.spells.nif.optimize.SpellCleanRefLists(data=nifdata).recurse()
    
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
            render_Billboard_textures(nifdata, model_minmax_list, input_filename, input_datadir_arg, output_datadir_arg)
            newroot = NifFormat.NiNode()
            newroot.name = "Scene Root"
#            nifdata.roots.append(newroot)

            billboard_alpha = NifFormat.NiAlphaProperty()
            billboard_alpha.flags = 4844
            billboard_alpha.threshold = 127
            BillboardAutoGen(input_filename, newroot, model_minmax_list, billboard_alpha)

            # create new nifdata stream and write to output file ....
            new_nifdata = NifFormat.Data(version=0x14000005, user_version=10)
            new_nifdata.roots = [newroot]
            output_niffile(new_nifdata, input_filename, output_datadir_arg)
            
        else:
            # decimate blocks (NiTriShape(Data) and NiTriStrips(Data) 
            for block in block_decimation_list:
                print "DEBUG: Decimating file[%s] block[#%s]..." % (input_filename, block.name)
                PMBlock(block.data, decimation_ratio, keep_border)
        
#        print "calling optimize_nifdata(nifdata)"
#        nifdata = optimize_nifdata(nifdata)
#        print "calling output_niffile(nifdata, input_filename, output_datadir)"
#        output_niffile(nifdata, input_filename, output_datadir_arg)
#        print "calling output_ddslist(dds_list)"
#        output_ddslist(dds_list, output_root)
        
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


from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL.EXT import texture_compression_s3tc as s3tc
import numpy
from pyffi.formats.dds import DdsFormat


def interpret_blendfunc(blendfunc):
    if blendfunc == 0:
        func_val = GL_ONE
    elif blendfunc == 1:
        func_val = GL_ZERO
    elif blendfunc == 2:
        func_val = GL_SRC_COLOR
    elif blendfunc == 3:
        func_val = GL_ONE_MINUS_SRC_COLOR
    elif blendfunc == 4:
        func_val = GL_DST_COLOR
    elif blendfunc == 5:
        func_val = GL_ONE_MINUS_DST_COLOR
    elif blendfunc == 6:
        func_val = GL_SRC_ALPHA
    elif blendfunc == 7:
        func_val = GL_ONE_MINUS_SRC_ALPHA
    elif blendfunc == 8:
        func_val = GL_DST_ALPHA
    elif blendfunc == 9:
        func_val = GL_ONE_MINUS_DST_ALPHA
    elif blendfunc == 10:
        func_val = GL_SRC_ALPHA_SATURATE

    return func_val


def interpet_alphafunc(alphafunc):
    if alphafunc == 0:
        func_val = GL_ALWAYS
    elif alphafunc == 1:
        func_val = GL_LESS
    elif alphafunc == 2:
        func_val = GL_EQUAL
    elif alphafunc == 3:
        func_val = GL_LEQUAL
    elif alphafunc == 4:
        func_val = GL_GREATER
    elif alphafunc == 5:
        func_val = GL_NOTEQUAL
    elif alphafunc == 6:
        func_val = GL_GEQUAL
    elif alphafunc == 7:
        func_val = GL_NEVER

    return func_val


def interpret_alpha_prop(prop):
    Mask_AlphaBlend_Enable = 0x1
    Mask_SourceBlend_Func = 0xF << 1
    Mask_DestBlend_Func = 0xF << 5
    Mask_AlphaTest_Enable = 0x1 << 9
    Mask_AlphaTest_Mode = 0x7 << 10
    Mask_NoSorter_Flag = 0x1 << 13

    flag_alpha_blend_enable = (prop.flags & Mask_AlphaBlend_Enable)
    flag_source_blend_func = (prop.flags & Mask_SourceBlend_Func) >> 1
    flag_dest_blend_func = (prop.flags & Mask_DestBlend_Func) >> 5
    flag_alpha_test_enable = (prop.flags & Mask_AlphaTest_Enable) >> 9
    flag_alpha_test_mode = (prop.flags & Mask_AlphaTest_Mode) >> 10
    flag_no_sorter_flag = (prop.flags & Mask_NoSorter_Flag) >> 13

    if flag_alpha_blend_enable:
        glEnable(GL_BLEND)
    else:
        glDisable(GL_BLEND)

    #force off
    glDisable(GL_BLEND)

    print "source_blend_func = " + hex(flag_source_blend_func)
    print "dest_blend_func = " + hex(flag_dest_blend_func)
    print "alpha_test_mode = " + hex(flag_alpha_test_mode)

    src_func = interpret_blendfunc(flag_source_blend_func)
    dest_func = interpret_blendfunc(flag_dest_blend_func)
    alpha_func = interpet_alphafunc(flag_alpha_test_mode)
    
    glBlendFunc(src_func, dest_func)
    threshold = prop.threshold / 255.
    glAlphaFunc(alpha_func, threshold)
        
    if flag_alpha_test_enable:
        glEnable(GL_ALPHA_TEST)
    else:
        glDisable(GL_ALPHA_TEST)

    return


def fbo2_init():
    fbo2 = GLuint()
    glGenFramebuffers(1, fbo2)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo2)

    # color texture buffer
    rgb_texture2 = GLuint()
    glGenTextures(1, rgb_texture2)
    glBindTexture(GL_TEXTURE_2D, rgb_texture2)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SIDE, SIDE, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, rgb_texture2, 0)

    # depth buffer
    depth_texture2 = GLuint()
    glGenTextures(1, depth_texture2)
    glBindTexture(GL_TEXTURE_2D, depth_texture2)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, SIDE, SIDE, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_texture2, 0)

    if not glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE:
        raise Exception('Framebuffer binding failed.  Press ENTER to exit.')

    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glBindTexture(GL_TEXTURE_2D, 0)

    return fbo2, rgb_texture2, depth_texture2


def fbo_init():
    fbo = GLuint()
    glGenFramebuffers(1, fbo)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)

    # color texture buffer
    rgb_texture = GLuint()
    glGenTextures(1, rgb_texture)
    if Use_GL_MultiSample:
        glBindTexture(GL_TEXTURE_2D_MULTISAMPLE, rgb_texture)
    else:
        glBindTexture(GL_TEXTURE_2D, rgb_texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
     
    if Use_GL_MultiSample:
        glTexImage2DMultisample( GL_TEXTURE_2D_MULTISAMPLE, 8, GL_RGBA8, SIDE, SIDE, True )
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D_MULTISAMPLE, rgb_texture, 0)
    else:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SIDE*MultiSampleRate, SIDE*MultiSampleRate, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, rgb_texture, 0)

    # depth buffer
    rbo = GLuint()
    glGenRenderbuffers(1, rbo);
    glBindRenderbuffer(GL_RENDERBUFFER, rbo);
    if Use_GL_MultiSample:
        glRenderbufferStorageMultisample(GL_RENDERBUFFER, 8, GL_DEPTH_COMPONENT, SIDE, SIDE);
    else:
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, SIDE*MultiSampleRate, SIDE*MultiSampleRate);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rbo);

    if not glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE:
        raise Exception('Framebuffer binding failed.  Press ENTER to exit.')

    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glBindRenderbuffer(GL_RENDERBUFFER, 0)

    return fbo


# Utility functions
def float_size(n=1):
    return sizeof(ctypes.c_float) * n

def pointer_offset(n=0):
    return ctypes.c_void_p(float_size(n))

def load_sourcetexture_block(block, texture_cache, has_alpha, has_parallax, input_datadir):
    # get texture filename
    texture_path = block.file_name
    filename = texture_path
    
    if block in texture_cache.keys():
        # return textureID
        ddsTexture = texture_cache[block]
#        print "*** Texture already cached. Binding texture for " + filename
        glBindTexture(GL_TEXTURE_2D, ddsTexture)
        return ddsTexture
        
    dds_has_alpha = has_alpha

    filename = filename.replace("\\", "/")
    print "Searching data sources for " + filename
#    fstream = open(input_datadir + filename, 'rb')
    fstream = FarNifAutoGen_utils.GetInputFileStream(filename)
    if fstream is None:
        return -1
    ddsdata = DdsFormat.Data()
    ddsdata.read(fstream)
    fstream.close()

    height = ddsdata.header.height
    width = ddsdata.header.width
    linear_size = ddsdata.header.linear_size
    mipmap_count = ddsdata.header.mipmap_count
    pixel_format = ddsdata.header.pixel_format
    fourCC = pixel_format.four_c_c
    texture_buffer = ddsdata.pixeldata.get_value()

    if fourCC == DdsFormat.FourCC.DXT1:
        components = 3
        blockSize = 8
    else:
        components = 4
        blockSize = 16

    if fourCC == DdsFormat.FourCC.DXT1:
        glformat = s3tc.GL_COMPRESSED_RGBA_S3TC_DXT1_EXT
    elif fourCC == DdsFormat.FourCC.DXT3:
        glformat = s3tc.GL_COMPRESSED_RGBA_S3TC_DXT3_EXT
    elif fourCC == DdsFormat.FourCC.DXT5:
        glformat = s3tc.GL_COMPRESSED_RGBA_S3TC_DXT5_EXT
    else:
        print "ERROR, unsupported format: " + hex(fourcc)
        raw_input("Press ENTER to Exit.")
        exit(-1)

    ddsTexture = GLuint()
    glGenTextures(1, ddsTexture)
    glBindTexture(GL_TEXTURE_2D, ddsTexture)
    glTextureParameteri(ddsTexture, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
#    glTextureParameteri(ddsTexture, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
    glTextureParameterf(ddsTexture, GL_TEXTURE_LOD_BIAS, -1.0)

    glTextureParameteri(ddsTexture, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
#    glTextureParameteri(ddsTexture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    offset = 0
    for level in xrange(mipmap_count):
        size = ((width+3)/4)*((height+3)/4)*blockSize
        glCompressedTexImage2D(GL_TEXTURE_2D, level, glformat, width, height,
                               0, size, texture_buffer[offset:offset+size])
        offset += size
        width /= 2
        height /= 2
        if width == 0:
            width = 1
        if height == 0:
            height = 1
        if offset >= len(texture_buffer):
            break;

#    print "Adding " + filename + " to cache..."
    texture_cache[block] = ddsTexture   
    return ddsTexture


def render_triangle_block_data(block, root, use_strips, fbo, mesh_cache, ddsTexture, RenderView):

    if block in mesh_cache:
        # skip vertex array creation, just composite transforms and draw vao
        print "*** Vertex Array already cached..."
    else:
        mesh_cache[block] = "placeholder"
    
    if block.has_vertices is False:
        return

    # prep draw to texture
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glBindTexture(GL_TEXTURE_2D, ddsTexture)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # insert camera rotations here....
    #top: no rotation
    if RenderView is "top":
        donothing = 1
    #front: rotate 90 around X
    if RenderView is "front":
        glRotatef(90, -1, 0, 0)
    #side: rotate 90 around X, rotate 90 around Z
    if RenderView is "side":
        glRotatef(90, -1, 0, 0)
        glRotatef(90, 0, 0, -1)

    root_chain = root.find_chain(block)
    if not root_chain:
        raise Exception("ERROR: can't find root_chain")
    for node in reversed(root_chain):
        if not isinstance(node, NifFormat.NiAVObject):
            continue
        node_matrix = node.get_transform().as_list()
#        print "node_matrix: "
#        print node_matrix
        glMultMatrixf(node_matrix)

    has_uv = False
    if len(block.uv_sets) > 0:
        has_uv = True
    if use_strips:
        glBegin(GL_TRIANGLE_STRIP)
        point_offset = 0
        for i in xrange(block.num_strips):
            strip_length = block.strip_lengths[i]
            for point_index in xrange(strip_length):
                vert_index = block.points[i][point_index]
                vert = block.vertices[vert_index]
                if has_uv:
                    uv = block.uv_sets[0][vert_index]
                    glTexCoord2f(uv.u, uv.v)                
                if block.has_vertex_colors:
                    color = block.vertex_colors[vert_index]
                    glColor4f(color.r, color.g, color.b, color.a)
                if block.has_normals:
                    normal = block.normals[vert_index]
                    glNormal3f(normal.x, normal.y, normal.z)
                glVertex3f(vert.x, vert.y, vert.z)
                point_offset += strip_length
        glEnd()
        
    else:
        glBegin(GL_TRIANGLES)
        for i in xrange(block.num_triangles):
    #        print "drawing triangle # " + str(i)
            triangle = block.triangles[i]
            for vert_index in [triangle.v_1, triangle.v_2, triangle.v_3]:
                vert = block.vertices[vert_index]
                if has_uv:
                    uv = block.uv_sets[0][vert_index]
                    glTexCoord2f(uv.u, uv.v)                
                if block.has_vertex_colors:
                    color = block.vertex_colors[vert_index]
                    glColor4f(color.r, color.g, color.b, color.a)
                if block.has_normals:
                    normal = block.normals[vert_index]
                    glNormal3f(normal.x, normal.y, normal.z)
                glVertex3f(vert.x, vert.y, vert.z)
        glEnd()
   
    return


def render_root_tree(root, RenderView, fbo, mesh_cache, texture_cache, input_datadir):

    for block in root.tree():
        if isinstance(block, NifFormat.NiTriShape) or isinstance(block, NifFormat.NiTriStrips):
#            print "Loading Tri-Node: " + block.name
            block_has_alpha_prop = False
            block_has_parallax = False
            sourcetextures_list = list()
            # 1. check for alpha property first
            for prop in block.get_properties():
                if isinstance(prop, NifFormat.NiAlphaProperty):
                    block_has_alpha_prop = True
                    # insert Alpha Function Tests Here...
                    interpret_alpha_prop(prop)
                if isinstance(prop, NifFormat.NiTexturingProperty):
                    if prop.apply_mode == 4:
                        block_has_parallax = True
                    if prop.has_base_texture:
                        if prop.base_texture is not None:
                            sourcetextures_list.append(prop.base_texture.source)
                    if prop.has_bump_map_texture:
                        if prop.bump_map_texture is not None:
                            sourcetextures_list.append(prop.bump_map_texture.source)

            # 2. then process any texture properties
            for sourcetexture in sourcetextures_list:
                if sourcetexture is not None:
                    ddsTexture = load_sourcetexture_block(sourcetexture, texture_cache, block_has_alpha_prop, block_has_parallax, input_datadir)

            # check for VertexData, calculate model_min/max if present
            if block.data is not None:
                use_strips = False
                if isinstance(block, NifFormat.NiTriStrips):
                    use_strips = True
                render_triangle_block_data(block.data, root, use_strips, fbo, mesh_cache, ddsTexture, RenderView)


def render_billboard_view(fbo, texture_cache, mesh_cache, RenderView, nifdata, input_filename, input_datadir, model_minmax_list):
    model_minx = model_minmax_list[0]
    model_miny = model_minmax_list[1]
    model_minz = model_minmax_list[2]
    model_maxx = model_minmax_list[3]
    model_maxy = model_minmax_list[4]
    model_maxz = model_minmax_list[5]

    if model_minx == model_maxx:
        model_maxx += 1
    if model_miny == model_maxy:
        model_maxy += 1
    if model_minz == model_maxz:
        model_maxz += 1
    
    # prepare for rendering...
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    if Use_GL_MultiSample:
        glViewport( 0, 0, SIDE, SIDE )
    else:    
        glViewport( 0, 0, SIDE*MultiSampleRate, SIDE*MultiSampleRate )
    glClearColor(1.0, 1.0, 1.0, 0.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

#    # top projection
    if RenderView is "top":
        glOrtho(model_minx, model_maxx, model_miny, model_maxy, model_minz-1000, model_maxz+1000)

    # front projection
    if RenderView is "front":
        glOrtho(model_minx, model_maxx, model_minz, model_maxz, model_maxy+1000, model_miny-1000)

    if RenderView is "side":
        glOrtho(model_miny, model_maxy, model_minz, model_maxz, model_minx, model_maxx)

    # step through all nodes...
    for root in nifdata.roots:       
        render_root_tree(root, RenderView, fbo, mesh_cache, texture_cache, input_datadir)


def save_fbo_to_file(texture_name, fbo, fbo2, rgb_texture2, depth_texture2, output_datadir):
    # copy to fbo2
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glBindFramebuffer(GL_READ_FRAMEBUFFER, fbo)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, fbo2)
    if Use_GL_MultiSample:
        glBlitFramebuffer(0, 0, SIDE, SIDE, 0, 0, SIDE, SIDE, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST)
    else:
        glBlitFramebuffer(0, 0, SIDE, SIDE, 0, 0, SIDE*MultiSampleRate, SIDE*MultiSampleRate, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST)

    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glBindTexture(GL_TEXTURE_2D, 0)
    glBindRenderbuffer(GL_RENDERBUFFER, 0)
    glFlush()

    #Obtain the color data in a numpy array
    glBindTexture(GL_TEXTURE_2D, rgb_texture2)
    color_str = glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE)
    glBindTexture(GL_TEXTURE_2D, 0)
    color_data = numpy.fromstring(color_str, dtype=numpy.uint8)
    color_data = color_data.reshape((SIDE,SIDE*4))
    color_data = numpy.flipud(color_data)

    for row_index in xrange(SIDE):
        offset_start = row_index * SIDE
        offset_end = offset_start + SIDE
        working_row = color_data

    rgb_dds = DdsFormat.Data()

    rgb_dds.header.flags.caps = 1
    rgb_dds.header.flags.height = 1
    rgb_dds.header.flags.width = 1
    rgb_dds.header.flags.pitch = 0
    rgb_dds.header.flags.pixel_format = 1
    rgb_dds.header.flags.mipmap_count = 0
    rgb_dds.header.flags.linear_size = 0

    rgb_dds.header.height = SIDE
    rgb_dds.header.width = SIDE
    rgb_dds.header.rgb_linear_size = 0
    rgb_dds.header.mipmap_count = 0

    rgb_dds.header.pixel_format.flags.alpha_pixels = 1
    rgb_dds.header.pixel_format.flags.four_c_c = 0
    rgb_dds.header.pixel_format.flags.rgb = 1

    rgb_dds.header.pixel_format.four_c_c = DdsFormat.FourCC.LINEAR
    rgb_dds.header.pixel_format.bit_count = 32
    rgb_dds.header.pixel_format.r_mask = 0xFF
    rgb_dds.header.pixel_format.g_mask = 0xFF00
    rgb_dds.header.pixel_format.b_mask = 0xFF0000
    rgb_dds.header.pixel_format.a_mask = 0xFF000000

    rgb_dds.pixeldata.set_value(color_data.tobytes())

    output_filename_path = output_datadir + texture_name
    folderPath = os.path.dirname(output_filename_path)
    try:
        if os.path.exists(folderPath) == False:
            os.makedirs(folderPath)
    except:
        debug_print("processNif() ERROR: could not create destination directory: " + str(folderPath))
#    print "outputing: " + texture_name

    fostream = open(output_filename_path, "wb")
    rgb_dds.write(fostream)
    fostream.close()

    return


def render_Billboard_textures(nifdata, model_minmax_list, input_filename, input_datadir, output_datadir):

    RenderView = "top"
    texture_cache = dict()
    mesh_cache = dict()

    doInit = False    
    # initialize glut, opengl ONLY IF NEEDED...
    try:
        glEnable(GL_TEXTURE_2D)
    except:
        doInit = True

    if doInit:
        glutInit()
        glutInitDisplayMode(GLUT_RGBA | GLUT_MULTISAMPLE)
        glutInitWindowSize(window_width, window_height)
        glutInitWindowPosition(0,0)
        window = glutCreateWindow("Billboard Texture Preview")

    fbo = fbo_init()
    fbo2, rgb_texture2, depth_texture2 = fbo2_init()

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)

    RenderView = "top"   
    render_billboard_view(fbo, texture_cache, mesh_cache, RenderView, nifdata, input_filename, input_datadir, model_minmax_list)
    texture_name = input_filename.lower().replace("\\", "/").replace(".nif", "Top.dds").replace("meshes/", "textures/lowres/")
    save_fbo_to_file(texture_name, fbo, fbo2, rgb_texture2, depth_texture2, output_datadir)

    RenderView = "front"   
    render_billboard_view(fbo, texture_cache, mesh_cache, RenderView, nifdata, input_filename, input_datadir, model_minmax_list)
    texture_name = texture_name.replace("Top.dds", "Front.dds")
    save_fbo_to_file(texture_name, fbo, fbo2, rgb_texture2, depth_texture2, output_datadir)

    RenderView = "side"   
    render_billboard_view(fbo, texture_cache, mesh_cache, RenderView, nifdata, input_filename, input_datadir, model_minmax_list)
    texture_name = texture_name.replace("Front.dds", "Side.dds")
    save_fbo_to_file(texture_name, fbo, fbo2, rgb_texture2, depth_texture2, output_datadir)

    return

def BillboardAutoGen(input_filename, root, model_minmax_list, alphablock, trunk_center=[0,0]):
    # TODO: remove existing meshes

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
    uv_set.append([0, 1])
    uv_set.append([1, 1])
    uv_set.append([1, 0])
    uv_set.append([0, 0])
    #back
    uv_set.append([0, 1])
    uv_set.append([1, 1])
    uv_set.append([1, 0])
    uv_set.append([0, 0])

    TrianglesA = []
    TrianglesA.append( [0, 1, 2]) # front
    TrianglesA.append( [0, 2, 3] )# front
    TrianglesA.append( [4, 6, 5]) # back
    TrianglesA.append( [4, 7, 6] )# back

    texture_name = input_filename.lower().replace("\\", "/").replace(".nif", "Front.dds").replace("meshes/", "textures/lowres/")
#    texture_name = "PLACEHOLDER"
    shape = makeTriShape(VertsA, TrianglesA, normals, uv_set, texture_name, alphablock)
    root.add_child(shape)
    
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

    texture_name = texture_name.replace("Front.dds", "Side.dds")
#    texture_name = "PLACEHOLDER"
    shape = makeTriShape(VertsB, TrianglesA, normals, uv_set, texture_name, alphablock)
    root.add_child(shape)



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
            
