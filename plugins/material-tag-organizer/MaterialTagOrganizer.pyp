"""
Material Tag Organizer

Tools for cleaning, merging, renaming and rebuilding Cinema 4D material tags
and polygon selections, with a workflow aimed at imported production assets.
"""

import c4d
import os
import re
from c4d import plugins, gui, bitmaps

# =================================================================
# 插件 ID
# =================================================================
PLUGIN_ID = 1060009

# =================================================================
#  UI 界面类
# =================================================================
class SettingsDialog(gui.GeDialog):
    GRP_MAIN = 1000
    GRP_OPTS = 1001
    GRP_BTNS = 1002
    
    CHK_ALL = 2000      
    CHK_CLEAN = 2001    # 1. 清理
    CHK_OPTIMIZE = 2002 # 2. 合并+整理
    
    BTN_EXECUTE = 3001
    BTN_CANCEL = 3002

    result_config = None

    def CreateLayout(self):
        self.SetTitle("Material Tag Organizer")
        
        self.GroupBegin(self.GRP_MAIN, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 1, 0, "", 0)
        self.GroupBorderSpace(15, 15, 15, 15)
        
        # --- 选项 ---
        self.GroupBegin(self.GRP_OPTS, c4d.BFH_SCALEFIT, 1, 0, "功能配置", c4d.BFV_TOP)
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(10, 10, 10, 10)
        
        self.AddCheckbox(self.CHK_ALL, c4d.BFH_LEFT, 0, 0, ">>> 全选功能 <<<")
        self.AddSeparatorH(c4d.BFH_SCALEFIT) 
        
        self.AddCheckbox(self.CHK_CLEAN, c4d.BFH_LEFT, 0, 0, "1. 深度清理 (移除一切无效选集 / SDS / 丢失材质)")
        
        self.AddCheckbox(self.CHK_OPTIMIZE, c4d.BFH_LEFT, 0, 0, "2. 智能合并 + 材质排序 + 标签重构")
        self.AddStaticText(0, c4d.BFH_LEFT, 0, 0, "    └─ 说明：数据备份后销毁旧标签，生成纯净新标签", 0)
        
        self.GroupEnd()
        
        # --- 按钮 ---
        self.GroupBegin(self.GRP_BTNS, c4d.BFH_SCALEFIT, 1, 0, "", 0)
        self.GroupBorderSpace(0, 15, 0, 0)
        self.AddButton(self.BTN_EXECUTE, c4d.BFH_SCALEFIT, 0, 30, "开始执行 (Run)")
        self.AddButton(self.BTN_CANCEL, c4d.BFH_SCALEFIT, 0, 30, "关闭 (Close)")
        self.GroupEnd()
        
        self.GroupEnd()
        return True

    def InitValues(self):
        self.SetBool(self.CHK_ALL, True)
        self.SetBool(self.CHK_CLEAN, True)
        self.SetBool(self.CHK_OPTIMIZE, True)
        return True

    def Command(self, id, msg):
        if id == self.CHK_ALL:
            val = self.GetBool(self.CHK_ALL)
            self.SetBool(self.CHK_CLEAN, val)
            self.SetBool(self.CHK_OPTIMIZE, val)
        
        if id in [self.CHK_CLEAN, self.CHK_OPTIMIZE]:
            all_on = (self.GetBool(self.CHK_CLEAN) and self.GetBool(self.CHK_OPTIMIZE))
            self.SetBool(self.CHK_ALL, all_on)

        if id == self.BTN_EXECUTE:
            self.result_config = {
                'clean': self.GetBool(self.CHK_CLEAN),
                'optimize': self.GetBool(self.CHK_OPTIMIZE)
            }
            self.Close()
        elif id == self.BTN_CANCEL:
            self.result_config = None
            self.Close()
        return True

