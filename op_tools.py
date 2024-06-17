import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import EnumProperty
from bpy.app.translations import pgettext


class MIO3SST_OT_snap_to_bone(bpy.types.Operator):
    bl_idname = "mesh.mio3_snap_to_bone"
    bl_label = "Snapping a vertex to a bone"
    bl_description = "DESC Snapping a vertex to a bone"
    bl_options = {"REGISTER", "UNDO"}

    bone_type: EnumProperty(
        name="Type",
        items=[
            ("Weight", "Weight", ""),
            ("Near", "Position", ""),
        ],
        default="Weight",
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        obj.update_from_editmode()
        if not obj.find_armature():
            self.report({"ERROR"}, "Armature modifier not set")
            return {"CANCELLED"}
        if not obj.active_shape_key:
            self.report({"ERROR"}, "Register ShapeKey for Shrink")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_verts = [v for v in bm.verts if v.select]
        if obj.use_mesh_mirror_x:
            selected_verts.extend(find_symmetry_verts(selected_verts, bm.verts))

        selected_edges = [e for e in bm.edges if e.select]
        islands = get_islands(selected_edges, selected_verts)

        armature = obj.find_armature()

        for verts in islands:
            if self.bone_type == "Weight":
                bone = find_bone(obj, armature, verts)
            else:
                bone = find_bone_by_nearest(obj, armature, verts)

            if bone:
                bone_head = armature.matrix_world @ bone.head_local
                bone_tail = armature.matrix_world @ bone.tail_local
                bone_vec = bone_tail - bone_head

                for vert in verts:
                    vert_world_co = obj.matrix_world @ vert.co

                    vert_to_bone = vert_world_co - bone_head
                    proj_vec = vert_to_bone.project(bone_vec)
                    snapped_pos = bone_head + proj_vec

                    new_world_pos = vert_world_co.lerp(snapped_pos, 0.95)
                    vert.co = obj.matrix_world.inverted() @ new_world_pos

        bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


class MIO3SST_OT_align_to_bone(bpy.types.Operator):
    bl_idname = "mesh.mio3_align_to_bone"
    bl_label = "Align edge loops"
    bl_description = "DESC Align edge loops"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        obj.update_from_editmode()
        if obj.data.total_face_sel > 0:
            self.report({"ERROR"}, "Please select only edges")
            return {"CANCELLED"}
        if not obj.find_armature():
            self.report({"ERROR"}, "Armature modifier not set")
            return {"CANCELLED"}
        if not obj.active_shape_key:
            self.report({"ERROR"}, "Register ShapeKey for Shrink")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)

        armature = obj.find_armature()
        selected_edges = [e for e in bm.edges if e.select]
        if obj.use_mesh_mirror_x:
            selected_edges.extend(find_symmetry_edges(selected_edges, bm.edges, bm.verts))

        edge_loops = find_edge_loops(selected_edges)

        for loop in edge_loops:
            selected_verts = list(set(v for e in loop for v in e.verts))

            bone = find_bone(obj, armature, selected_verts)

            bone_matrix = armature.matrix_world @ bone.matrix_local
            center = sum([obj.matrix_world @ v.co for v in selected_verts], Vector()) / len(
                selected_verts
            )
            bone_matrix_inv = bone_matrix.inverted()

            for vert in selected_verts:
                vert_world_co = obj.matrix_world @ vert.co
                bone_space_co = bone_matrix_inv @ vert_world_co

                # 整列
                bone_space_center = bone_matrix_inv @ center
                bone_space_co.y = bone_space_center.y

                vert_world_co = bone_matrix @ bone_space_co
                vert.co = obj.matrix_world.inverted() @ vert_world_co

        bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


def find_symmetry_verts(selected_verts, verts):
    symm_verts = []
    kd = kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()
    for v in selected_verts:
        co = v.co
        symm_co = Vector((-co.x, co.y, co.z))
        co_find = kd.find(symm_co)
        if co_find is not None and co_find[2] < 0.0001:
            symm_vert = verts[co_find[1]]
            if symm_vert not in selected_verts:
                symm_verts.append(symm_vert)
    return symm_verts


