"""Spells for optimizing nif files.

.. autoclass:: SpellCleanRefLists
   :show-inheritance:
   :members:

.. autoclass:: SpellMergeDuplicates
   :show-inheritance:
   :members:

.. autoclass:: SpellOptimizeGeometry
   :show-inheritance:
   :members:

.. autoclass:: SpellOptimize
   :show-inheritance:
   :members:

.. autoclass:: SpellDelUnusedBones
   :show-inheritance:
   :members:

"""

# --------------------------------------------------------------------------
# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2011, NIF File Format Library and Tools.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****
# --------------------------------------------------------------------------

from itertools import izip
import os.path # exists

from pyffi.formats.nif import NifFormat
from pyffi.utils import unique_map
import pyffi.utils.tristrip
import pyffi.utils.vertex_cache
import pyffi.spells
import pyffi.spells.nif
import pyffi.spells.nif.fix
import pyffi.spells.nif.modify
from pyffi.spells.nif.optimize import *

# localization
#import gettext
#_ = gettext.translation('pyffi').ugettext
_ = lambda msg: msg # stub, for now

# set flag to overwrite files
__readonly__ = False

# example usage
__examples__ = """* Standard usage:

    python niftoaster.py optimize /path/to/copy/of/my/nifs

* Optimize, but do not merge NiMaterialProperty blocks:

    python niftoaster.py optimize --exclude=NiMaterialProperty /path/to/copy/of/my/nifs
"""

class SpellOptimizeGeometry2(pyffi.spells.nif.NifSpell):
    """Optimize all geometries:
      - remove duplicate vertices
      - triangulate
      - recalculate skin partition
      - recalculate tangent space 
    """

    SPELLNAME = "opt_geometry"
    READONLY = False

    # spell parameters
    VERTEXPRECISION = 3
    NORMALPRECISION = 3
    UVPRECISION = 5
    VCOLPRECISION = 3

    def __init__(self, *args, **kwargs):
        pyffi.spells.nif.NifSpell.__init__(self, *args, **kwargs)
        # list of all optimized geometries so far
        # (to avoid optimizing the same geometry twice)
        self.optimized = []

    def datainspect(self):
        # do not optimize if an egm or tri file is detected
        filename = self.stream.name
        if (os.path.exists(filename[:-3] + "egm")
            or os.path.exists(filename[:-3] + "tri")):
            return False
        # so far, only reference lists in NiObjectNET blocks, NiAVObject
        # blocks, and NiNode blocks are checked
        return self.inspectblocktype(NifFormat.NiTriBasedGeom)

    def branchinspect(self, branch):
        # only inspect the NiAVObject branch
        return isinstance(branch, NifFormat.NiAVObject)

    def optimize_vertices(self, data):
        self.toaster.msg("removing duplicate vertices")
        # get map, deleting unused vertices
        return unique_map(
            vhash
            for i, vhash in enumerate(data.get_vertex_hash_generator(
                vertexprecision=self.VERTEXPRECISION,
                normalprecision=self.NORMALPRECISION,
                uvprecision=self.UVPRECISION,
                vcolprecision=self.VCOLPRECISION)))

    def branchentry(self, branch):
        """Optimize a NiTriStrips or NiTriShape block:
          - remove duplicate vertices
          - retriangulate for vertex cache
          - recalculate skin partition
          - recalculate tangent space 

        @todo: Limit the length of strips (see operation optimization mod for
            Oblivion!)
        """
        if not isinstance(branch, NifFormat.NiTriBasedGeom):
            # keep recursing
            return True

        if branch in self.optimized:
            # already optimized
            return False

        if branch.data.additional_data:
            # occurs in fallout nv
            # not sure how to deal with additional data
            # so skipping to be on the safe side
            self.toaster.msg(
                "mesh has additional geometry data"
                " which is not well understood: not optimizing")
            return False
    
        # we found a geometry to optimize

        # we're going to change the data
        self.changed = True

        # cover degenerate case
        if branch.data.num_vertices < 3 or branch.data.num_triangles == 0:
            self.toaster.msg(
                "less than 3 vertices or no triangles: removing branch")
            self.data.replace_global_node(branch, None)
            return False

        self.optimized.append(branch)

        # shortcut
        data = branch.data

        v_map, v_map_inverse = self.optimize_vertices(data)
        
        self.toaster.msg("(num vertices was %i and is now %i)"
                         % (len(v_map), len(v_map_inverse)))

        # optimizing triangle ordering
        # first, get new triangle indices, with duplicate vertices removed
        triangles = list(pyffi.utils.vertex_cache.get_unique_triangles(
            (v_map[v0], v_map[v1], v_map[v2])
            for v0, v1, v2 in data.get_triangles()))
