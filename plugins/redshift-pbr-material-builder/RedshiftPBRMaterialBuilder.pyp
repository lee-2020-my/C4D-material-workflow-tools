import c4d
import os
import maxon
import re
from c4d.gui import GeDialog

# ==============================================================================
#  全局配置 & 插件ID
# ==============================================================================
PLUGIN_ID = 1060001 
PLUGIN_NAME = "Redshift PBR Material Builder" 
RS_NODESPACE_ID = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")

COL_TEX = maxon.Color(0.0, 0.1, 0.8)   # 蓝色
COL_NODE = maxon.Color(0.9, 0.4, 0.0)  # 橙色
COL_BLK = maxon.Color(0.1, 0.1, 0.1)   # 黑色
DEFAULT_BORDER_STYLE = c4d.BORDER_NONE

# RS 对象标签 ID
ID_RS_OBJECT_TAG = 1036222 
# RS 标签参数 ID
RS_OVERRIDE = 1000
RS_SUBDIVISION = 1001
RS_DISPLACEMENT = 1002

# 端口映射
PORT_MAP = {
    "color": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color", "com.redshift3d.redshift4c4d.nodes.core.material.diffuse_color"],
    "rough": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refl_roughness", "com.redshift3d.redshift4c4d.nodes.core.material.refl_roughness"],
    "metal": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.metalness", "com.redshift3d.redshift4c4d.nodes.core.material.refl_metalness"],
    "bump":  ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.bump_input", "com.redshift3d.redshift4c4d.nodes.core.material.bump_input"],
    "alpha": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.opacity_color", "com.redshift3d.redshift4c4d.nodes.core.material.opacity_color"],
    "emiss": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.emission_color", "com.redshift3d.redshift4c4d.nodes.core.material.emission_color"],
    "emiss_w": ["com.redshift3d.redshift4c4d.nodes.core.standardmaterial.emission_weight", "com.redshift3d.redshift4c4d.nodes.core.material.emission_weight"]
}

# ==============================================================================
#  [提取原有逻辑] 命名清洗规则
# ==============================================================================
ALL_CHANNELS = [
    "base_color", "basecolor", "albedo", "diffuse", "diff", "color", "col",
    "ambient_occlusion", "ambient", "occlusion", "ao", "occ",
    "roughness", "rough", "rgh", "glossiness", "gloss",
    "metalness", "metallic", "metal", "mtl",
    "normal", "norm", "nrm", "dx", "ogl",
    "displacement", "displace", "height", "disp", "dsp",
    "opacity", "alpha", "mask", "trans",
    "emission", "emissive", "bump", "bmp"
]
ALL_CHANNELS.sort(key=len, reverse=True)

def get_clean_name_logic(stem_name):
    """
    通用命名清洗逻辑
    """
    found_suffix = False
    for kw in ALL_CHANNELS:
        pattern_end = re.compile(r'[-_\s\.]' + kw + r'$', re.IGNORECASE)
        if pattern_end.search(stem_name):
            stem_name = pattern_end.sub('', stem_name)
            found_suffix = True
            break 
        pattern_mid = re.compile(r'[-_\s\.]' + kw + r'[-_\s\.]', re.IGNORECASE)
        if pattern_mid.search(stem_name):
            stem_name = pattern_mid.sub('', stem_name)
            found_suffix = True
            break
            
    stem_name = stem_name.strip("-_ .0123456789")
    if not stem_name: 
        stem_name = "Material"
    else: 
        stem_name = stem_name.title()
        
    return stem_name

# ==============================================================================
#  核心逻辑区
# ==============================================================================
def apply_mature_setup(doc, material, has_displacement):
    active_object = doc.GetActiveObject()
    if not active_object:
        return 

    material_tag = c4d.BaseTag(c4d.Ttexture)
    active_object.InsertTag(material_tag)
    material_tag[c4d.TEXTURETAG_MATERIAL] = material
    material_tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
    
    if has_displacement:
        rs_tag = active_object.GetTag(ID_RS_OBJECT_TAG)
        if not rs_tag:
            rs_tag = c4d.BaseTag(ID_RS_OBJECT_TAG)
            active_object.InsertTag(rs_tag)
        
        rs_tag[RS_OVERRIDE] = True        
        rs_tag[RS_SUBDIVISION] = True     
        rs_tag[RS_DISPLACEMENT] = True    

    c4d.EventAdd()

