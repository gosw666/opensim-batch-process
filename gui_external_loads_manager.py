"""
gui_external_loads_manager.py - ExternalLoads 批量管理对话框
支持为每个文件选择不同的 ExternalLoads XML 配置，并可以修改施加力的点
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json


class ExternalLoadsManagerDialog:
    """ExternalLoads 批量管理对话框"""
    
    # 可用的 body 选项
    BODY_OPTIONS = [
        'toes_r', 'toes_l',
        'calcn_r', 'calcn_l',
        'talus_r', 'talus_l',
        'tibia_r', 'tibia_l',
        'femur_r', 'femur_l'
    ]
    
    # 配置类型选项
    CONFIG_TYPES = {
        'single_foot': '单足',
        'dual_foot': '双足'
    }
    
    def __init__(self, parent, ik_files, existing_external_loads=None, mot_folder=None):
        """
        初始化对话框
        
        参数:
            parent: 父窗口
            ik_files: IK 文件路径列表
            existing_external_loads: 现有的 ExternalLoads 映射字典 {trial_name: xml_path}
            mot_folder: MOT 文件所在文件夹（用于自动匹配）
        """
        self.parent = parent
        self.ik_files = ik_files
        self.existing_external_loads = existing_external_loads or {}
        self.mot_folder = mot_folder
        
        # 存储每个 trial 的配置
        # {trial_name: {'xml_path': str, 'config_type': str, 'applied_to_body': str, 'mot_file': str, 'force_id': str, 'point_id': str, 'torque_id': str, 'force_id_left': str, 'point_id_left': str, 'torque_id_left': str}}
        self.trial_configs = {}
        
        # 加载模板配置
        self.templates = self._load_templates()
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("批量管理 ExternalLoads 配置")
        self.dialog.geometry("1100x700")
        self.dialog.configure(bg='#FFE4E1')  # 粉色背景
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 初始化配置
        self._initialize_configs()
        
        # 创建界面
        self.create_widgets()
        
        # 结果
        self.result = None
    
    def _load_templates(self):
        """加载模板配置"""
        # 直接使用默认模板，不尝试从外部文件加载
        return {
            # "forefoot": {
            #     "applied_to_body": "toes_r",
            #     "force_identifier": "f1_",
            #     "point_identifier": "p1_",
            #     "torque_identifier": "m1_",
            #     "data_source_name": "DataRate=2000.000000"
            # },
            # "rearfoot": {
            #     "applied_to_body": "calcn_r",
            #     "force_identifier": "f1_",
            #     "point_identifier": "p1_",
            #     "torque_identifier": "m1_",
            #     "data_source_name": "DataRate=2000.000000"
            # },
            "single_foot": {
                "applied_to_body": "toes_r",
                "force_identifier": "f1_",
                "point_identifier": "p1_",
                "torque_identifier": "m1_",
                "data_source_name": "Unassigned"
            },
            "dual_foot": {
                "applied_to_body_right": "calcn_r",
                "applied_to_body_left": "calcn_l",
                "force_identifier_right": "f1_",
                "point_identifier_right": "p1_",
                "torque_identifier_right": "m1_",
                "force_identifier_left": "f2_",
                "point_identifier_left": "p2_",
                "torque_identifier_left": "m2_",
                "data_source_name": "Unassigned"
            }
        }
    
    def _initialize_configs(self):
        """初始化每个 trial 的配置"""
        for ik_path in self.ik_files:
            # 从 IK 文件名中提取 trial 名称，去除 _IK, _ik, _Ik 后缀
            trial_name = Path(ik_path).stem.replace("_IK", "").replace("_ik", "").replace("_Ik", "")
            
            # 检查是否已有配置
            xml_path = self.existing_external_loads.get(trial_name)
            
            # 自动检测配置类型
            config_type = self._detect_config_type_from_filename(trial_name)
            
            # 自动查找 MOT 文件
            mot_file = self._find_mot_file(trial_name)
            
            # 从现有 XML 读取配置（如果有）
            applied_to_body = None
            if xml_path and Path(xml_path).exists():
                applied_to_body = self._read_applied_to_body_from_xml(xml_path)
            
            # 如果没有从 XML 读取到，使用默认值
            if not applied_to_body:
                if config_type == 'dual_foot':
                    applied_to_body = 'calcn_r'  # 双足默认右足
                else:
                    applied_to_body = 'toes_r'  # 单足默认脚趾
            
            # 力标识符默认值
            force_id = 'f1_'
            point_id = 'p1_'
            torque_id = 'm1_'
            force_id_left = 'f2_'
            point_id_left = 'p2_'
            torque_id_left = 'm2_'
            
            # 左脚踏加点默认值
            applied_to_body_left = applied_to_body.replace('_r', '_l') if '_r' in applied_to_body else 'calcn_l'
            
            self.trial_configs[trial_name] = {
                'xml_path': xml_path or '',
                'config_type': config_type,
                'applied_to_body': applied_to_body,
                'applied_to_body_left': applied_to_body_left,
                'mot_file': str(mot_file) if mot_file else '',
                'force_id': force_id,
                'point_id': point_id,
                'torque_id': torque_id,
                'force_id_left': force_id_left,
                'point_id_left': point_id_left,
                'torque_id_left': torque_id_left
            }
    
    def _detect_config_type_from_filename(self, filename):
        """根据文件名检测配置类型"""
        # 默认单足
        return 'single_foot'
    
    def _find_mot_file(self, trial_name, search_folders=None):
        """
        查找对应的力数据文件（GRF MOT文件，排除 IK 文件）
        
        参数:
            trial_name: trial 名称（可能包含_ik后缀）
            search_folders: 可选的搜索文件夹列表，如果为 None 则使用默认搜索逻辑
        """
        if search_folders is None:
            search_folders = []
            
            # 如果指定了 MOT 文件夹，优先使用
            if self.mot_folder:
                search_folders.append(Path(self.mot_folder))
            
            # 从 IK 文件所在文件夹查找
            for ik_path in self.ik_files:
                search_folders.append(Path(ik_path).parent)
        else:
            # 确保 search_folders 中的元素都是 Path 对象
            search_folders = [Path(f) if not isinstance(f, Path) else f for f in search_folders]
        
        # 从 trial_name 中去除 _ik 或 _IK 后缀（因为力数据文件名不包含这些后缀）
        base_trial_name = trial_name.replace("_ik", "").replace("_IK", "").replace("_Ik", "")
        
        # 尝试多种命名方式（排除 IK 文件）
        possible_names = [
            f"{base_trial_name}.mot",
            f"{base_trial_name}_GRF.mot",
            f"{base_trial_name}_grf.mot",
            f"{base_trial_name}_force.mot",
            f"{base_trial_name}_Force.mot",
            # 也尝试原始名称（以防万一）
            f"{trial_name}.mot",
            f"{trial_name}_GRF.mot",
        ]
        
        for folder in search_folders:
            if not folder.exists():
                continue
            for name in possible_names:
                candidate = folder / name
                # 排除 IK 文件（包含 _ik 或 _IK 的文件）
                if candidate.exists() and '_ik' not in candidate.name.lower():
                    return candidate
        
        return None
    
    def _read_applied_to_body_from_xml(self, xml_path):
        """从 XML 文件读取 applied_to_body"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # 查找第一个 ExternalForce 的 applied_to_body
            applied_to_body_elem = root.find('.//applied_to_body')
            if applied_to_body_elem is not None and applied_to_body_elem.text:
                return applied_to_body_elem.text.strip()
        except:
            pass
        return None
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部按钮栏
        top_frame = ttk.Frame(self.dialog, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Button(top_frame, text="批量自动匹配力数据", command=self.batch_auto_match_mot).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="批量生成 XML 文件", command=self.batch_generate_xml).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="应用配置", command=self.apply_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
        # 主内容区域
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建表格框架
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动区域
        canvas = tk.Canvas(table_frame, bg='#FFE4E1')  # 粉色背景
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表头
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        headers = ['Trial 名称', '力数据文件', '配置类型', '施加点', '力标识符', 'XML 文件']
        widths = [120, 250, 100, 100, 200, 320]
        
        for i, (header, width) in enumerate(zip(headers, widths)):
            ttk.Label(header_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=i, padx=5, sticky=tk.W
            )
        
        # 存储行控件的引用
        self.row_widgets = {}
        
        # 为每个 trial 创建一行
        for trial_name in sorted(self.trial_configs.keys()):
            self._create_trial_row(scrollable_frame, trial_name)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件，实现滚动功能
        def on_mouse_wheel(event):
            # 计算滚动量
            scroll_amount = int(-1*(event.delta/120))
            # 执行滚动
            canvas.yview_scroll(scroll_amount, "units")
        
        # 只绑定到canvas，这样只有在滚动条区域滚动时才会触发整个界面的滚动
        canvas.bind("<MouseWheel>", on_mouse_wheel)
    
    def _create_trial_row(self, parent, trial_name):
        """为单个 trial 创建配置行"""
        config = self.trial_configs[trial_name]
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)
        
        # Trial 名称（只读）
        ttk.Label(row_frame, text=trial_name, width=18).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        # GRF MOT 文件选择（自动查找，排除 IK 文件）
        mot_display_value = os.path.basename(config['mot_file']) if config['mot_file'] else '未找到'
        mot_var = tk.StringVar(value=mot_display_value)
        mot_entry = ttk.Entry(row_frame, textvariable=mot_var, width=40, state='readonly')
        mot_entry.grid(row=0, column=1, padx=5, sticky=tk.W+tk.E)
        
        def select_mot_file():
            filename = filedialog.askopenfilename(
                title=f"选择 GRF MOT 文件（非 IK 文件）: {trial_name}",
                filetypes=[("MOT files", "*.mot")]
            )
            if filename:
                # 检查是否是 IK 文件
                if '_ik' in filename.lower():
                    messagebox.showwarning("警告", "请选择 GRF MOT 文件，不要选择 IK 文件（包含 _ik 的文件）")
                    return
                mot_var.set(os.path.basename(filename))
                config['mot_file'] = filename
        
        mot_btn_frame = ttk.Frame(row_frame)
        mot_btn_frame.grid(row=0, column=1, padx=(0, 5), sticky=tk.E)
        ttk.Button(mot_btn_frame, text="浏览...", command=select_mot_file, width=7).pack(side=tk.LEFT, padx=2)
        
        # 自动查找按钮
        def auto_find_mot():
            mot_file = self._find_mot_file(trial_name)
            if mot_file:
                mot_var.set(mot_file.name)
                config['mot_file'] = str(mot_file)
                messagebox.showinfo("成功", f"找到 GRF MOT 文件:\n{mot_file.name}")
            else:
                messagebox.showwarning("未找到", f"未找到 {trial_name} 对应的 GRF MOT 文件\n\n请手动选择")
        
        ttk.Button(mot_btn_frame, text="自动查找", command=auto_find_mot, width=7).pack(side=tk.LEFT, padx=2)
        
        # 配置类型选择
        config_type_var = tk.StringVar(value=config['config_type'])
        config_combo = ttk.Combobox(
            row_frame,
            textvariable=config_type_var,
            values=list(self.CONFIG_TYPES.keys()),
            state='readonly',
            width=15
        )
        config_combo.grid(row=0, column=2, padx=5, sticky=tk.W)
        
        def on_config_type_changed(event=None):
            new_type = config_type_var.get()
            config['config_type'] = new_type
            # 更新 applied_to_body 的默认值
            if new_type == 'dual_foot':
                body_var.set('calcn_r')
                config['applied_to_body'] = 'calcn_r'
            else:
                body_var.set('calcn_r')
                config['applied_to_body'] = 'calcn_r'
        
        config_combo.bind('<<ComboboxSelected>>', on_config_type_changed)
        
        # 施加点选择
        body_var = tk.StringVar(value=config['applied_to_body'])
        body_combo = ttk.Combobox(
            row_frame,
            textvariable=body_var,
            values=self.BODY_OPTIONS,
            state='readonly',
            width=12
        )
        body_combo.grid(row=0, column=3, padx=5, sticky=tk.W)
        
        # 双足配置的左脚踏加点选择
        body_left_var = tk.StringVar(value=config.get('applied_to_body_left', 'calcn_l'))
        body_left_combo = ttk.Combobox(
            row_frame,
            textvariable=body_left_var,
            values=self.BODY_OPTIONS,
            state='readonly',
            width=12
        )
        body_left_combo.grid(row=1, column=3, padx=5, sticky=tk.W)
        
        def update_applied_to_body(event=None):
            config['applied_to_body'] = body_var.get()
        
        def update_applied_to_body_left(event=None):
            config['applied_to_body_left'] = body_left_var.get()
        
        body_combo.bind('<<ComboboxSelected>>', update_applied_to_body)
        body_left_combo.bind('<<ComboboxSelected>>', update_applied_to_body_left)
        
        # 力标识符选择
        force_id_var = tk.StringVar(value=config['force_id'])
        point_id_var = tk.StringVar(value=config['point_id'])
        torque_id_var = tk.StringVar(value=config['torque_id'])
        
        # 力标识符选项
        id_options = ['f1_', 'f2_', 'f3_', 'f4_']
        point_options = ['p1_', 'p2_', 'p3_', 'p4_']
        torque_options = ['m1_', 'm2_', 'm3_', 'm4_']
        
        # 力标识符框架
        id_frame = ttk.Frame(row_frame)
        id_frame.grid(row=0, column=4, padx=5, sticky=tk.W)
        
        # 力标识符选择（单足和双足的右脚）
        ttk.Label(id_frame, text="力", width=2).grid(row=0, column=0, padx=1, sticky=tk.W)
        force_combo = ttk.Combobox(
            id_frame,
            textvariable=force_id_var,
            values=id_options,
            state='readonly',
            width=4
        )
        force_combo.grid(row=0, column=1, padx=1, sticky=tk.W)
        
        ttk.Label(id_frame, text="点", width=2).grid(row=0, column=2, padx=1, sticky=tk.W)
        point_combo = ttk.Combobox(
            id_frame,
            textvariable=point_id_var,
            values=point_options,
            state='readonly',
            width=4
        )
        point_combo.grid(row=0, column=3, padx=1, sticky=tk.W)
        
        ttk.Label(id_frame, text="矩", width=2).grid(row=0, column=4, padx=1, sticky=tk.W)
        torque_combo = ttk.Combobox(
            id_frame,
            textvariable=torque_id_var,
            values=torque_options,
            state='readonly',
            width=4
        )
        torque_combo.grid(row=0, column=5, padx=1, sticky=tk.W)
        
        # 实现滚动联动效果
        def on_force_scroll(event):
            # 从当前值获取数字部分
            current_value = force_id_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                point_id_var.set(f'p{number}_')
                torque_id_var.set(f'm{number}_')
                # 更新配置
                config['point_id'] = f'p{number}_'
                config['torque_id'] = f'm{number}_'
        
        def on_point_scroll(event):
            # 从当前值获取数字部分
            current_value = point_id_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                force_id_var.set(f'f{number}_')
                torque_id_var.set(f'm{number}_')
                # 更新配置
                config['force_id'] = f'f{number}_'
                config['torque_id'] = f'm{number}_'
        
        def on_torque_scroll(event):
            # 从当前值获取数字部分
            current_value = torque_id_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                force_id_var.set(f'f{number}_')
                point_id_var.set(f'p{number}_')
                # 更新配置
                config['force_id'] = f'f{number}_'
                config['point_id'] = f'p{number}_'
        
        # 绑定鼠标滚轮事件
        force_combo.bind('<MouseWheel>', on_force_scroll)
        point_combo.bind('<MouseWheel>', on_point_scroll)
        torque_combo.bind('<MouseWheel>', on_torque_scroll)
        
        # 双足配置的左脚力标识符
        force_id_left_var = tk.StringVar(value=config['force_id_left'])
        point_id_left_var = tk.StringVar(value=config['point_id_left'])
        torque_id_left_var = tk.StringVar(value=config['torque_id_left'])
        
        left_id_frame = ttk.Frame(row_frame)
        left_id_frame.grid(row=1, column=4, padx=5, sticky=tk.W)
        
        ttk.Label(left_id_frame, text="力", width=2).grid(row=0, column=0, padx=1, sticky=tk.W)
        force_left_combo = ttk.Combobox(
            left_id_frame,
            textvariable=force_id_left_var,
            values=id_options,
            state='readonly',
            width=4
        )
        force_left_combo.grid(row=0, column=1, padx=1, sticky=tk.W)
        
        ttk.Label(left_id_frame, text="点", width=2).grid(row=0, column=2, padx=1, sticky=tk.W)
        point_left_combo = ttk.Combobox(
            left_id_frame,
            textvariable=point_id_left_var,
            values=point_options,
            state='readonly',
            width=4
        )
        point_left_combo.grid(row=0, column=3, padx=1, sticky=tk.W)
        
        ttk.Label(left_id_frame, text="矩", width=2).grid(row=0, column=4, padx=1, sticky=tk.W)
        torque_left_combo = ttk.Combobox(
            left_id_frame,
            textvariable=torque_id_left_var,
            values=torque_options,
            state='readonly',
            width=4
        )
        torque_left_combo.grid(row=0, column=5, padx=1, sticky=tk.W)
        
        # 为左脚力标识符添加滚动联动效果
        def on_force_left_scroll(event):
            # 从当前值获取数字部分
            current_value = force_id_left_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                point_id_left_var.set(f'p{number}_')
                torque_id_left_var.set(f'm{number}_')
                # 更新配置
                config['point_id_left'] = f'p{number}_'
                config['torque_id_left'] = f'm{number}_'
        
        def on_point_left_scroll(event):
            # 从当前值获取数字部分
            current_value = point_id_left_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                force_id_left_var.set(f'f{number}_')
                torque_id_left_var.set(f'm{number}_')
                # 更新配置
                config['force_id_left'] = f'f{number}_'
                config['torque_id_left'] = f'm{number}_'
        
        def on_torque_left_scroll(event):
            # 从当前值获取数字部分
            current_value = torque_id_left_var.get()
            if current_value:
                number = current_value[1]  # 提取数字部分
                # 更新其他两个下拉菜单
                force_id_left_var.set(f'f{number}_')
                point_id_left_var.set(f'p{number}_')
                # 更新配置
                config['force_id_left'] = f'f{number}_'
                config['point_id_left'] = f'p{number}_'
        
        # 绑定鼠标滚轮事件
        force_left_combo.bind('<MouseWheel>', on_force_left_scroll)
        point_left_combo.bind('<MouseWheel>', on_point_left_scroll)
        torque_left_combo.bind('<MouseWheel>', on_torque_left_scroll)
        
        # 更新力标识符
        def update_force_id(event=None):
            config['force_id'] = force_id_var.get()
            config['point_id'] = point_id_var.get()
            config['torque_id'] = torque_id_var.get()
        
        def update_force_id_left(event=None):
            config['force_id_left'] = force_id_left_var.get()
            config['point_id_left'] = point_id_left_var.get()
            config['torque_id_left'] = torque_id_left_var.get()
        
        force_combo.bind('<<ComboboxSelected>>', update_force_id)
        point_combo.bind('<<ComboboxSelected>>', update_force_id)
        torque_combo.bind('<<ComboboxSelected>>', update_force_id)
        
        force_left_combo.bind('<<ComboboxSelected>>', update_force_id_left)
        point_left_combo.bind('<<ComboboxSelected>>', update_force_id_left)
        torque_left_combo.bind('<<ComboboxSelected>>', update_force_id_left)
        
        # 根据配置类型显示/隐藏施加点选择和力标识符选择
        def toggle_controls():
            if config_type_var.get() == 'dual_foot':
                body_combo.config(state='readonly')  # 双足也可以选择施加点
                body_left_combo.grid(row=1, column=3, padx=5, sticky=tk.W)
                left_id_frame.grid(row=1, column=4, padx=5, sticky=tk.W)
            else:
                body_combo.config(state='readonly')
                body_left_combo.grid_forget()
                left_id_frame.grid_forget()
        
        config_combo.bind('<<ComboboxSelected>>', lambda e: (on_config_type_changed(e), toggle_controls()))
        toggle_controls()
        
        # XML 文件选择
        xml_var = tk.StringVar(value=config['xml_path'])
        xml_entry = ttk.Entry(row_frame, textvariable=xml_var, width=36)
        xml_entry.grid(row=0, column=7, padx=5, sticky=tk.W+tk.E, rowspan=2)
        
        def select_xml_file():
            filename = filedialog.askopenfilename(
                title=f"选择 ExternalLoads XML 文件: {trial_name}",
                filetypes=[("XML files", "*.xml")]
            )
            if filename:
                xml_var.set(filename)
                config['xml_path'] = filename
        
        xml_btn_frame = ttk.Frame(row_frame)
        xml_btn_frame.grid(row=0, column=7, padx=(0, 5), sticky=tk.E, rowspan=2)
        ttk.Button(xml_btn_frame, text="浏览...", command=select_xml_file, width=7).pack(side=tk.LEFT, padx=2)
        
        # 从 MOT 文件生成 XML 按钮
        def generate_xml_from_mot():
            # 从GUI控件读取最新值（而不是从config字典）
            current_mot_file = mot_var.get() if mot_var.get() != '未找到' else config['mot_file']
            if not current_mot_file or not Path(current_mot_file).exists():
                messagebox.showwarning("警告", f"请先选择或找到 {trial_name} 的 GRF MOT 文件")
                return
            
            # 选择保存位置（确保文件名不包含 _ik 后缀）
            clean_trial_name = trial_name.replace("_ik", "").replace("_IK", "").replace("_Ik", "")
            default_xml_name = f"{clean_trial_name}_ExternalLoads.xml"
            xml_path = filedialog.asksaveasfilename(
                title=f"保存 ExternalLoads XML 文件: {trial_name}",
                defaultextension=".xml",
                initialfile=default_xml_name,
                filetypes=[("XML files", "*.xml")]
            )
            
            if xml_path:
                # 从GUI控件读取最新值
                current_config_type = config_type_var.get()
                current_applied_to_body = body_var.get()
                
                # 传递力标识符参数
                if current_config_type == 'dual_foot':
                    success = self._generate_xml_file(
                        trial_name=trial_name,
                        mot_file_path=current_mot_file,
                        output_path=xml_path,
                        config_type=current_config_type,
                        applied_to_body=current_applied_to_body,
                        applied_to_body_left=config.get('applied_to_body_left', 'calcn_l'),
                        force_identifier_right=config['force_id'],
                        point_identifier_right=config['point_id'],
                        torque_identifier_right=config['torque_id'],
                        force_identifier_left=config['force_id_left'],
                        point_identifier_left=config['point_id_left'],
                        torque_identifier_left=config['torque_id_left']
                    )
                else:
                    success = self._generate_xml_file(
                        trial_name=trial_name,
                        mot_file_path=current_mot_file,
                        output_path=xml_path,
                        config_type=current_config_type,
                        applied_to_body=current_applied_to_body,
                        force_identifier=config['force_id'],
                        point_identifier=config['point_id'],
                        torque_identifier=config['torque_id']
                    )
                
                if success:
                    xml_var.set(xml_path)
                    config['xml_path'] = xml_path
                    messagebox.showinfo("成功", f"已生成 XML 文件:\n{xml_path}")
                else:
                    messagebox.showerror("失败", f"生成 XML 文件失败")
        
        ttk.Button(xml_btn_frame, text="生成", command=generate_xml_from_mot, width=7).pack(side=tk.LEFT, padx=2)
        
        # 保存控件引用
        self.row_widgets[trial_name] = {
            'mot_var': mot_var,
            'config_type_var': config_type_var,
            'body_var': body_var,
            'body_left_var': body_left_var,
            'force_id_var': force_id_var,
            'point_id_var': point_id_var,
            'torque_id_var': torque_id_var,
            'force_id_left_var': force_id_left_var,
            'point_id_left_var': point_id_left_var,
            'torque_id_left_var': torque_id_left_var,
            'xml_var': xml_var,
            'row_frame': row_frame
        }
    
    def batch_auto_match_mot(self):
        """批量自动匹配力数据文件（GRF MOT文件，排除IK文件）"""
        # 询问用户选择搜索目录（可以多选）
        search_folders = []
        
        # 首先询问是否使用之前设置的 MOT 文件夹
        if self.mot_folder:
            use_existing = messagebox.askyesno(
                "选择搜索目录",
                f"是否使用之前设置的力数据文件夹？\n\n{self.mot_folder}\n\n"
                "点击'是'使用该文件夹，点击'否'选择新的搜索目录"
            )
            if use_existing:
                search_folders.append(Path(self.mot_folder))
        
        # 如果用户选择不使用之前的文件夹，或者没有之前的文件夹，则让用户选择
        if not search_folders:
            # 显示提示信息（只显示一次）
            messagebox.showinfo(
                "选择搜索目录",
                "请选择要搜索力数据文件（GRF MOT文件）的文件夹\n\n"
                "可以多次选择多个文件夹，点击'取消'完成选择\n\n"
                "注意：程序会自动排除IK文件（包含_ik的文件）"
            )
            
            # 循环选择文件夹，直到用户点击取消
            while True:
                folder = filedialog.askdirectory(
                    title="选择力数据文件搜索目录（点击取消完成选择）"
                )
                if not folder:  # 用户点击了取消
                    break
                folder_path = Path(folder)
                if folder_path.exists():
                    search_folders.append(folder_path)
                    # 显示已选择的文件夹
                    print(f"已添加搜索目录: {folder_path}")
                else:
                    messagebox.showwarning("警告", f"文件夹不存在: {folder}")
        
        if not search_folders:
            messagebox.showwarning("警告", "未选择任何搜索目录")
            return
        
        # 临时更新搜索文件夹列表
        original_mot_folder = self.mot_folder
        self.mot_folder = str(search_folders[0])  # 保存第一个作为默认
        
        matched_count = 0
        failed_trials = []
        
        for trial_name in self.trial_configs.keys():
            # 在所有选择的文件夹中搜索
            mot_file = self._find_mot_file(trial_name, search_folders=search_folders)
            
            if mot_file:
                self.trial_configs[trial_name]['mot_file'] = str(mot_file)
                self.row_widgets[trial_name]['mot_var'].set(mot_file.name)
                matched_count += 1
            else:
                failed_trials.append(trial_name)
        
        # 恢复原始 MOT 文件夹设置
        self.mot_folder = original_mot_folder
        
        # 显示结果
        msg = f"自动匹配完成！\n\n成功匹配: {matched_count}/{len(self.trial_configs)} 个 MOT 文件"
        if failed_trials:
            msg += f"\n\n未找到 MOT 文件的 trial ({len(failed_trials)} 个):\n"
            msg += "\n".join(failed_trials[:5])
            if len(failed_trials) > 5:
                msg += f"\n... (还有 {len(failed_trials)-5} 个)"
            messagebox.showwarning("部分成功", msg)
        else:
            messagebox.showinfo("完成", msg)
    
    def batch_generate_xml(self):
        """批量生成 XML 文件"""
        # 先更新配置（从界面读取最新值）
        for trial_name, widgets in self.row_widgets.items():
            config = self.trial_configs[trial_name]
            config['xml_path'] = widgets['xml_var'].get()
            config['config_type'] = widgets['config_type_var'].get()
            config['applied_to_body'] = widgets['body_var'].get()
            config['applied_to_body_left'] = widgets['body_left_var'].get()
            # 更新力标识符参数
            config['force_id'] = widgets['force_id_var'].get()
            config['point_id'] = widgets['point_id_var'].get()
            config['torque_id'] = widgets['torque_id_var'].get()
            # 更新左脚力标识符参数
            config['force_id_left'] = widgets['force_id_left_var'].get()
            config['point_id_left'] = widgets['point_id_left_var'].get()
            config['torque_id_left'] = widgets['torque_id_left_var'].get()
        
        # 选择保存目录
        save_dir = filedialog.askdirectory(title="选择 XML 文件保存目录")
        if not save_dir:
            return
        
        generated_count = 0
        failed_trials = []
        
        for trial_name, config in self.trial_configs.items():
            if not config['mot_file']:
                failed_trials.append(f"{trial_name}: 未找到 MOT 文件")
                continue
            
            # 生成 XML 文件路径（确保文件名不包含 _ik 后缀）
            clean_trial_name = trial_name.replace("_ik", "").replace("_IK", "").replace("_Ik", "")
            xml_path = Path(save_dir) / f"{clean_trial_name}_ExternalLoads.xml"
            
            # 传递力标识符参数
            if config['config_type'] == 'dual_foot':
                success = self._generate_xml_file(
                    trial_name=trial_name,
                    mot_file_path=config['mot_file'],
                    output_path=str(xml_path),
                    config_type=config['config_type'],
                    applied_to_body=config['applied_to_body'],
                    applied_to_body_left=config.get('applied_to_body_left', 'calcn_l'),
                    force_identifier_right=config['force_id'],
                    point_identifier_right=config['point_id'],
                    torque_identifier_right=config['torque_id'],
                    force_identifier_left=config['force_id_left'],
                    point_identifier_left=config['point_id_left'],
                    torque_identifier_left=config['torque_id_left']
                )
            else:
                success = self._generate_xml_file(
                    trial_name=trial_name,
                    mot_file_path=config['mot_file'],
                    output_path=str(xml_path),
                    config_type=config['config_type'],
                    applied_to_body=config['applied_to_body'],
                    force_identifier=config['force_id'],
                    point_identifier=config['point_id'],
                    torque_identifier=config['torque_id']
                )
            
            if success:
                config['xml_path'] = str(xml_path)
                self.row_widgets[trial_name]['xml_var'].set(str(xml_path))
                generated_count += 1
            else:
                failed_trials.append(trial_name)
        
        msg = f"批量生成完成！\n成功: {generated_count}/{len(self.trial_configs)}"
        if failed_trials:
            msg += f"\n失败: {len(failed_trials)} 个"
            msg += "\n\n失败列表:\n" + "\n".join(failed_trials[:5])
            if len(failed_trials) > 5:
                msg += f"\n... (还有 {len(failed_trials)-5} 个)"
            messagebox.showwarning("部分成功", msg)
        else:
            messagebox.showinfo("成功", msg)
    
    def _generate_xml_file(self, trial_name, mot_file_path, output_path, config_type, applied_to_body, force_identifier=None, point_identifier=None, torque_identifier=None, applied_to_body_left=None, force_identifier_right=None, point_identifier_right=None, torque_identifier_right=None, force_identifier_left=None, point_identifier_left=None, torque_identifier_left=None):
        """生成单个 XML 文件"""
        try:
            mot_path = Path(mot_file_path)
            if not mot_path.exists():
                return False
            
            # 创建 XML 结构
            root = ET.Element('OpenSimDocument')
            root.set('Version', '40500')
            
            external_loads = ET.SubElement(root, 'ExternalLoads')
            external_loads.set('name', 'externalloads')
            
            objects = ET.SubElement(external_loads, 'objects')
            
            template = self.templates[config_type]
            
            if config_type == 'dual_foot':
                # 双足配置
                # 根据用户选择的施加点来决定左右脚
                # 右脚
                external_force_right = ET.SubElement(objects, 'ExternalForce')
                external_force_right.set('name', 'right')
                
                # 左脚
                external_force_left = ET.SubElement(objects, 'ExternalForce')
                external_force_left.set('name', 'left')
                
                # 确定左右脚的施加点
                if applied_to_body and '_r' in applied_to_body:
                    # 用户选择的是右脚，直接使用
                    body_name_right = applied_to_body
                    # 左脚使用用户选择的左脚踏加点，如果没有选择则使用默认值
                    body_name_left = applied_to_body_left or template['applied_to_body_left']
                elif applied_to_body and '_l' in applied_to_body:
                    # 用户选择的是左脚，作为左脚踏加点
                    body_name_left = applied_to_body
                    # 右脚使用默认值
                    body_name_right = template['applied_to_body_right']
                    # 交换力标识符
                    force_identifier_right, force_identifier_left = force_identifier_left, force_identifier_right
                    point_identifier_right, point_identifier_left = point_identifier_left, point_identifier_right
                    torque_identifier_right, torque_identifier_left = torque_identifier_left, torque_identifier_right
                else:
                    # 没有指定或不是左右脚，使用默认值
                    body_name_right = applied_to_body if applied_to_body else template['applied_to_body_right']
                    body_name_left = applied_to_body_left or template['applied_to_body_left']
                
                # 设置右脚参数
                force_id_right = force_identifier_right or template['force_identifier_right']
                point_id_right = point_identifier_right or template['point_identifier_right']
                torque_id_right = torque_identifier_right or template['torque_identifier_right']
                
                ET.SubElement(external_force_right, 'applied_to_body').text = f' {body_name_right} '
                ET.SubElement(external_force_right, 'force_expressed_in_body').text = ' ground '
                ET.SubElement(external_force_right, 'point_expressed_in_body').text = ' ground '
                ET.SubElement(external_force_right, 'force_identifier').text = f' {force_id_right} '
                ET.SubElement(external_force_right, 'point_identifier').text = f' {point_id_right} '
                ET.SubElement(external_force_right, 'torque_identifier').text = f' {torque_id_right} '
                ET.SubElement(external_force_right, 'data_source_name').text = f' {template["data_source_name"]} '
                
                # 设置左脚参数
                force_id_left = force_identifier_left or template['force_identifier_left']
                point_id_left = point_identifier_left or template['point_identifier_left']
                torque_id_left = torque_identifier_left or template['torque_identifier_left']
                
                ET.SubElement(external_force_left, 'applied_to_body').text = f' {body_name_left} '
                ET.SubElement(external_force_left, 'force_expressed_in_body').text = ' ground '
                ET.SubElement(external_force_left, 'point_expressed_in_body').text = ' ground '
                ET.SubElement(external_force_left, 'force_identifier').text = f' {force_id_left} '
                ET.SubElement(external_force_left, 'point_identifier').text = f' {point_id_left} '
                ET.SubElement(external_force_left, 'torque_identifier').text = f' {torque_id_left} '
                ET.SubElement(external_force_left, 'data_source_name').text = f' {template["data_source_name"]} '
            else:
                # 单足配置
                external_force = ET.SubElement(objects, 'ExternalForce')
                external_force.set('name', 'externalforce')
                
                # 使用用户选择的施加点，默认为模板中的值
                body_name = applied_to_body if applied_to_body else template['applied_to_body']
                force_id = force_identifier or template['force_identifier']
                point_id = point_identifier or template['point_identifier']
                torque_id = torque_identifier or template['torque_identifier']
                
                ET.SubElement(external_force, 'applied_to_body').text = body_name
                ET.SubElement(external_force, 'force_expressed_in_body').text = 'ground'
                ET.SubElement(external_force, 'point_expressed_in_body').text = 'ground'
                ET.SubElement(external_force, 'force_identifier').text = force_id
                ET.SubElement(external_force, 'point_identifier').text = point_id
                ET.SubElement(external_force, 'torque_identifier').text = torque_id
                # 当使用 datafile 时，data_source_name 应设置为 Unassigned
                ET.SubElement(external_force, 'data_source_name').text = 'Unassigned'
            
            ET.SubElement(external_loads, 'groups')
            
            # 设置 datafile 路径（使用绝对路径）
            # 注意：datafile 会覆盖 individual external forces 的 data_source_name
            mot_path_abs = mot_path.resolve()
            ET.SubElement(external_loads, 'datafile').text = str(mot_path_abs)
            
            # 格式化 XML
            xml_str = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            formatted_xml = dom.toprettyxml(indent='\t', encoding='utf-8')
            
            # 保存文件
            with open(output_path, 'wb') as f:
                f.write(formatted_xml)
            
            return True
        
        except Exception as e:
            print(f"生成 XML 文件失败 ({trial_name}): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def apply_config(self):
        """应用配置并返回结果"""
        # 更新配置（从界面读取最新值）
        for trial_name, widgets in self.row_widgets.items():
            config = self.trial_configs[trial_name]
            config['xml_path'] = widgets['xml_var'].get()
            config['config_type'] = widgets['config_type_var'].get()
            config['applied_to_body'] = widgets['body_var'].get()
            config['mot_file'] = widgets['mot_var'].get()
        
        # 验证配置
        missing_xml = []
        for trial_name, config in self.trial_configs.items():
            if not config['xml_path']:
                missing_xml.append(trial_name)
            elif not Path(config['xml_path']).exists():
                missing_xml.append(f"{trial_name} (文件不存在)")
        
        if missing_xml:
            result = messagebox.askyesno(
                "警告",
                f"以下 {len(missing_xml)} 个 trial 的 XML 文件不存在或未设置：\n" +
                "\n".join(missing_xml[:5]) +
                (f"\n... (还有 {len(missing_xml)-5} 个)" if len(missing_xml) > 5 else "") +
                "\n\n是否继续？"
            )
            if not result:
                return
        
        # 返回结果：{trial_name: xml_path}，只包含存在的文件
        self.result = {
            trial_name: config['xml_path'] 
            for trial_name, config in self.trial_configs.items() 
            if config['xml_path'] and Path(config['xml_path']).exists()
        }
        self.dialog.destroy()
    
    def cancel(self):
        """取消操作"""
        self.result = None
        self.dialog.destroy()
    
    def show(self):
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result

