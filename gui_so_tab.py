"""
gui_so_tab.py - SO标签页GUI
实现静态优化（Static Optimization）批处理功能的GUI界面
参考 OpenSim Static Optimization Tool 的参数设计
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import opensim as osim
from gui_external_loads_manager import ExternalLoadsManagerDialog
import multiprocessing
from multiprocessing import Queue


def so_execution(output_dir, model_file, ik_files, external_loads_files, prefix, activation_exponent, use_muscle_physiology, step_interval, start_time, end_time, precision, force_set_files, replace_force_set, queue):
    """SO执行函数，在独立进程中运行"""
    try:
        import os
        from pathlib import Path
        import opensim as osim
        
        # 设置工作目录为模型文件所在目录，确保相对路径正确解析
        model_dir = os.path.dirname(model_file)
        os.chdir(model_dir)
        
        # 批量处理IK文件
        success_count = 0
        fail_count = 0
        skipped_count = 0
        
        def find_matching_trial_name(trial_name, available_names):
            """智能匹配trial名称"""
            # 精确匹配
            if trial_name in available_names:
                return trial_name
            
            # 尝试去除常见后缀后匹配
            base_name = trial_name.replace("_IK", "").replace("_ik", "")
            for name in available_names:
                if name.startswith(base_name) or base_name.startswith(name):
                    return name
            
            # 尝试部分匹配（包含关系）
            for name in available_names:
                if base_name in name or name in base_name:
                    return name
            
            return None
        
        for ik_path in ik_files:
            ik_file = Path(ik_path)
            # 从IK文件名提取trial名称（去除_IK, _ik, _Ik后缀）
            trial_name = ik_file.stem.replace("_IK", "").replace("_ik", "").replace("_Ik", "")
            
            # 发送日志消息
            queue.put({'type': 'log', 'message': f"\n▶ Trial: {trial_name}"})
            
            # 智能匹配ExternalLoads XML
            external_loads_xml = None
            if trial_name in external_loads_files:
                external_loads_xml = external_loads_files[trial_name]
            else:
                # 尝试智能匹配
                matched_name = find_matching_trial_name(trial_name, list(external_loads_files.keys()))
                if matched_name:
                    external_loads_xml = external_loads_files[matched_name]
                    # 发送日志消息
                    queue.put({'type': 'log', 'message': f"  智能匹配: {trial_name} -> {matched_name}"})
            
            if not external_loads_xml:
                # 发送日志消息
                queue.put({'type': 'log', 'message': f"⚠ 未找到对应 ExternalLoads.xml，跳过: {trial_name}"})
                skipped_count += 1
                continue
            
            # 确保输出文件名不包含 _ik 后缀
            clean_trial_name = trial_name.replace("_ik", "").replace("_IK", "").replace("_Ik", "")
            
            try:
                # 读取IK文件获取时间范围
                ik_table = osim.TimeSeriesTable(str(ik_path))
                time_vec = ik_table.getIndependentColumn()
                t0_file = time_vec[0]
                tf_file = time_vec[-1]
                
                # 确定时间范围
                if end_time < 0:
                    end_time = tf_file
                else:
                    end_time = min(end_time, tf_file)
                start_time = max(start_time, t0_file)
                
                # 确保使用绝对路径
                model_file_path = os.path.abspath(str(model_file))
                ik_file_path = os.path.abspath(str(ik_path))
                external_loads_path = os.path.abspath(str(external_loads_xml))
                
                # 验证文件是否存在
                if not os.path.exists(model_file_path):
                    raise FileNotFoundError(f"模型文件不存在: {model_file_path}")
                if not os.path.exists(ik_file_path):
                    raise FileNotFoundError(f"IK文件不存在: {ik_file_path}")
                if not os.path.exists(external_loads_path):
                    raise FileNotFoundError(f"ExternalLoads文件不存在: {external_loads_path}")
                
                # 创建 AnalyzeTool
                analyze_tool = osim.AnalyzeTool()
                analyze_tool.setName(f"{prefix}_{clean_trial_name}")
                
                # 使用 setModelFilename 而不是 setModel（根据教程示例）
                # 将路径转换为正斜杠格式（OpenSim需要）
                model_file_path_normalized = model_file_path.replace('\\', '/')
                analyze_tool.setModelFilename(model_file_path_normalized)
                
                # 设置运动文件和外部载荷文件（路径也转换为正斜杠）
                ik_file_path_normalized = ik_file_path.replace('\\', '/')
                external_loads_path_normalized = external_loads_path.replace('\\', '/')
                analyze_tool.setCoordinatesFileName(ik_file_path_normalized)
                analyze_tool.setExternalLoadsFileName(external_loads_path_normalized)
                
                # 设置低通滤波频率（根据XML示例，默认6Hz）
                analyze_tool.setLowpassCutoffFrequency(6.0)
                
                # 设置力集文件（如果有）
                if force_set_files:
                    force_set_array = osim.ArrayStr()
                    for force_file in force_set_files:
                        force_set_array.append(str(force_file))
                    analyze_tool.setForceSetFiles(force_set_array)
                    analyze_tool.setReplaceForceSet(replace_force_set)
                
                # 创建 StaticOptimization
                so = osim.StaticOptimization()
                so.setStartTime(start_time)
                so.setEndTime(end_time)
                so.setStepInterval(step_interval)
                so.setActivationExponent(activation_exponent)
                so.setUseMusclePhysiology(use_muscle_physiology)
                
                # 添加到分析集
                analyze_tool.updAnalysisSet().cloneAndAppend(so)
                
                # 配置 AnalyzeTool（时间范围和输出设置）
                analyze_tool.setStartTime(start_time)
                analyze_tool.setFinalTime(end_time)
                analyze_tool.setResultsDir(str(output_dir))
                analyze_tool.setOutputPrecision(precision)
                
                # 创建临时XML配置文件并重新加载（根据教程示例，这确保所有设置正确应用）
                import tempfile
                temp_xml = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
                temp_xml_path = temp_xml.name
                temp_xml.close()
                
                analyze_tool.printToXML(temp_xml_path)
                
                # 从XML文件重新加载AnalyzeTool（True参数表示加载并验证）
                analyze_tool = osim.AnalyzeTool(temp_xml_path, True)
                
                # 运行静态优化
                analyze_tool.run()
                
                # 清理临时文件
                try:
                    os.unlink(temp_xml_path)
                except:
                    pass
                
                # 发送日志消息
                queue.put({'type': 'log', 'message': f"✔ SO完成: {trial_name}"})
                success_count += 1
                
            except Exception as e:
                # 发送日志消息
                queue.put({'type': 'log', 'message': f"✗ SO失败: {trial_name}"})
                queue.put({'type': 'log', 'message': f"  错误信息: {str(e)}"})
                import traceback
                queue.put({'type': 'log', 'message': f"  详细错误: {traceback.format_exc()}"})
                fail_count += 1
        
        # 发送总结日志消息
        queue.put({'type': 'log', 'message': "\n" + "=" * 80})
        queue.put({'type': 'log', 'message': "SO批处理完成"})
        queue.put({'type': 'log', 'message': f"成功: {success_count} 个文件"})
        queue.put({'type': 'log', 'message': f"失败: {fail_count} 个文件"})
        queue.put({'type': 'log', 'message': f"跳过: {skipped_count} 个文件（未找到对应ExternalLoads）"})
        queue.put({'type': 'log', 'message': "=" * 80})
        
        # 发送完成消息
        queue.put({'type': 'complete'})
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        
        # 发送错误日志消息
        queue.put({'type': 'log', 'message': "\n" + "=" * 80})
        queue.put({'type': 'log', 'message': "SO批处理出错！"})
        queue.put({'type': 'log', 'message': error_msg})
        queue.put({'type': 'log', 'message': "=" * 80})
        
        # 发送错误消息
        queue.put({'type': 'error', 'message': str(e)})


class SOTab:
    """SO标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 存储输入值（必须在create_widgets()之前定义）
        self.model_file = tk.StringVar()
        self.ik_files = []  # 存储多个IK结果文件路径
        self.external_loads_files = {}  # 字典：trial_name -> ExternalLoads XML路径
        self.output_dir = tk.StringVar()
        
        # 静态优化参数
        self.activation_exponent = tk.DoubleVar(value=2.0)
        self.use_muscle_physiology = tk.BooleanVar(value=True)
        self.step_interval = tk.IntVar(value=1)
        
        # 时间设置
        self.start_time = tk.DoubleVar(value=0.0)
        self.end_time = tk.DoubleVar(value=-1.0)  # -1表示使用文件全部时间
        
        # 输出设置
        self.prefix = tk.StringVar(value="SO")
        self.precision = tk.IntVar(value=8)
        
        # 执行器设置
        self.force_set_files = []  # 额外的力集文件列表
        self.replace_force_set = tk.BooleanVar(value=False)
        
        # 日志节流控制
        self.log_queue = []
        self.log_timer = None
        self.log_interval = 500  # 毫秒
        
        # 进程控制
        self.so_process = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建滚动框架
        canvas = tk.Canvas(self.parent, bg='#FFE4E1')  # 粉色背景
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(scrollable_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 缩放后的模型文件
        ttk.Label(file_frame, text="缩放后的模型文件 (.osim):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.model_file, width=60, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_model_file).grid(row=0, column=2, padx=5, pady=5)
        
        # IK结果文件列表
        ik_frame = ttk.Frame(file_frame)
        ik_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(ik_frame, text="IK结果文件列表 (*_IK.mot):").pack(side=tk.LEFT, padx=5)
        ttk.Button(ik_frame, text="添加IK文件...", command=self.add_ik_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(ik_frame, text="清空列表", command=self.clear_ik_files).pack(side=tk.LEFT, padx=5)
        
        # IK文件列表框
        ik_listbox_frame = ttk.Frame(file_frame)
        ik_listbox_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        
        self.ik_listbox = tk.Listbox(ik_listbox_frame, height=4)
        self.ik_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ik_scrollbar = ttk.Scrollbar(ik_listbox_frame, orient="vertical", command=self.ik_listbox.yview)
        self.ik_listbox.configure(yscrollcommand=ik_scrollbar.set)
        ik_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ExternalLoads XML文件列表
        el_frame = ttk.Frame(file_frame)
        el_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(el_frame, text="ExternalLoads XML文件 (每个trial一个):").pack(side=tk.LEFT, padx=5)
        ttk.Button(el_frame, text="批量管理...", command=self.batch_manage_external_loads).pack(side=tk.LEFT, padx=5)
        ttk.Button(el_frame, text="添加XML文件...", command=self.add_external_loads_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(el_frame, text="清空列表", command=self.clear_external_loads_files).pack(side=tk.LEFT, padx=5)
        
        # ExternalLoads文件列表框
        el_listbox_frame = ttk.Frame(file_frame)
        el_listbox_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        
        self.el_listbox = tk.Listbox(el_listbox_frame, height=4)
        self.el_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        el_scrollbar = ttk.Scrollbar(el_listbox_frame, orient="vertical", command=self.el_listbox.yview)
        self.el_listbox.configure(yscrollcommand=el_scrollbar.set)
        el_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 输出文件夹
        ttk.Label(file_frame, text="输出文件夹:").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=60, state='readonly').grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_output_dir).grid(row=5, column=2, padx=5, pady=5)
        
        # 静态优化参数区域
        so_params_frame = ttk.LabelFrame(scrollable_frame, text="静态优化参数", padding="10")
        so_params_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 激活指数（目标函数）
        ttk.Label(so_params_frame, text="激活指数 (Objective Function):").grid(row=0, column=0, sticky=tk.W, pady=5)
        activation_entry = ttk.Entry(so_params_frame, textvariable=self.activation_exponent, width=15)
        activation_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(so_params_frame, text="(默认: 2.0, 表示 Sum of (muscle activation) ^ 2.0)").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # 使用肌肉生理学
        ttk.Checkbutton(
            so_params_frame,
            text="使用肌肉力-长度-速度关系 (Use muscle physiology)",
            variable=self.use_muscle_physiology
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 步长间隔
        ttk.Label(so_params_frame, text="步长间隔 (Step Interval):").grid(row=2, column=0, sticky=tk.W, pady=5)
        step_entry = ttk.Entry(so_params_frame, textvariable=self.step_interval, width=15)
        step_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(so_params_frame, text="(默认: 1, 表示每1步记录一次)").grid(row=2, column=2, sticky=tk.W, padx=5)
        
        # 时间设置区域
        time_frame = ttk.LabelFrame(scrollable_frame, text="时间设置", padding="10")
        time_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(time_frame, text="时间范围:").grid(row=0, column=0, sticky=tk.W, pady=5)
        start_entry = ttk.Entry(time_frame, textvariable=self.start_time, width=15)
        start_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(time_frame, text="到").grid(row=0, column=2, padx=5)
        end_entry = ttk.Entry(time_frame, textvariable=self.end_time, width=15)
        end_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(time_frame, text="(结束时间设为 -1 表示使用文件全部时间)").grid(row=0, column=4, sticky=tk.W, padx=5)
        
        # 输出设置区域
        output_frame = ttk.LabelFrame(scrollable_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="前缀 (Prefix):").grid(row=0, column=0, sticky=tk.W, pady=5)
        prefix_entry = ttk.Entry(output_frame, textvariable=self.prefix, width=20)
        prefix_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(output_frame, text="精度 (Precision):").grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        precision_entry = ttk.Entry(output_frame, textvariable=self.precision, width=10)
        precision_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 执行器设置区域
        actuator_frame = ttk.LabelFrame(scrollable_frame, text="执行器设置", padding="10")
        actuator_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(actuator_frame, text="额外的力集文件 (Additional force set files):").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # 按钮框架
        button_frame_force = ttk.Frame(actuator_frame)
        button_frame_force.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(button_frame_force, text="添加力集文件...", command=self.add_force_set_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame_force, text="清空列表", command=self.clear_force_set_files).pack(side=tk.LEFT, padx=2)
        
        # 力集文件列表框
        force_listbox_frame = ttk.Frame(actuator_frame)
        force_listbox_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        
        self.force_listbox = tk.Listbox(force_listbox_frame, height=3)
        self.force_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        force_scrollbar = ttk.Scrollbar(force_listbox_frame, orient="vertical", command=self.force_listbox.yview)
        self.force_listbox.configure(yscrollcommand=force_scrollbar.set)
        force_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 追加/替换选项
        ttk.Radiobutton(
            actuator_frame,
            text="追加到模型的力集 (Append to model's force set)",
            variable=self.replace_force_set,
            value=False
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(
            actuator_frame,
            text="替换模型的力集 (Replace model's force set)",
            variable=self.replace_force_set,
            value=True
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 运行按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="运行SO批处理", command=self.run_so)
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="中止", command=self.stop_so, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 状态显示
        status_frame = ttk.LabelFrame(scrollable_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 先创建滚动条
        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical")
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 再创建文本框，并关联滚动条
        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD, state='disabled', yscrollcommand=status_scrollbar.set)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置滚动条命令
        status_scrollbar.config(command=self.status_text.yview)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定窗口大小变化事件，调整Canvas大小
        self.parent.bind('<Configure>', lambda e: canvas.configure(width=e.width-20))
        
        # 绑定鼠标滚轮事件，实现滚动功能
        def on_mouse_wheel(event):
            # 计算滚动量
            scroll_amount = int(-1*(event.delta/120))
            # 执行滚动
            canvas.yview_scroll(scroll_amount, "units")
        
        # 绑定到canvas和scrollable_frame，确保在整个滚动区域都能响应
        canvas.bind("<MouseWheel>", on_mouse_wheel)
        scrollable_frame.bind("<MouseWheel>", on_mouse_wheel)
        
        # 为scrollable_frame中的所有子组件绑定鼠标滚轮事件
        def bind_to_children(widget):
            widget.bind("<MouseWheel>", on_mouse_wheel)
            for child in widget.winfo_children():
                bind_to_children(child)
        
        # 递归绑定到所有子组件
        bind_to_children(scrollable_frame)
    
    def select_model_file(self):
        """选择缩放后的模型文件"""
        filename = filedialog.askopenfilename(
            title="选择缩放好的模型文件 (.osim)",
            filetypes=[("OpenSim model", "*.osim")]
        )
        if filename:
            self.model_file.set(filename)
    
    def add_ik_files(self):
        """添加IK结果文件到列表"""
        filenames = filedialog.askopenfilenames(
            title="选择一个或多个 IK 结果文件 (*_IK.mot)",
            filetypes=[("IK results", "*_IK.mot"), ("Motion files", "*.mot")]
        )
        for filename in filenames:
            if filename not in self.ik_files:
                self.ik_files.append(filename)
                self.ik_listbox.insert(tk.END, os.path.basename(filename))
    
    def clear_ik_files(self):
        """清空IK文件列表"""
        self.ik_files.clear()
        self.ik_listbox.delete(0, tk.END)
    
    def add_external_loads_files(self):
        """添加ExternalLoads XML文件到列表"""
        filenames = filedialog.askopenfilenames(
            title="选择 ExternalLoads.xml 文件（每个 trial 一个）",
            filetypes=[("XML files", "*.xml")]
        )
        for filename in filenames:
            # 智能提取trial名称：支持多种命名格式
            stem = Path(filename).stem
            trial_name = stem.replace("_ExternalLoads", "").replace("ExternalLoads", "").replace("_EL", "")
            # 如果还是和stem一样，尝试从XML内容读取
            if trial_name == stem:
                trial_name = self.extract_trial_name_from_xml(filename)
            self.external_loads_files[trial_name] = filename
            # 更新列表框
            self.update_el_listbox()
    
    def extract_trial_name_from_xml(self, xml_path):
        """从ExternalLoads XML文件中提取trial名称（通过datafile路径）"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()
            # 查找datafile元素
            datafile_elem = root.find('.//datafile')
            if datafile_elem is not None and datafile_elem.text:
                mot_path = Path(datafile_elem.text.strip())
                # 从MOT文件路径提取trial名称
                return mot_path.stem.replace("_GRF", "").replace("_grf", "")
        except:
            pass
        # 如果无法提取，使用文件名（去除常见后缀）
        return Path(xml_path).stem.replace("_ExternalLoads", "").replace("ExternalLoads", "")
    
    def clear_external_loads_files(self):
        """清空ExternalLoads文件列表"""
        self.external_loads_files.clear()
        self.el_listbox.delete(0, tk.END)
    
    def batch_manage_external_loads(self):
        """批量管理 ExternalLoads 配置"""
        if not self.ik_files:
            messagebox.showwarning("警告", "请先添加IK文件")
            return
        
        # 尝试自动找到 MOT 文件夹（从 IK 文件所在文件夹）
        mot_folder = None
        if self.ik_files:
            # 检查 IK 文件所在文件夹是否有对应的 MOT 文件
            ik_folder = Path(self.ik_files[0]).parent
            # 查找是否有 .mot 文件
            mot_files = list(ik_folder.glob("*.mot"))
            if mot_files:
                mot_folder = str(ik_folder)
        
        # 打开批量管理对话框
        dialog = ExternalLoadsManagerDialog(
            parent=self.parent,
            ik_files=self.ik_files,
            existing_external_loads=self.external_loads_files,
            mot_folder=mot_folder
        )
        
        result = dialog.show()
        
        if result:
            # 更新 ExternalLoads 文件映射
            self.external_loads_files = result
            self.update_el_listbox()
            messagebox.showinfo("成功", f"已更新 {len(result)} 个 ExternalLoads 配置")
    
    def update_el_listbox(self):
        """更新ExternalLoads文件列表框"""
        self.el_listbox.delete(0, tk.END)
        for trial_name, xml_path in self.external_loads_files.items():
            self.el_listbox.insert(tk.END, f"{trial_name} -> {os.path.basename(xml_path)}")
    
    def find_matching_trial_name(self, trial_name, available_names):
        """智能匹配trial名称（支持模糊匹配）"""
        # 精确匹配
        if trial_name in available_names:
            return trial_name
        
        # 尝试去除常见后缀后匹配
        base_name = trial_name.replace("_IK", "").replace("_ik", "")
        for name in available_names:
            if name.startswith(base_name) or base_name.startswith(name):
                return name
        
        # 尝试部分匹配（包含关系）
        for name in available_names:
            if base_name in name or name in base_name:
                return name
        
        return None
    
    def add_force_set_files(self):
        """添加力集文件到列表"""
        filenames = filedialog.askopenfilenames(
            title="选择一个或多个力集文件 (.xml)",
            filetypes=[("XML files", "*.xml")]
        )
        for filename in filenames:
            if filename not in self.force_set_files:
                self.force_set_files.append(filename)
                self.force_listbox.insert(tk.END, os.path.basename(filename))
    
    def clear_force_set_files(self):
        """清空力集文件列表"""
        self.force_set_files.clear()
        self.force_listbox.delete(0, tk.END)
    
    def select_output_dir(self):
        """选择输出文件夹"""
        dirname = filedialog.askdirectory(
            title="选择SO输出文件夹"
        )
        if dirname:
            self.output_dir.set(dirname)
    
    def set_model_file(self, model_path):
        """设置模型文件（用于流水线模式）"""
        if os.path.exists(model_path):
            self.model_file.set(model_path)
    
    def set_ik_files(self, ik_file_paths):
        """设置IK文件列表（用于流水线模式）"""
        self.ik_files.clear()
        self.ik_listbox.delete(0, tk.END)
        for ik_path in ik_file_paths:
            if os.path.exists(ik_path):
                self.ik_files.append(ik_path)
                self.ik_listbox.insert(tk.END, os.path.basename(ik_path))
    
    def set_external_loads_files(self, external_loads_dict):
        """设置ExternalLoads文件字典（用于流水线模式）"""
        self.external_loads_files = external_loads_dict.copy()
        self.update_el_listbox()
    
    def log(self, message):
        """在状态文本框中添加日志（带节流机制），同时输出到后台终端"""
        print(message)  # 输出到后台终端
        self.log_queue.append(message)
        if not self.log_timer:
            self.process_log_queue()
    
    def process_log_queue(self):
        """处理日志队列"""
        if self.log_queue:
            messages = self.log_queue.copy()
            self.log_queue.clear()
            
            def update_log():
                self.status_text.config(state='normal')
                for message in messages:
                    self.status_text.insert(tk.END, message + "\n")
                self.status_text.see(tk.END)
                self.status_text.config(state='disabled')
            
            self.parent.after(0, update_log)
        
        # 重置计时器
        self.log_timer = self.parent.after(self.log_interval, self.process_log_queue)
    
    def run_so(self):
        """运行SO批处理"""
        # 验证输入
        if not self.model_file.get():
            messagebox.showerror("错误", "请选择缩放后的模型文件")
            return {'success': False, 'error': '未选择模型文件'}
        
        if not self.ik_files:
            messagebox.showerror("错误", "请至少添加一个IK结果文件")
            return {'success': False, 'error': '未选择IK文件'}
        
        if not self.external_loads_files:
            messagebox.showerror("错误", "请至少添加一个ExternalLoads XML文件")
            return {'success': False, 'error': '未选择ExternalLoads XML文件'}
        
        # 设置输出文件夹（如果未设置，使用第一个IK文件所在文件夹）
        if not self.output_dir.get():
            output_dir = os.path.dirname(self.ik_files[0])
            self.output_dir.set(output_dir)
        
        output_dir_path = Path(self.output_dir.get())
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        # 清空状态
        def clear_status():
            self.status_text.config(state='normal')
            self.status_text.delete(1.0, tk.END)
            self.status_text.config(state='disabled')
        self.parent.after(0, clear_status)
        
        # 记录开始信息
        def log_start():
            self.log("=" * 80)
            self.log("开始运行SO批处理...")
            self.log(f"模型文件: {self.model_file.get()}")
            self.log(f"IK文件数量: {len(self.ik_files)}")
            self.log(f"ExternalLoads文件数量: {len(self.external_loads_files)}")
            self.log(f"输出文件夹: {output_dir_path}")
            self.log(f"激活指数: {self.activation_exponent.get()}")
            self.log(f"使用肌肉生理学: {self.use_muscle_physiology.get()}")
            self.log(f"步长间隔: {self.step_interval.get()}")
            self.log("=" * 80)
        self.parent.after(0, log_start)
        
        # 禁用运行按钮，启用停止按钮
        def disable_buttons():
            self.run_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        self.parent.after(0, disable_buttons)
        
        # 启动SO执行进程
        import multiprocessing
        from multiprocessing import Queue
        
        # 创建消息队列
        msg_queue = Queue()
        
        # 启动SO执行进程
        self.so_process = multiprocessing.Process(
            target=so_execution,
            args=(
                output_dir_path,
                self.model_file.get(),
                self.ik_files,
                self.external_loads_files,
                self.prefix.get() or "SO",
                self.activation_exponent.get(),
                self.use_muscle_physiology.get(),
                self.step_interval.get(),
                self.start_time.get(),
                self.end_time.get(),
                self.precision.get(),
                self.force_set_files,
                self.replace_force_set.get(),
                msg_queue
            )
        )
        self.so_process.daemon = True
        self.so_process.start()
        
        # 启用中止按钮
        def enable_stop_button():
            self.stop_button.config(state=tk.NORMAL)
        self.parent.after(0, enable_stop_button)
        
        # 启动消息处理线程
        def process_messages():
            try:
                # 尝试从队列获取消息
                try:
                    msg = msg_queue.get(block=False)
                    if msg['type'] == 'log':
                        self.log(msg['message'])
                    elif msg['type'] == 'error':
                        self.log(f"错误: {msg['message']}")
                        # 恢复按钮状态
                        def enable_buttons():
                            self.run_button.config(state=tk.NORMAL)
                            self.stop_button.config(state=tk.DISABLED)
                        self.parent.after(0, enable_buttons)
                    elif msg['type'] == 'complete':
                        # 恢复按钮状态
                        def enable_buttons():
                            self.run_button.config(state=tk.NORMAL)
                            self.stop_button.config(state=tk.DISABLED)
                        self.parent.after(0, enable_buttons)
                    msg_queue.task_done()
                except multiprocessing.queues.Empty:
                    pass
            except Exception as e:
                pass
            finally:
                # 继续处理消息
                self.parent.after(100, process_messages)
        
        # 开始处理消息
        self.parent.after(100, process_messages)
    
    def stop_so(self):
        """中止SO批处理"""
        if self.so_process and self.so_process.is_alive():
            self.log("正在中止SO批处理...")
            self.so_process.terminate()
            self.so_process.join(timeout=5)
            
            # 恢复按钮状态
            def enable_buttons():
                self.run_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
            self.parent.after(0, enable_buttons)
            
            self.log("SO批处理已中止")