def get_texture_type_by_score(fname):
    fname = fname.lower()
    rules = [
        ("color",  ["base_color", "basecolor", "albedo", "diffuse", "diff", "_col", "_c."], 10),
        ("normal", ["normal", "norm", "nrm", "_n.", "_ogl", "_dx"], 10),
        ("metal",  ["metalness", "metallic", "_mtl"], 10), 
        ("rough",  ["roughness", "rough", "rgh"], 10),
        ("ao",     ["ambient", "occlusion", "ao", "occ"], 10),
        ("disp",   ["displacement", "displace", "height", "disp"], 10),
        ("alpha",  ["opacity", "alpha", "mask"], 10),
        ("emiss",  ["emission", "emissive"], 10),
        ("bump",   ["bump", "bmp"], 5),
        ("metal",  ["metal"], 1), 
        ("color",  ["color"], 1)
    ]
    best_match = None
    max_score = 0
    for ch_type, kws, score in rules:
        for kw in kws:
            if kw in fname:
                current_score = score
                if re.search(r'[-_\s\.]' + kw + r'\.', fname): current_score += 5
                if current_score > max_score:
                    max_score = current_score
                    best_match = ch_type
    return best_match

def classify_files_by_weight(file_list):
    tex_maps = { k: [] for k in ["color", "ao", "rough", "metal", "normal", "bump", "disp", "alpha", "emiss"] }
    for f in file_list:
        fname = os.path.basename(f)
        match = get_texture_type_by_score(fname)
        if match: tex_maps[match].append(f)
    return tex_maps

def set_node_color_space(node, tex_type):
    file_port = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
    if not file_port: return
    cs_port = file_port.FindChild("colorspace")
    if not cs_port: return
    if tex_type in ["color", "emiss"]:
        cs_port.SetDefaultValue("RS_INPUT_COLORSPACE_SRGB")
    else:
        cs_port.SetDefaultValue("RS_INPUT_COLORSPACE_RAW")

def scan_and_group_files(folder_path):
    allowed_extensions = [".png", ".jpg", ".jpeg", ".exr", ".tiff", ".tif", ".bmp", ".tga"]
    raw_groups = {}
    
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if not os.path.isfile(file_path): continue
        name, ext = os.path.splitext(file_name)
        if ext.lower() not in allowed_extensions: continue
        
        stem_name = name.lower()
        clean_name = get_clean_name_logic(stem_name)
        
        is_valid_group = False
        for kw in ALL_CHANNELS:
            if kw in stem_name: is_valid_group = True; break
        if not is_valid_group: continue

        if clean_name not in raw_groups: raw_groups[clean_name] = []
        raw_groups[clean_name].append(file_path)

    final_groups = {}
    CHECK_TYPES = {
        "Color": ["basecolor", "albedo", "diffuse", "diff", "color", "col"],
        "Norm":  ["normal", "norm", "nrm"],
        "Rough": ["roughness", "rough", "rgh"],
        "Metal": ["metalness", "metallic", "metal", "mtl"], 
        "Disp":  ["displace", "disp", "height"],
        "Alpha": ["opacity", "alpha"],
        "AO":    ["ao", "ambient"]
    }
    for grp, files in raw_groups.items():
        found_types = set()
        for f in files:
            fname = os.path.basename(f).lower()
            for t, kws in CHECK_TYPES.items():
                if any(kw in fname for kw in kws):
                    found_types.add(t)
                    break
        if len(found_types) >= 3:
            final_groups[grp] = files
    return final_groups

