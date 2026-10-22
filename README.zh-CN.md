# C4D 材质工作流工具集

这是一个面向 **Cinema 4D** 材质工作流的小型开源工具集，目前包含两个独立的 Python 插件：

1. **Redshift PBR Material Builder**：自动识别 PBR 贴图、设置色彩空间并连接 Redshift 材质节点，也支持从文件夹批量创建材质。
2. **Material Tag Organizer**：清理、合并、排序和重建材质标签与多边形选集，适合处理导入后材质通道较多的角色、车辆等资产。

## Redshift PBR Material Builder

### 支持的主要通道

- Base Color / Albedo / Diffuse
- AO
- Roughness
- Metalness
- Normal / Bump
- Displacement / Height
- Opacity / Alpha
- Emission

颜色和自发光贴图自动使用 sRGB；Roughness、Normal、Metalness 等数据贴图自动使用 Raw。

### 已有材质自动连接

1. 新建 Redshift Standard Material。
2. 将一套 PBR 贴图拖入节点编辑器。
3. 激活该材质。
4. 运行 **Redshift PBR Material Builder** 的自动连接功能。

插件会根据贴图文件名识别通道并自动建立连接。

### 文件夹批量创建

选择包含 PBR 贴图的文件夹后，插件会根据文件名进行分组。当一组贴图包含至少 3 类可识别通道时，会自动创建对应 Redshift 材质。

## Material Tag Organizer

主要用于整理导入资产中混乱的材质和标签。它工作在 Cinema 4D 的材质/标签层面，**并不限定 Redshift 渲染器**：默认/原生 Cinema 4D 材质和 Redshift 材质所对应的材质标签都可以整理。

- 批量处理所选多边形对象；
- 清理无效材质标签、孤立选集等；
- 按规范化名称合并重复材质；
- 材质按 A-Z 排序；
- 材质统一增加 `M_` 前缀并清洗非法字符；
- 重建选集与材质标签；
- 选集统一命名为 `00_M_xxx_Set` 一类格式；
- 完成后显示处理统计。

### 重要提醒

当前“重复材质合并”依据的是**材质名称**，而不是完整比较材质节点图。整理标签本身不依赖特定渲染器，但插件也不会比较不同渲染器内部的着色节点图来判断材质是否真正相同。

## License

MIT License，详见 [LICENSE](LICENSE)。