def find_symmetry_edges(selected_edges, edges, verts):
    symm_edges = []
    kd = kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()
    for e in selected_edges:
        v1, v2 = e.verts
        symm_co1 = Vector((-v1.co.x, v1.co.y, v1.co.z))
        symm_co2 = Vector((-v2.co.x, v2.co.y, v2.co.z))
        co_find1 = kd.find(symm_co1)
        co_find2 = kd.find(symm_co2)
        if co_find1 is not None and co_find2 is not None:
            if co_find1[2] < 0.0001 and co_find2[2] < 0.0001:
                symm_v1 = verts[co_find1[1]]
                symm_v2 = verts[co_find2[1]]
                symm_edge = next(
                    (e for e in edges if symm_v1 in e.verts and symm_v2 in e.verts), None
                )
                if symm_edge is not None and symm_edge not in selected_edges:
                    symm_edges.append(symm_edge)
    return symm_edges


def get_islands(selected_edges, verts):
    islands = []
    while verts:
        v = verts.pop()
        island = {v}
        stack = [v]
        while stack:
            v = stack.pop()
            for e in v.link_edges:
                if e in selected_edges:
                    ov = e.other_vert(v)
                    if ov not in island:
                        island.add(ov)
                        stack.append(ov)
                        verts.remove(ov)
        islands.append(list(island))
    return islands


def find_edge_loops(selected_edges):
    edge_groups = []
    vertex_to_edge = {}

    for edge in selected_edges:
        for vertex in edge.verts:
            if vertex not in vertex_to_edge:
                vertex_to_edge[vertex] = []
            vertex_to_edge[vertex].append(edge)

    while selected_edges:
        edge_group = []
        edge = selected_edges.pop()
        edge_group.append(edge)

        queue = list(edge.verts)
        while queue:
            vertex = queue.pop(0)
            connected_edges = vertex_to_edge[vertex]
            for edge in connected_edges:
                if edge in selected_edges:
                    selected_edges.remove(edge)
                    edge_group.append(edge)
                    queue.extend(edge.verts)

        edge_groups.append(edge_group)
    return edge_groups


def find_bone(obj, armature, selected_verts):
    max_weight = 0
    max_bone = None

    for vert in selected_verts:
        mesh_vert = obj.data.vertices[vert.index]
        for group in mesh_vert.groups:
            weight = group.weight
            if weight > max_weight:
                bone_name = obj.vertex_groups[group.group].name
                bone = armature.data.bones.get(bone_name)
                if bone and bone.use_deform and not bone.hide:
                    max_weight = weight
                    max_bone = bone
    return max_bone


def find_bone_by_nearest(obj, armature, selected_verts):
    bone_head_coords, bone_tail_coords = find_bone_world_cos(armature)

    nearest_bone = None
    min_distance = float("inf")
    for vert in selected_verts:
        mesh_vert = obj.data.vertices[vert.index]
        vert_coord_world = obj.matrix_world @ mesh_vert.co
        for bone in bone_head_coords.keys():
            head_distance = (vert_coord_world - bone_head_coords[bone]).length
            tail_distance = (vert_coord_world - bone_tail_coords[bone]).length
            distance = min(head_distance, tail_distance)
            if distance < min_distance:
                min_distance = distance
                nearest_bone = bone

    return nearest_bone


def find_bone_world_cos(armature):
    armature_matrix_world = armature.matrix_world
    bone_head_coords = {}
    bone_tail_coords = {}
    for bone in armature.data.bones:
        if bone.use_deform and not bone.hide:
            bone_head_coords[bone] = armature_matrix_world @ bone.head_local
            bone_tail_coords[bone] = armature_matrix_world @ bone.tail_local
    return bone_head_coords, bone_tail_coords


def menu(self, context):
    self.layout.operator(
        MIO3SST_OT_snap_to_bone.bl_idname,
        text=pgettext(MIO3SST_OT_snap_to_bone.bl_label),
        icon="BONE_DATA",
    )
    self.layout.operator(
        MIO3SST_OT_align_to_bone.bl_idname,
        text=pgettext(MIO3SST_OT_align_to_bone.bl_label),
        icon="ANTIALIASED",
    )


classes = [
    MIO3SST_OT_snap_to_bone,
    MIO3SST_OT_align_to_bone,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
