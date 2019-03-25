import os
from shutil import copyfile
import pdb
import math
from gimpfu import *

# lowres - resize length to divide by 8 or length=64 min
# copy and rename 8x8_n.dds for use with lowres

specular_strength = 0.27
mgso_specular_fix = 25

log_messages = True
print_messages = True
if (os.environ.get("FARNIFAUTOGEN_OUTPUTROOT") is not None):
    outputRoot = os.environ["FARNIFAUTOGEN_OUTPUTROOT"] + "/"
else:
    outputRoot = "C:/"
output_dir = outputRoot + "FarNifAutoGen.output/data/textures/"
error_filename = outputRoot + "FarNifAutoGen.output/gimp_log.txt"

def debug_output(message):
    if (print_messages == True):
        gimp.message(message)
    if (log_messages == True):
        with open(error_filename, "a") as error_file:
            error_file.write(message + "\n")
            error_file.close()

# copy and rename "8x8_n.dds" to use as fake normalmap
def fake_normalmap_file(filedir, filename):
    # check for _n or _g in name
    if ("_n.dds" in filename.lower()) or ("_g.dds" in filename.lower()):
        return
    # create normal name
    normal_name = filename[:len(filename)-4] + "_n.dds"
    # check if exists, and delete
    if os.path.exists(filedir + normal_name):
        os.remove(filedir + normal_name)
    try:
        copyfile("8x8_n.dds", filedir + normal_name)
    except:
        debug_output("Error trying to create normalmap for: " + filename)
        return -1
        #pdb.gimp_quit(-1)


# - load image
# - reduce to 64 x ____
# - save as dds (dxt1?)
def resize_lowres(file_path):
    filename = os.path.basename(file_path)
    filedir = os.path.dirname(file_path) + "/"
    # load file
    #debug_output("DEBUG: loading: " + file_path + "...")
    try:
        image = pdb.gimp_file_load(file_path, filename)
    except:
        debug_output("ERROR trying to load: " + file_path + ", skipping...")
        return -1
        #pdb.gimp_quit(-1)
    use_width = False
    width = image.width
    height = image.height
    if (width < height):
        shortlength = width
        use_width = True
    else:
        shortlength = height
    if (shortlength <= 64):
        debug_output("DEBUG: image dimensions too small: [" + str(width) + " x " + str(height) + "], no need to scale.")
        # continue with save step to optimize format (dxt1)
    else:
        shortlength = shortlength / 8
        if (shortlength < 64):
            shortlength = 64
        # resize shortest dimension to div8 or minimum 64
        if (use_width == True):
            ratio = float(shortlength) / float(width)
            longlength = int(height * ratio)
            #debug_output("DEBUG: scaling to: [" + str(shortlength) + " x " + str(longlength) + "]...")
            pdb.gimp_image_scale(image, shortlength, longlength)
        else:
            ratio = float(shortlength) / float(height)
            longlength = int(width * ratio)
            #debug_output("DEBUG: scaling to: [" + str(longlength) + " x " + str(shortlength) + "]...")
            pdb.gimp_image_scale(image, longlength, shortlength)
    # save
    debug_output("DEBUG: saving: " + file_path + "...")
    pdb.file_dds_save(image, image.active_layer, #image, drawyable/layer
                      file_path, filename, #filename, raw-filename
                      1, # compression: 0=none, 1=bc1/dxt1, 2=bc2/dxt3, 3=bc3/dxt5, 4=BC3n/dxt5nm, ... 8=alpha exponent... 
                      1, # mipmaps: 0=no mipmaps, 1=generate mipmaps, 2=use existing mipmaps(layers)
                      0, # savetype: 0=selected layer, 1=cube map, 2=volume map, 3=texture array
                      0, # format: 0=default, 1=R5G6B5, 2=RGBA4, 3=RGB5A1, 4=RGB10A2
                      -1, # transparent_index: -1 to disable (indexed images only)
                      0, # filter for generated mipmaps: 0=default, 1=nearest, 2=box, 3=triangle, 4=quadratic, 5=bspline, 6=mitchell, 7=lanczos, 8=kaiser
                      0, # wrap-mode for generated mipmaps: 0=default, 1=mirror, 2=repeat, 3=clamp
                      0, # gamma_correct: use gamma corrected mipmap filtering
                      0, # srgb: use sRGB colorspace for gamma correction
                      2.2, # gamma: gamma value used for gamma correction (ex: 2.2)
                      1, # perceptual_metric: use a perceptual error metric during compression
                      0, # preserve_alpha_coverage: preserve alpha test coverage for alpha channel maps
                      0) # alpha_test_threshold: alpha test threshold value for which alpha test coverage should be preserved
    fake_normalmap_file(filedir, filename)
    gimp.delete(image)


def run(file_path):
    #gimp.message("Resizing lowres/lod texture...")
    resize_lowres(file_path)
    pdb.gimp_quit(0)


if __name__ == "__main__":
    debug_output("This is a GIMP utility script that is designed to only be called by another script.  Exiting.")

    
