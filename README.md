# OpenSim AST-IK-ID-SO 批处理工具

## 项目简介

这是一个基于Python和OpenSim的生物力学数据处理GUI工具，支持以下功能：

- **C3D转换**：将C3D文件转换为TRC和MOT格式
- **AST模型缩放**：自动缩放OpenSim模型
- **IK逆运动学**：批量处理逆运动学分析
- **ID逆动力学**：批量处理逆动力学分析
- **SO静态优化**：批量处理静态优化分析

## 文件结构

```
gui_package/
├── main_gui.py                    # 主GUI入口程序
├── main_gui.spec                  # PyInstaller打包配置文件
├── beiti.png                      # 程序Logo图片
├── gui_ast_tab.py                 # AST缩放标签页
├── gui_ik_tab.py                  # IK逆运动学标签页
├── gui_id_tab.py                  # ID逆动力学标签页
├── gui_so_tab.py                  # SO静态优化标签页
├── gui_c3d_tab.py                 # C3D转换标签页
├── gui_ai_tab.py                  # AI助手标签页（当前已隐藏）
├── gui_external_loads_manager.py   # ExternalLoads管理对话框
└── README.md                      # 本说明文件
```

> ⚠️ **注意**：`Geometry/` 文件夹因体积较大（~50MB）未包含在仓库中，请从以下链接下载：
> - 方式1：从原始OpenSim安装目录复制 `Geometry` 文件夹
> - 方式2：从 [OpenSim 官网](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSIM/pages/5308024/Geometry) 下载

## 环境要求

- Python 3.11+
- OpenSim 4.x Python API
- PyInstaller 6.x

## 安装依赖

```bash
# 创建conda环境（推荐）
conda create -n opensim_gui python=3.11
conda activate opensim_gui

# 安装OpenSim（根据你的OpenSim版本选择合适的安装方式）
# 常见方式：
# 1. 使用conda安装（如果有）
# 2. 从OpenSim官网下载安装包
# 3. 从源代码编译

# 安装PyInstaller
pip install pyinstaller

# 验证OpenSim安装
python -c "import opensim; print(opensim.__version__)"
```

## 运行GUI

在命令行中直接运行Python脚本：

```bash
cd gui_package
python main_gui.py
```

## 打包为可执行文件

### 方法一：在有OpenSim环境中打包

```bash
cd gui_package
pyinstaller main_gui.spec
```

打包完成后，可执行文件会生成在 `dist/main_gui.exe`

### 方法二：使用其他Python环境

如果需要在不同环境中打包，需要修改 `main_gui.spec` 中的路径：

```python
# 找到并修改以下路径为你的OpenSim安装路径
conda_prefix = r'你的OpenSim conda环境路径'
opensim_path = os.path.join(conda_prefix, 'Lib', 'opensim')
library_bin_path = os.path.join(conda_prefix, 'Library', 'bin')
```

## 当前配置

- **AI界面**：已隐藏（如需启用，修改 `main_gui.py` 中被注释的AI相关代码）
- **低通滤波系数**：IK、ID、SO模块均设置为 6Hz
- **双足足底力默认设置**：calcn_r（右脚跟）和 calcn_l（左脚跟）

## 修改说明

### 修改低通滤波系数

在以下文件中搜索 `setLowpassCutoffFrequency` 并修改数值：

- `gui_id_tab.py` - ID模块
- `gui_so_tab.py` - SO模块
- `gui_ai_tab.py` - AI功能中的IK和SO调用

示例：
```python
# 从
id_tool.setLowpassCutoffFrequency(6.0)
# 改为
id_tool.setLowpassCutoffFrequency(20.0)
```

### 修改双足足底力默认值

在 `gui_external_loads_manager.py` 中修改：

```python
"dual_foot": {
    "applied_to_body_right": "calcn_r",  # 修改右脚默认值
    "applied_to_body_left": "calcn_l",   # 修改左脚默认值
    ...
}
```

### 启用AI界面

在 `main_gui.py` 中取消以下代码的注释：

```python
# 第96行：取消导入
from gui_ai_tab import AITab

# 第168行：取消引用
self.ai_tab = None  # 改为 self.ai_tab = None

# 第228-231行：取消创建AI标签页的代码
# ai_frame = ttk.Frame(self.notebook)
# self.notebook.add(ai_frame, text="AI 助手")
# self.ai_tab = AITab(ai_frame)
```

## 常见问题

### Q: 打包时提示 "OpenSim path not found"
**A**: 确保在有OpenSim的环境中运行打包命令，或正确配置 `main_gui.spec` 中的路径

### Q: 运行时提示缺少DLL
**A**: 确保打包时包含了 `Library\bin` 目录下的所有DLL文件

### Q: 打包后的程序无法运行
**A**: 检查是否包含完整的OpenSim库文件和Geometry目录

## 开发者

本项目基于OpenSim 4.x API开发，使用Tkinter构建GUI界面。

## 许可证

请根据你的使用场景选择合适的许可证。

## 联系方式

如有问题或建议，请通过GitHub Issues提交。
