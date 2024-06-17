import bpy
from . import op_auto_shrink
from . import op_tools

bl_info = {
    "name": "Mio3 Shrink Tools",
    "version": (0, 9),
    "blender": (3, 6, 0),
    "location": "View 3D > Sidebar > Edit Tab > Mio3 Shrink Tools",
    "description": "Support tools for shrink-shape keys",
    "category": "Mesh",
}


class MMIO3SST_PT_main(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Edit"
    bl_label = "Mio3 Shrink Tools"

    def draw(self, context):
        for op in ops:
            if hasattr(op, "menu"):
                op.menu(self, context)


def update_panel(self, context):
    is_exist = hasattr(bpy.types, "MMIO3SST_PT_main")
    category = bpy.context.preferences.addons[__package__].preferences.category
    if is_exist:
        try:
            bpy.utils.unregister_class(MMIO3SST_PT_main)
        except:
            pass

    MMIO3SST_PT_main.bl_category = category
    bpy.utils.register_class(MMIO3SST_PT_main)


class MMIO3SST_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    category: bpy.props.StringProperty(
        name="Tab Name",
        default="Edit",
        update=update_panel,
    )

    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "category")


translation_dict = {
    "en_US": {
        ("*", "DESC Auto Shrink"): "Automatically create shrink shape keys for deform bones\nHide bones you want to exclude, such as auxiliary bones and bust bones, in pause mode.",
        ("*", "DESC Snapping a vertex to a bone"): "Snap selected vertices to bones",
        ("*", "DESC Align edge loops"): "Align selected edge loops with respect to the bone coordinate Y axis",
    },
    "ja_JP": {
        ("*", "Auto Shrink"): "シュリンクシェイプキー用のサポートツール",

        ("*", "Auto Shrink"): "シュリンクを自動生成",
        ("*", "DESC Auto Shrink"): "デフォームボーンのシュリンクシェイプキーを自動的に作成\n補助ボーンや胸ボーンなど対象外にしたいボーンはポーズモードで隠してください",
        ("*", "Snapping a vertex to a bone"): "頂点をボーンにスナップ",
        ("*", "DESC Snapping a vertex to a bone"): "選択された頂点をボーンにスナップ",
        ("*", "Align edge loops"): "エッジループを整列",
        ("*", "DESC Align edge loops"): "選択されたエッジループをボーン座標Y軸に対して整列",

        ("*", "Leave the volume"): "ボリュームを残す",
        ("*", "Selected only"): "選択した頂点のみ",
        ("*", "Type Snap"): "スナップを優先",
        ("*", "Type Tnterpolation"): "スナップを優先",

        ("*", "Armature modifier not set"): "アーマチュアが設定されていません",
        ("*", "Register ShapeKey for Shrink"): "シュリンク用シェイプキーを登録してください",
        ("*", "Please select only edges"): "エッジのみ選択してください",
        ("*", "No deform bone shown"): "表示されているデフォームボーンがありません",
    }
}  # fmt: skip


ops = [
    op_auto_shrink,
    op_tools,
]


def register():
    bpy.app.translations.register(__name__, translation_dict)
    bpy.utils.register_class(MMIO3SST_Preferences)
    bpy.utils.register_class(MMIO3SST_PT_main)
    for op in ops:
        op.register()


def unregister():
    for op in reversed(ops):
        op.unregister()
    bpy.utils.unregister_class(MMIO3SST_PT_main)
    bpy.utils.unregister_class(MMIO3SST_Preferences)
    bpy.app.translations.unregister(__name__)


if __name__ == "__main__":
    register()