# =================================================================
#  主逻辑类
# =================================================================
class ObjectOptimizer(plugins.CommandData):

    def Execute(self, doc):
        dlg = SettingsDialog()
        dlg.Open(c4d.DLG_TYPE_MODAL, defaultw=350, defaulth=260)
        if not dlg.result_config: return True
        self.RunOptimization(doc, dlg.result_config)
        return True

    def RunOptimization(self, doc, config):
        selection = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)
        doc.StartUndo()

        stats = {
            'merged': 0, 'objects': 0, 'cleaned': 0, 'organized': 0    
        }

        # 1. 全局材质合并 & 排序
        if config['optimize']:
            stats['merged'] = self.GlobalMergeMaterials(doc)
            self.SortAllMaterials(doc)

        # 2. 对象处理
        if selection:
            for op in selection:
                if not op.CheckType(c4d.Opolygon): continue
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, op)
                self.ProcessObject(op, config, stats)
                stats['objects'] += 1
        
        doc.EndUndo()
        c4d.EventAdd()

        # 反馈
        if stats['merged'] == 0 and stats['objects'] == 0:
            if config['optimize']:
                msg = "✅ 材质已排序。(未发现重复材质，未选中对象)"
            else:
                msg = "⚠️ 未选中对象。"
        else:
            msg = "✅ 优化完成！\n" + "-"*30 + "\n"
            if config['optimize']:
                msg += f"🔹 材质管理: 删除 {stats['merged']} 个重复项 + A-Z排序\n"
            if selection:
                msg += f"📦 处理对象: {stats['objects']} 个\n"
                if config['clean']:
                    msg += f"🧹 清理标签: {stats['cleaned']} 个 (含无效选集)\n"
                if config['optimize']:
                    msg += f"🎨 整理重构: 标签已销毁重建\n"
        gui.MessageDialog(msg)

    # ==========================================
    #  核心 A: 全局合并
    # ==========================================
    def GlobalMergeMaterials(self, doc):
        all_mats = []
        def collect(root):
            while root:
                all_mats.append(root)
                collect(root.GetDown())
                root = root.GetNext()
        collect(doc.GetFirstMaterial())

        if not all_mats: return 0

        groups = {}
        for m in all_mats:
            name = m.GetName()
            clean_name = re.sub(r"[\._\s]+\d+$", "", name).strip()
            if clean_name not in groups: groups[clean_name] = []
            groups[clean_name].append(m)

        remap = {} 
        deleted_count = 0
        for base_name, m_list in groups.items():
            if len(m_list) < 2: continue 
            m_list.sort(key=lambda x: len(x.GetName()))
            master = m_list[0]
            duplicates = m_list[1:]
            for dup in duplicates: remap[id(dup)] = master

        if not remap: return 0

        all_objs = []
        def collect_objs(op):
            while op:
                all_objs.append(op)
                collect_objs(op.GetDown())
                op = op.GetNext()
        collect_objs(doc.GetFirstObject())

        for obj in all_objs:
            for tag in obj.GetTags():
                if tag.CheckType(c4d.Ttexture):
                    mat = tag[c4d.TEXTURETAG_MATERIAL]
                    if mat and id(mat) in remap:
                        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
                        tag[c4d.TEXTURETAG_MATERIAL] = remap[id(mat)]

        for m in all_mats:
            if id(m) in remap:
                doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
                m.Remove()
                deleted_count += 1
        return deleted_count

    # ==========================================
    #  核心 B: 材质排序
    # ==========================================
    def SortAllMaterials(self, doc):
        mats = doc.GetMaterials()
        if len(mats) < 2: return
        mats.sort(key=lambda m: m.GetName().lower())
        for m in mats: m.Remove()
        pred = None
        for m in mats:
            doc.InsertMaterial(m, pred)
            pred = m

    # ==========================================
    #  核心 C: 对象处理 (v9.0 重写)
    # ==========================================
    def ProcessObject(self, op, config, stats):
        # 1. 获取所有标签
        all_tags = op.GetTags()
        
        # 2. 分类标签
        tex_tags = [t for t in all_tags if t.CheckType(c4d.Ttexture)]
        sel_tags = [t for t in all_tags if t.CheckType(c4d.Tpolygonselection)]
        
        # 建立 选集名 -> 选集标签 的映射 (处理同名选集)
        sel_tag_map = {}
        for st in sel_tags:
            sel_tag_map[st.GetName()] = st

        # 3. 准备数据容器
        # mat_sel_map: { Material : BaseSelect(合并后的选集) }
        mat_sel_map = {}
        global_mats = []
        
        # 记录正在被使用的选集标签 (用于判断是否是垃圾)
        used_sel_tags = set()

        # 4. 数据提取 (不管是否清理，先读数据)
        for tt in tex_tags:
            mat = tt[c4d.TEXTURETAG_MATERIAL]
            
            # Missing material references cannot participate in merge/rebuild.
            # They are removed later when clean mode is enabled; otherwise we leave
            # the tag untouched instead of inserting None into the sort/rebuild lists.
            if not mat:
                continue
            
            # 读取选集限制
            sel_name = tt[c4d.TEXTURETAG_RESTRICTION]
            
            if sel_name and sel_name in sel_tag_map:
                # 这是一个局部材质
                target_sel_tag = sel_tag_map[sel_name]
                used_sel_tags.add(target_sel_tag)
                
                if config['optimize']:
                    if mat not in mat_sel_map:
                        mat_sel_map[mat] = c4d.BaseSelect()
                    # 备份数据到内存
                    mat_sel_map[mat].Merge(target_sel_tag.GetBaseSelect())
            else:
                # 这是一个全局材质
                if config['optimize']:
                    if mat not in global_mats:
                        global_mats.append(mat)

        # 5. 制定【死亡名单】 (核弹核心逻辑)
        tags_to_kill = set()

        # A. 如果开启整理(Optimize)：销毁一切相关旧物
        if config['optimize']:
            # 删掉所有旧材质标签
            for t in tex_tags: 
                tags_to_kill.add(t)
            # 删掉所有被引用的旧选集标签 (因为数据已经备份到 mat_sel_map 了)
            for t in used_sel_tags: 
                tags_to_kill.add(t)
        
        # B. 如果开启清理(Clean)：识别并销毁垃圾
        if config['clean']:
            # 删掉所有【未被引用】的孤儿选集
            for st in sel_tags:
                if st not in used_sel_tags:
                    tags_to_kill.add(st)
            
            # 删掉 SDS / Session
            for t in all_tags:
                if t.CheckType(c4d.Tsds) or t.CheckType(1019396):
                    tags_to_kill.add(t)
                # 材质丢失的标签
                if t.CheckType(c4d.Ttexture) and not t[c4d.TEXTURETAG_MATERIAL]:
                    tags_to_kill.add(t)

        # 6. 执行销毁
        for t in tags_to_kill:
            if t.GetDocument() or t.GetMain(): # 确保还在对象上
                t.Remove()
                stats['cleaned'] += 1

        # 7. 重建新世界 (Optimize)
        if config['optimize']:
            # A. 全局材质 (右)
            global_mats.sort(key=lambda x: x.GetName().lower(), reverse=True)
            for mat in global_mats:
                self.StandardizeName(mat)
                nt = c4d.TextureTag()
                nt.SetMaterial(mat)
                nt[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
                op.InsertTag(nt)

            # B. 局部材质 (左)
            sorted_mats = sorted(list(mat_sel_map.keys()), key=lambda x: x.GetName().lower())
            
            for i in range(len(sorted_mats)-1, -1, -1):
                mat = sorted_mats[i]
                bs = mat_sel_map[mat]
                
                clean_name = self.StandardizeName(mat)
                sel_name = f"{i:02d}_{clean_name}_Set"
                
                st = c4d.SelectionTag(c4d.Tpolygonselection)
                st.SetName(sel_name)
                st.GetBaseSelect().Merge(bs)
                
                tt = c4d.TextureTag()
                tt.SetMaterial(mat)
                tt[c4d.TEXTURETAG_RESTRICTION] = sel_name
                tt[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
                
                op.InsertTag(st)
                op.InsertTag(tt)
                stats['organized'] += 1

    def StandardizeName(self, mat):
        if not mat: return "Null"
        name = mat.GetName()
        clean = "".join([c if c.isalnum() else "_" for c in name])
        if not clean.upper().startswith("M_"):
            clean = "M_" + clean
        if name != clean:
            mat.SetName(clean)
        return clean

# =================================================================
# 图标
# =================================================================
def CreateDefaultIcon():
    w, h = 32, 32
    bmp = c4d.bitmaps.BaseBitmap()
    bmp.Init(w, h)
    for y in range(h):
        for x in range(w):
            bmp.SetPixel(x, y, 60, 60, 60)
    return bmp

def load_icon():
    icon_filename = "MaterialTagOrganizer.png"
    try:
        if __file__:
            dir_path = os.path.dirname(__file__)
            path = os.path.join(dir_path, icon_filename)
            if os.path.exists(path):
                bmp = bitmaps.BaseBitmap()
                res = bmp.InitWith(path)
                if isinstance(res, tuple): res = res[0]
                if res == c4d.IMAGERESULT_OK:
                    return bmp
    except: pass
    return CreateDefaultIcon()

if __name__ == "__main__":
    icon_bmp = load_icon()
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="Material Tag Organizer", 
        info=0,
        icon=icon_bmp,
        help="Clean and organize Cinema 4D material tags",
        dat=ObjectOptimizer()
    )