# ==============================================================================
#  逻辑 B: 导入文件夹
# ==============================================================================
def create_new_material(mat_name, file_list):
    doc = c4d.documents.GetActiveDocument()
    material = c4d.BaseMaterial(c4d.Mmaterial)
    material.SetName("M_" + mat_name)
    doc.InsertMaterial(material)
    
    node_material = material.GetNodeMaterialReference()
    graph = node_material.CreateDefaultGraph(RS_NODESPACE_ID)
    if graph.IsNullValue(): return
    
    tex_maps = classify_files_by_weight(file_list)

    idTexture = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.texturesampler")
    idMix = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer")
    idCC = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection")
    idBump = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.bumpmap")
    idDisp = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.displacement")
    idRamp = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsramp")
    idScale = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsmathabs")

    with graph.BeginTransaction() as t:
        created_tex_nodes = []
        
        def add_tex_node(filepath, type_key):
            node = graph.AddChild(maxon.Id(), idTexture)
            created_tex_nodes.append(node)
            node.SetValue(maxon.NODE.BASE.COLOR, COL_TEX)
            node.SetValue(maxon.NODE.BASE.NAME, maxon.String(os.path.basename(filepath)))
            
            file_port = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
            if file_port:
                file_port.FindChild("path").SetDefaultValue(maxon.Url(filepath))
                cs_port = file_port.FindChild("colorspace")
                if cs_port:
                    if type_key in ["color", "emiss"]:
                        cs_port.SetDefaultValue("RS_INPUT_COLORSPACE_SRGB")
                    else:
                        cs_port.SetDefaultValue("RS_INPUT_COLORSPACE_RAW")
            return node

        res = []
        maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.nodes.core.standardmaterial", True, res)
        if not res: return
        main_node = res[0]
        rough_port = main_node.GetInputs().FindChild(PORT_MAP["rough"][0])
        if rough_port:
            rough_parent = rough_port.GetParent()
            if rough_parent:
                ior_p = rough_parent.FindChild("refl_ior")
                if ior_p:
                    ior_p.SetDefaultValue(1.5)

        # Color
        final_col_out = None
        if tex_maps["color"]:
            tnode = add_tex_node(tex_maps["color"][0], "color")
            t_out = tnode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            cc = graph.AddChild("CC", idCC)
            cc.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            if t_out: t_out.Connect(cc.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection.input"))
            final_col_out = cc.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection.outcolor")

        if tex_maps["ao"]:
            anode = add_tex_node(tex_maps["ao"][0], "ao")
            a_out = anode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            mix = graph.AddChild("AO Mix", idMix)
            mix.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.layer1_blend_mode").SetDefaultValue(4)
            if final_col_out: final_col_out.Connect(mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.base_color"))
            if a_out: a_out.Connect(mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.layer1_color"))
            final_col_out = mix.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.outcolor")

        if final_col_out:
            final_col_out.Connect(main_node.GetInputs().FindChild(PORT_MAP["color"][0]))

        # Rough
        if tex_maps["rough"]:
            rnode = add_tex_node(tex_maps["rough"][0], "rough")
            ramp = graph.AddChild("Rough Ramp", idRamp)
            ramp.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            rnode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                ramp.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsramp.input"))
            ramp.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsramp.outcolor").Connect(
                main_node.GetInputs().FindChild(PORT_MAP["rough"][0]))

        # Metal
        if tex_maps["metal"]:
            mnode = add_tex_node(tex_maps["metal"][0], "metal")
            mnode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                main_node.GetInputs().FindChild(PORT_MAP["metal"][0]))

        # Normal/Bump
        active_bump = tex_maps["normal"][0] if tex_maps["normal"] else (tex_maps["bump"][0] if tex_maps["bump"] else None)
        is_n = True if tex_maps["normal"] else False
        if active_bump:
            bnode = add_tex_node(active_bump, "normal" if is_n else "bump")
            bump = graph.AddChild("Bump", idBump)
            bump.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            bump.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.inputtype").SetDefaultValue(1 if is_n else 0)
            bnode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                bump.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.input"))
            bump.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.out").Connect(
                main_node.GetInputs().FindChild(PORT_MAP["bump"][0]))

        # Disp
        if tex_maps["disp"]:
            out_res = []
            maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.node.output", True, out_res)
            if out_res:
                dnode = add_tex_node(tex_maps["disp"][0], "disp")
                disp = graph.AddChild("Displace", idDisp)
                disp.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
                dnode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                    disp.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.displacement.texmap"))
                disp.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.displacement.out").Connect(
                    out_res[0].GetInputs().FindChild("com.redshift3d.redshift4c4d.node.output.displacement"))
        
        # Alpha
        if tex_maps["alpha"]:
            anode = add_tex_node(tex_maps["alpha"][0], "alpha")
            anode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                main_node.GetInputs().FindChild(PORT_MAP["alpha"][0]))
        
        # Emiss
        if tex_maps["emiss"]:
            enode = add_tex_node(tex_maps["emiss"][0], "emiss")
            enode.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor").Connect(
                main_node.GetInputs().FindChild(PORT_MAP["emiss"][0]))
            main_node.GetInputs().FindChild(PORT_MAP["emiss_w"][0]).SetDefaultValue(1.0)

        # Scale
        if created_tex_nodes:
            scale = graph.AddChild(maxon.Id(), idScale)
            scale.SetValue(maxon.NODE.BASE.NAME, maxon.String("Global Scale"))
            scale.SetValue(maxon.NODE.BASE.COLOR, COL_BLK)
            scale.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsmathabs.input").SetDefaultValue(1.0)
            s_out = scale.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsmathabs.out")
            if s_out:
                for tn in created_tex_nodes:
                    try: s_out.Connect(tn.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.scale"))
                    except: pass
        t.Commit()
        c4d.CallCommand(465002363)

    # === [关键移植] 调用模型赋予函数 ===
    has_disp = len(tex_maps["disp"]) > 0
    apply_mature_setup(doc, material, has_disp)

# ==============================================================================
#  逻辑 C: 连连看
# ==============================================================================
def auto_connect_selected_mat(mat):
    nodeMaterial = mat.GetNodeMaterialReference()
    if not nodeMaterial.HasSpace(RS_NODESPACE_ID): return
    graph = nodeMaterial.GetGraph(RS_NODESPACE_ID)
    if not graph: return

    main_node = None
    is_legacy = False
    res = []
    maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.nodes.core.standardmaterial", True, res)
    if res: main_node = res[0]
    else:
        maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.nodes.core.material", True, res)
        if res: main_node = res[0]; is_legacy = True
    
    if not main_node:
        c4d.gui.MessageDialog("错误：未找到 RS 主材质节点。")
        return

    idMix = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer")
    idCC = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection")
    idBump = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.bumpmap")
    idDisp = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.displacement")
    idRamp = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsramp")
    idScale = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsmathabs")

    def get_target(key):
        idx = 1 if is_legacy else 0
        return main_node.GetInputs().FindChild(PORT_MAP[key][idx])

    has_disp = False 
    
    # [修正] 用于记录找到的所有贴图路径，以便后续重命名
    found_textures_list = []

    with graph.BeginTransaction() as t:
        tex_node_map = { k: None for k in ["color", "ao", "rough", "metal", "normal", "bump", "disp", "alpha", "emiss"] }
        root = graph.GetRoot()
        children = []
        root.GetChildren(children, maxon.NODE_KIND.NODE)
        existing_tex_nodes = []

        for node in children:
            if "texturesampler" in node.GetId().ToString():
                node.SetValue(maxon.NODE.BASE.COLOR, COL_TEX)
                existing_tex_nodes.append(node)
                fpath = ""
                p = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
                if p:
                    path_port = p.FindChild("path")
                    if path_port:
                        url = path_port.GetDefaultValue()
                        if url: fpath = url.GetUrl().lower()
                
                # 如果没找到路径，尝试从节点名获取（有时候用户手动改名）
                if not fpath: fpath = str(node.GetValue(maxon.NODE.BASE.NAME)).lower()
                
                # 记录文件名供后续重命名使用
                if fpath:
                    found_textures_list.append(os.path.basename(fpath))

                fname = os.path.basename(fpath)
                best_match = get_texture_type_by_score(fname)
                if best_match:
                    tex_node_map[best_match] = node
                    set_node_color_space(node, best_match)

        # Color & AO
        final_col_out = None
        col_node = tex_node_map["color"]
        if col_node:
            t_out = col_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            cc = graph.AddChild("CC", idCC)
            cc.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            if t_out: t_out.Connect(cc.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection.input"))
            final_col_out = cc.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorcorrection.outcolor")
        
        ao_node = tex_node_map["ao"]
        if ao_node:
            mix = graph.AddChild("AO Mix", idMix)
            mix.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.layer1_blend_mode").SetDefaultValue(4) 
            if final_col_out: final_col_out.Connect(mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.base_color"))
            ao_out = ao_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if ao_out: ao_out.Connect(mix.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.layer1_color"))
            final_col_out = mix.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rscolorlayer.outcolor")
        
        if final_col_out:
            tgt = get_target("color")
            if tgt: final_col_out.Connect(tgt)

        # Roughness
        rough_node = tex_node_map["rough"]
        if rough_node:
            ramp = graph.AddChild("Rough Ramp", idRamp)
            ramp.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            rough_out = rough_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if rough_out: rough_out.Connect(ramp.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsramp.input"))
            tgt = get_target("rough")
            if tgt: ramp.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsramp.outcolor").Connect(tgt)

        # Metal
        metal_node = tex_node_map["metal"]
        if metal_node:
            tgt = get_target("metal")
            m_out = metal_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if tgt and m_out: 
                m_out.Connect(tgt)
                if is_legacy:
                    f_mode = main_node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.material.refl_fresnel_mode")
                    if f_mode: f_mode.SetDefaultValue(2)

        # Bump
        active_bump_node = tex_node_map["normal"] if tex_node_map["normal"] else tex_node_map["bump"]
        if active_bump_node:
            bump = graph.AddChild("Bump", idBump)
            bump.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
            is_n = True if tex_node_map["normal"] else False
            bump.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.inputtype").SetDefaultValue(1 if is_n else 0)
            b_out_tex = active_bump_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if b_out_tex: b_out_tex.Connect(bump.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.input"))
            tgt = get_target("bump")
            if tgt: bump.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.out").Connect(tgt)

        # Disp
        disp_node_tex = tex_node_map["disp"]
        if disp_node_tex:
            has_disp = True
            out_nodes = []
            maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.node.output", True, out_nodes)
            if out_nodes:
                out_node = out_nodes[0]
                disp_shader = graph.AddChild(maxon.Id(), idDisp)
                disp_shader.SetValue(maxon.NODE.BASE.COLOR, COL_NODE)
                d_out_tex = disp_node_tex.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
                d_in_shader = disp_shader.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.displacement.texmap")
                if d_out_tex and d_in_shader: d_out_tex.Connect(d_in_shader)
                d_out_shader = disp_shader.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.displacement.out")
                out_in = out_node.GetInputs().FindChild("com.redshift3d.redshift4c4d.node.output.displacement")
                if d_out_shader and out_in: d_out_shader.Connect(out_in)

        # Alpha / Opacity
        alpha_node = tex_node_map["alpha"]
        if alpha_node:
            tgt = get_target("alpha")
            a_out = alpha_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if tgt and a_out:
                a_out.Connect(tgt)

        # Emission
        emiss_node = tex_node_map["emiss"]
        if emiss_node:
            tgt = get_target("emiss")
            e_out = emiss_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor")
            if tgt and e_out:
                e_out.Connect(tgt)
            emiss_w = get_target("emiss_w")
            if emiss_w:
                emiss_w.SetDefaultValue(1.0)

        # Scale
        if existing_tex_nodes:
            scale_node = None
            nodes = []
            maxon.GraphModelHelper.FindNodesByAssetId(graph, "com.redshift3d.redshift4c4d.nodes.core.rsmathabs", True, nodes)
            if nodes: scale_node = nodes[0]
            else:
                scale_node = graph.AddChild(maxon.Id(), idScale)
                scale_node.SetValue(maxon.NODE.BASE.NAME, maxon.String("Global Scale"))
                scale_node.SetValue(maxon.NODE.BASE.COLOR, COL_BLK)
                scale_node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsmathabs.input").SetDefaultValue(1.0)
            
            s_out = scale_node.GetOutputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.rsmathabs.out")
            for tn in existing_tex_nodes:
                p_scale = tn.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.scale")
                if p_scale and not p_scale.GetConnections(maxon.PORT_DIR.INPUT):
                    try: s_out.Connect(p_scale)
                    except: pass
        
        t.Commit()
        c4d.CallCommand(465002363)

    # === [关键修复] 执行重命名 ===
    # 之前可能因为分类失败导致没找到名字，现在我们暴力遍历 found_textures_list
    best_candidate = None
    
    # 1. 优先找带 Color/Albedo/Diffuse 的
    for fn in found_textures_list:
        lower_fn = fn.lower()
        if any(x in lower_fn for x in ["color", "albedo", "diffuse", "col", "diff"]):
            best_candidate = fn
            break
    
    # 2. 如果没找到，就用列表里第一个（只要是贴图就行）
    if not best_candidate and found_textures_list:
        best_candidate = found_textures_list[0]
        
    if best_candidate:
        name_part, ext_part = os.path.splitext(best_candidate)
        clean_name = get_clean_name_logic(name_part)
        new_name = "M_" + clean_name
        mat.SetName(new_name)

    # 调用模型赋予函数
    doc = c4d.documents.GetActiveDocument()
    apply_mature_setup(doc, mat, has_disp)

# ==============================================================================
#  UI 界面
# ==============================================================================
class MyDialog(c4d.gui.GeDialog):
    def CreateLayout(self):
        self.SetTitle(PLUGIN_NAME)
        if self.GroupBegin(id=950, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1):
            self.GroupBorderSpace(left=10, top=10, right=10, bottom=10)
            self.GroupBorderNoTitle(borderstyle=DEFAULT_BORDER_STYLE)
            if self.GroupBegin(id=1004, cols=2, flags=c4d.BFH_SCALEFIT):
                self.AddStaticText(2005, flags=c4d.BFH_LEFT, name="当前渲染器:")
                self.AddStaticText(2006, flags=c4d.BFH_SCALEFIT, name="检测中...", borderstyle=c4d.BORDER_WITH_TITLE_BOLD)
            self.GroupEnd()
            
            self.AddCustomGui(0, c4d.CUSTOMGUI_SEPARATOR, "", c4d.BFH_SCALEFIT, 0, 10)
            
            self.AddButton(id=3003, flags=c4d.BFH_SCALEFIT, initw=0, inith=30, name="导入贴图文件夹 (批量创建)")
            self.AddCustomGui(0, c4d.CUSTOMGUI_SEPARATOR, "", c4d.BFH_SCALEFIT, 0, 5)
            self.AddButton(id=3008, flags=c4d.BFH_SCALEFIT, initw=0, inith=30, name="所选材质自动连连看")
        self.GroupEnd()
        return True

    def InitValues(self): self.check_renderer(); return True
    def Timer(self, msg): self.check_renderer(); return True
    
    def check_renderer(self):
        doc = c4d.documents.GetActiveDocument()
        rd = doc.GetActiveRenderData()
        rname = "未检测到 Redshift"
        col = c4d.Vector(1, 0, 0)
        if rd:
            rid = rd[c4d.RDATA_RENDERENGINE]
            plugin = c4d.plugins.FindPlugin(rid, c4d.PLUGINTYPE_VIDEOPOST)
            if plugin and "redshift" in plugin.GetName().lower():
                rname = "Redshift"
                col = c4d.Vector(0.0, 0.8, 0.0)
        self.SetString(2006, " " + rname)
        self.SetDefaultColor(2006, c4d.COLOR_TEXT, col)

    def Command(self, id, msg):
        if id == 3003:
            folder_path = c4d.storage.LoadDialog(c4d.FILESELECTTYPE_ANYTHING, "请选择贴图文件夹", c4d.FILESELECT_DIRECTORY)
            if folder_path:
                groups = scan_and_group_files(folder_path)
                if not groups:
                    c4d.gui.MessageDialog("未找到成套材质 (需>=3种通道)")
                    return True
                doc = c4d.documents.GetActiveDocument()
                doc.StartUndo()
                c = 0
                for mn, fl in groups.items(): create_new_material(mn, fl); c+=1
                doc.EndUndo()
                c4d.EventAdd()
                c4d.gui.MessageDialog(f"导入完成！共创建 {c} 个材质。")
        if id == 3008:
            doc = c4d.documents.GetActiveDocument()
            mat = doc.GetActiveMaterial()
            if not mat:
                c4d.gui.MessageDialog("请先选择一个材质球！")
            else:
                doc.StartUndo()
                auto_connect_selected_mat(mat)
                doc.EndUndo()
                c4d.EventAdd()
        return True

# ==============================================================================
#  CommandData 插件注册
# ==============================================================================
class TextureLinkPlugin(c4d.plugins.CommandData):
    dialog = None

    def Execute(self, doc):
        if self.dialog is None:
            self.dialog = MyDialog()
        return self.dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID, defaultw=400, defaulth=220)

    def RestoreLayout(self, sec_ref):
        if self.dialog is None:
            self.dialog = MyDialog()
        return self.dialog.Restore(pluginid=PLUGIN_ID, secret=sec_ref)

if __name__ == '__main__':
    # 尝试加载同目录下的图标 (TextureLink PRO.png)
    bmp = c4d.bitmaps.BaseBitmap()
    dir, _ = os.path.split(__file__)
    fn = os.path.join(dir, "RedshiftPBRMaterialBuilder.png")
    bmp.InitWith(fn)

    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=bmp, 
        help="Build and auto-connect PBR materials for Redshift",
        dat=TextureLinkPlugin()
    )