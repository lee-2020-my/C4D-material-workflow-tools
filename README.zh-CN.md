# C4D 材质工作流工具集

面向 **Cinema 4D** 的开源 Python 小工具集，目前包含 Redshift PBR 材质自动搭建与材质标签整理两个工具。

[最新版本 v1.0.0](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/tag/v1.0.0) · [English](README.md) · [MIT License](LICENSE)

## 直接下载

**不用下载整个 GitHub 源码仓库。**按需要选一个即可：

| 下载 | 适合用途 |
|---|---|
| [**Redshift PBR Material Builder v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/Redshift-PBR-Material-Builder-v1.0.0.zip) | 自动识别 PBR 贴图并搭建/连接 Redshift 材质 |
| [**Material Tag Organizer v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/Material-Tag-Organizer-v1.0.0.zip) | 清理和整理材质标签、选集与材质命名；支持 C4D 原生材质和 Redshift 材质 |
| [**全部工具 v1.0.0**](https://github.com/lee-2020-my/C4D-material-workflow-tools/releases/download/v1.0.0/C4D-Material-Workflow-Tools-v1.0.0.zip) | 两个插件一起安装 |

## 安装方法

1. 下载上面的 ZIP 并解压。
2. 将解压得到的插件文件夹放到一个固定位置，例如 `D:\C4D_Plugins\`。
3. Cinema 4D 中打开 **偏好设置 > Plugins（插件）**，把 `D:\C4D_Plugins\` 加入插件搜索路径。
4. 重启 Cinema 4D。安装成功后可在 **Extensions（扩展）** 菜单中启动插件。

> **Redshift PBR Material Builder** 需要 Redshift；**Material Tag Organizer** 工作在 C4D 材质/标签层面，并不限于 Redshift。

## 1. Redshift PBR Material Builder

### 主要功能

- 自动识别 Base Color、AO、Roughness、Metalness、Normal/Bump、Displacement、Opacity、Emission 等常见 PBR 通道；
- 颜色/自发光贴图使用 sRGB，数据贴图使用 Raw；
- 自动连接 Redshift Standard Material 节点；
- 支持文件夹批量识别并创建材质；
- 可根据贴图组自动命名材质；
- 带位移贴图时可配合对象位移/细分工作流。

### 已有材质自动连接

1. 新建 Redshift Standard Material。
2. 将一套 PBR 贴图拖入节点编辑器。
3. 激活该材质。
4. 打开 **Extensions > Redshift PBR Material Builder** 并执行自动连接。

### 文件夹批量创建

1. 将一套或多套 PBR 贴图放在文件夹中。
2. 打开插件并选择文件夹导入功能。
3. 选择贴图目录。
4. 插件按文件名识别贴图组并自动创建 Redshift 材质。

## 2. Material Tag Organizer

用于整理导入资产中混乱的材质、材质标签和多边形选集。它**不限于 Redshift**，C4D 默认/原生材质对应的材质标签同样可以处理。

### 主要功能

- 批量处理所选多边形对象；
- 清理无效材质标签、孤立选集等；
- 按规范化名称合并重复材质；
- 材质按 A-Z 排序；
- 材质统一增加 `M_` 前缀并清洗非法字符；
- 重建选集与材质标签；
- 选集按 `00_M_xxx_Set` 一类格式整理；
- 完成后显示处理统计。

### 使用方法

1. 建议先另存一份场景副本。
2. 选择一个或多个需要整理的多边形对象。
3. 打开 **Extensions > Material Tag Organizer**。
4. 选择需要的清理/合并/整理选项后执行。

> **建议先备份场景：**整理操作可能修改材质标签、选集和材质分配关系。

### 当前限制

“重复材质合并”目前主要依据**材质名称**，而不是完整比较材质节点图。如果不同材质故意使用 `Paint`、`Paint.1`、`Paint.2` 一类名称，请先确认再执行合并。

## License

MIT License，详见 [LICENSE](LICENSE)。