#        old_atvr = pyffi.utils.vertex_cache.average_transform_to_vertex_ratio(
#            triangles)
#        self.toaster.msg("optimizing triangle ordering")
#        new_triangles = pyffi.utils.vertex_cache.get_cache_optimized_triangles(
#            triangles)
#        new_atvr = pyffi.utils.vertex_cache.average_transform_to_vertex_ratio(
#            new_triangles)
#        if new_atvr < old_atvr:
#            triangles = new_triangles
#            self.toaster.msg(
#                "(ATVR reduced from %.3f to %.3f)" % (old_atvr, new_atvr))
#        else:
#            self.toaster.msg(
#                "(ATVR stable at %.3f)" % old_atvr)            
        # optimize triangles to have sequentially ordered indices
        self.toaster.msg("optimizing vertex ordering")
        v_map_opt = pyffi.utils.vertex_cache.get_cache_optimized_vertex_map(
            triangles)
        triangles = [(v_map_opt[v0], v_map_opt[v1], v_map_opt[v2])
                      for v0, v1, v2 in triangles]
        # update vertex map and its inverse
        for i in xrange(data.num_vertices):
            try:
                v_map[i] = v_map_opt[v_map[i]]
            except IndexError:
                # found a trailing vertex which is not used
                v_map[i] = None
            if v_map[i] is not None:
                v_map_inverse[v_map[i]] = i
            else:
                self.toaster.logger.warn("unused vertex")
        try:
            new_numvertices = max(v for v in v_map if v is not None) + 1
        except ValueError:
            # max() arg is an empty sequence
            # this means that there are no vertices
            self.toaster.msg(
                "less than 3 vertices or no triangles: removing branch")
            self.data.replace_global_node(branch, None)
            return False
        del v_map_inverse[new_numvertices:]

        # use a triangle representation
        if not isinstance(branch, NifFormat.NiTriShape):
            self.toaster.msg("replacing branch by NiTriShape")
            newbranch = branch.get_interchangeable_tri_shape(
                triangles=triangles)
            self.data.replace_global_node(branch, newbranch)
            branch = newbranch
            data = newbranch.data
        else:
            data.set_triangles(triangles)

        # copy old data
        oldverts = [(v.x, v.y, v.z) for v in data.vertices]
        oldnorms = [(n.x, n.y, n.z) for n in data.normals]
        olduvs   = [[(uv.u, uv.v) for uv in uvset] for uvset in data.uv_sets]
        oldvcols = [(c.r, c.g, c.b, c.a) for c in data.vertex_colors]
        if branch.skin_instance: # for later
            oldweights = branch.get_vertex_weights()
        # set new data
        data.num_vertices = new_numvertices
        if data.has_vertices:
            data.vertices.update_size()
            for i, v in enumerate(data.vertices):
                old_i = v_map_inverse[i]
                v.x = oldverts[old_i][0]
                v.y = oldverts[old_i][1]
                v.z = oldverts[old_i][2]
        if data.has_normals:
            data.normals.update_size()
            for i, n in enumerate(data.normals):
                old_i = v_map_inverse[i]
                n.x = oldnorms[old_i][0]
                n.y = oldnorms[old_i][1]
                n.z = oldnorms[old_i][2]
        # XXX todo: if ...has_uv_sets...:
        data.uv_sets.update_size()
        for j, uvset in enumerate(data.uv_sets):
            for i, uv in enumerate(uvset):
                old_i = v_map_inverse[i]
                uv.u = olduvs[j][old_i][0]
                uv.v = olduvs[j][old_i][1]
        if data.has_vertex_colors:
            data.vertex_colors.update_size()
            for i, c in enumerate(data.vertex_colors):
                old_i = v_map_inverse[i]
                c.r = oldvcols[old_i][0]
                c.g = oldvcols[old_i][1]
                c.b = oldvcols[old_i][2]
                c.a = oldvcols[old_i][3]
        del oldverts
        del oldnorms
        del olduvs
        del oldvcols

        # update skin data
        if branch.skin_instance:
            self.toaster.msg("update skin data vertex mapping")
            skindata = branch.skin_instance.data
            newweights = []
            for i in xrange(new_numvertices):
                newweights.append(oldweights[v_map_inverse[i]])
            for bonenum, bonedata in enumerate(skindata.bone_list):
                w = []
                for i, weightlist in enumerate(newweights):
                    for bonenum_i, weight_i in weightlist:
                        if bonenum == bonenum_i:
                            w.append((i, weight_i))
                bonedata.num_vertices = len(w)
                bonedata.vertex_weights.update_size()
                for j, (i, weight_i) in enumerate(w):
                    bonedata.vertex_weights[j].index = i
                    bonedata.vertex_weights[j].weight = weight_i

            # update skin partition (only if branch already exists)
            if branch.get_skin_partition():
                self.toaster.msg("updating skin partition")
                if isinstance(branch.skin_instance,
                              NifFormat.BSDismemberSkinInstance):
                    # get body part indices (in the old system!)
                    triangles, trianglepartmap = (
                        branch.skin_instance.get_dismember_partitions())
                    maximize_bone_sharing = True
                    # update mapping
                    new_triangles = []
                    new_trianglepartmap = []
                    for triangle, trianglepart in izip(triangles, trianglepartmap):
                        new_triangle = tuple(v_map[i] for i in triangle)
                        # it could happen that v_map[i] is None
                        # these triangles are skipped
                        # see for instance
                        # falloutnv/meshes/armor/greatkhans/greatkhan_v3.nif
                        # falloutnv/meshes/armor/tunnelsnake01/m/outfitm.nif
                        if None not in new_triangle:
                            new_triangles.append(new_triangle)
                            new_trianglepartmap.append(trianglepart)
                    triangles = new_triangles
                    trianglepartmap = new_trianglepartmap
                else:
                    # no body parts
                    triangles = None
                    trianglepartmap = None
                    maximize_bone_sharing = False
                # use Oblivion settings
                branch.update_skin_partition(
                    maxbonesperpartition=18, maxbonespervertex=4,
                    stripify=False, verbose=0,
                    triangles=triangles, trianglepartmap=trianglepartmap,
                    maximize_bone_sharing=maximize_bone_sharing)

        # update morph data
        for morphctrl in branch.get_controllers():
            if isinstance(morphctrl, NifFormat.NiGeomMorpherController):
                morphdata = morphctrl.data
                # skip empty morph data
                if not morphdata:
                    continue
                # convert morphs
                self.toaster.msg("updating morphs")
                # check size and fix it if needed
                # (see issue #3395484 reported by rlibiez)
                # remap of morph vertices works only if
                # morph.num_vertices == len(v_map)
                if morphdata.num_vertices != len(v_map):
                    self.toaster.logger.warn(
                        "number of vertices in morph ({0}) does not match"
                        " number of vertices in shape ({1}):"
                        " resizing morph, graphical glitches might result"
                        .format(morphdata.num_vertices, len(v_map)))
                    morphdata.num_vertices = len(v_map)
                    for morph in morphdata.morphs:
                        morph.arg = morphdata.num_vertices # manual argument passing
                        morph.vectors.update_size()
                # now remap morph vertices
                for morph in morphdata.morphs:
                    # store a copy of the old vectors
                    oldmorphvectors = [(vec.x, vec.y, vec.z)
                                       for vec in morph.vectors]
                    for old_i, vec in izip(v_map_inverse, morph.vectors):
                        vec.x = oldmorphvectors[old_i][0]
                        vec.y = oldmorphvectors[old_i][1]
                        vec.z = oldmorphvectors[old_i][2]
                    del oldmorphvectors
                # resize matrices
                morphdata.num_vertices = new_numvertices
                for morph in morphdata.morphs:
                    morph.arg = morphdata.num_vertices # manual argument passing
                    morph.vectors.update_size()

        # recalculate tangent space (only if the branch already exists)
        if (branch.find(block_name='Tangent space (binormal & tangent vectors)',
                        block_type=NifFormat.NiBinaryExtraData)
            or (data.num_uv_sets & 61440)
            or (data.bs_num_uv_sets & 61440)):
            self.toaster.msg("recalculating tangent space")
            branch.update_tangent_space()

        # stop recursion
        return False


