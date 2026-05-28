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

> **注意**：`Geometry/` 文件夹因体积较大（~50MB）未包含在仓库中，请从以下链接下载：
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

## 关于作者

你好！我是**林之舵**。

- 邮箱：linzhiduo@bsu.edu.cn
- 学校：北京体育大学 体育工程学院
- 专业：23级 智能体育工程 本科生
- 热爱：生物力学 | 体能训练 | 排球

如果你对生物力学、运动科学或体育技术感兴趣，欢迎联系我交流！

## 许可证

请根据你的使用场景选择合适的许可证。

## 联系方式

如有问题或建议，请通过GitHub Issues提交或发送邮件至 linzhiduo@bsu.edu.cn
