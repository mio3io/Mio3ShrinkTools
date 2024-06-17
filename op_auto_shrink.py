import bpy
import bmesh
from mathutils import Vector
from bpy.props import EnumProperty, BoolProperty
from bpy.app.translations import pgettext
import time


class MIO3_OT_auto_shrink(bpy.types.Operator):
    bl_idname = "mio3.auto_shrink"
    bl_label = "Auto Shrink"
    bl_description = "DESC Auto Shrink"
    bl_options = {"REGISTER", "UNDO"}

    volume: BoolProperty(name="Leave the volume", default=True)
    selected: BoolProperty(name="Selected only", default=False)

    type: EnumProperty(
        name="優先",
        items=[
            ("snap", "Type Snap", ""),
            ("lerp", "Type Tnterpolation", ""),
        ],
        default="snap",
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None

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
        start_time = time.time()

        if context.active_object.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

        obj = context.active_object

        armature = obj.find_armature()
        obj_world_mat = obj.matrix_world
        obj_world_mat_inv = obj_world_mat.inverted()
        arm_world_mat = armature.matrix_world

        # 表示中のデフォームボーンを抽出
        selected_bones = [bone for bone in armature.data.bones if not bone.hide and bone.use_deform]

        if not selected_bones:
            self.report({"ERROR"}, "No deform bone shown")
            return {"CANCELLED"}

        # 事前計算
        vertex_weights = {}
        for vert in obj.data.vertices:
            vert_weights = {}
            for group in vert.groups:
                if group.group < len(obj.vertex_groups):
                    group_name = obj.vertex_groups[group.group].name
                    vert_weights[group_name] = group.weight
            vertex_weights[vert.index] = vert_weights

        bone_heads = [arm_world_mat @ bone.head_local for bone in selected_bones]
        bone_tails = [arm_world_mat @ bone.tail_local for bone in selected_bones]
        bone_vecs = [bone_tails[i] - bone_heads[i] for i in range(len(selected_bones))]

        bm = bmesh.from_edit_mesh(obj.data)

        for i, vert in enumerate(bm.verts):
            if self.selected and not vert.select:
                continue
            vert_world_co = obj_world_mat @ vert.co
            total_weighted_pos = Vector((0, 0, 0))
            total_weight = 0

            for j, bone in enumerate(selected_bones):
                if bone.name not in vertex_weights[i]:
                    continue

                weight = vertex_weights[i][bone.name]
                if weight > 0:
                    bone_head = bone_heads[j]
                    bone_tail = bone_tails[j]
                    bone_vec = bone_vecs[j]

                    dist_to_head_sq = (vert_world_co - bone_head).length_squared
                    dist_to_tail_sq = (vert_world_co - bone_tail).length_squared
                    if self.type == "lerp":
                        if len(bone.children) == 0:
                            snapped_pos = bone_head
                        else:
                            vert_to_bone = vert_world_co - bone_head
                            proj_vec = vert_to_bone.project(bone_vec)
                            snapped_pos = bone_head + proj_vec

                            if dist_to_head_sq < dist_to_tail_sq:
                                snapped_pos = bone_head.lerp(snapped_pos, weight)
                            else:
                                snapped_pos = bone_tail.lerp(snapped_pos, weight)
                    else:
                        if len(bone.children) == 0:
                            snapped_pos = bone_head
                        elif weight < 0.99:
                            if dist_to_head_sq < dist_to_tail_sq:
                                snapped_pos = bone_head
                            else:
                                snapped_pos = bone_tail
                        else:
                            vert_to_bone = vert_world_co - bone_head
                            proj_vec = vert_to_bone.project(bone_vec)
                            snapped_pos = bone_head + proj_vec

                    total_weighted_pos += snapped_pos * weight
                    total_weight += weight

            if total_weight > 0:
                factor = 0.95 if self.volume else 1
                vert.co = obj_world_mat_inv @ vert_world_co.lerp(
                    total_weighted_pos / total_weight, factor
                )

        bmesh.update_edit_mesh(obj.data)

        print(f"Time: {time.time() - start_time}")
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "volume")
        layout.prop(self, "selected")
        row = layout.row()
        row.prop(self, "type", expand=True)


def menu(self, context):
    self.layout.operator(
        MIO3_OT_auto_shrink.bl_idname,
        text=pgettext(MIO3_OT_auto_shrink.bl_label),
        icon="ARMATURE_DATA",
    )


classes = [MIO3_OT_auto_shrink]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
