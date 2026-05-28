"""
gui_id_tab.py - ID标签页GUI
实现ID逆动力学批处理功能的GUI界面
参考ID_Pipeline.py的批处理逻辑，确保与convert_c3d.py输出格式衔接
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import opensim as osim
from gui_external_loads_manager import ExternalLoadsManagerDialog


class IDTab:
    """ID标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 存储输入值（必须在create_widgets()之前定义）
        self.model_file = tk.StringVar()
        self.ik_files = []  # 存储多个IK结果文件路径
        self.external_loads_files = {}  # 字典：trial_name -> ExternalLoads XML路径
        self.output_dir = tk.StringVar()
        
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
        
        ttk.Label(el_frame, text="ExternalLoads XML文件 (每个trial一个，指向convert_c3d.py输出的MOT文件):").pack(side=tk.LEFT, padx=5)
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
        
        # 运行按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="运行ID批处理", command=self.run_id, style="Accent.TButton")
        self.run_button.pack(side=tk.LEFT, padx=5)
        
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
            filetypes=[("IK results", "*_IK.mot")]
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
            # 尝试多种可能的命名格式
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
    
    def select_output_dir(self):
        """选择输出文件夹"""
        dirname = filedialog.askdirectory(
            title="选择ID输出文件夹"
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
    
    def log(self, message):
        """在状态文本框中添加日志"""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')
        self.parent.update()
    
    def run_id(self):
        """运行ID批处理"""
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
        self.status_text.config(state='normal')
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state='disabled')
        
        self.log("=" * 80)
        self.log("开始运行ID批处理...")
        self.log(f"模型文件: {self.model_file.get()}")
        self.log(f"IK文件数量: {len(self.ik_files)}")
        self.log(f"ExternalLoads文件数量: {len(self.external_loads_files)}")
        self.log(f"输出文件夹: {output_dir_path}")
        self.log("=" * 80)
        
        try:
            # 批量处理IK文件
            success_count = 0
            fail_count = 0
            skipped_count = 0
            
            for ik_path in self.ik_files:
                ik_file = Path(ik_path)
                # 从IK文件名提取trial名称（去除_IK, _ik, _Ik后缀）
                trial_name = ik_file.stem.replace("_IK", "").replace("_ik", "").replace("_Ik", "")
                
                self.log(f"\n▶ Trial: {trial_name}")
                
                # 智能匹配ExternalLoads XML
                external_loads_xml = None
                if trial_name in self.external_loads_files:
                    external_loads_xml = self.external_loads_files[trial_name]
                else:
                    # 尝试智能匹配
                    matched_name = self.find_matching_trial_name(trial_name, list(self.external_loads_files.keys()))
                    if matched_name:
                        external_loads_xml = self.external_loads_files[matched_name]
                        self.log(f"  智能匹配: {trial_name} -> {matched_name}")
                
                if not external_loads_xml:
                    self.log(f"⚠ 未找到对应 ExternalLoads.xml，跳过: {trial_name}")
                    skipped_count += 1
                    continue
                
                # 确保 ID 文件名不包含 _ik 后缀
                clean_trial_name = trial_name.replace("_ik", "").replace("_IK", "").replace("_Ik", "")
                output_sto = output_dir_path / f"{clean_trial_name}_ID.sto"
                
                try:
                    # 每个trial重新加载模型，保证上一次修改不影响下一次
                    model_trial = osim.Model(str(self.model_file.get()))
                    model_trial.initSystem()
                    
                    # 禁用模型中所有肌肉力
                    for i in range(model_trial.getMuscles().getSize()):
                        muscle = model_trial.getMuscles().get(i)
                        muscle.set_appliesForce(False)
                    
                    # 读取IK时间
                    ik_table = osim.TimeSeriesTable(str(ik_path))
                    time_vec = ik_table.getIndependentColumn()
                    t0 = time_vec[0]
                    tf = time_vec[-1]
                    
                    # 设置ID Tool
                    id_tool = osim.InverseDynamicsTool()
                    id_tool.setModel(model_trial)
                    id_tool.setCoordinatesFileName(str(ik_path))
                    id_tool.setLowpassCutoffFrequency(6.0)  # IK数据滤波
                    
                    # 使用ExternalLoads XML
                    id_tool.setExternalLoadsFileName(str(external_loads_xml))
                    
                    # 时间与输出设置
                    id_tool.setStartTime(t0)
                    id_tool.setEndTime(tf)
                    id_tool.setResultsDir(str(output_dir_path))
                    id_tool.setOutputGenForceFileName(str(output_sto))
                    
                    # 运行ID
                    id_tool.run()
                    self.log(f"✔ ID完成: {output_sto.name}")
                    success_count += 1
                    
                except Exception as e:
                    self.log(f"✗ ID失败: {trial_name}")
                    self.log(f"  错误信息: {str(e)}")
                    fail_count += 1
            
            # 总结
            self.log("\n" + "=" * 80)
            self.log("ID批处理完成")
            self.log(f"成功: {success_count} 个文件")
            self.log(f"失败: {fail_count} 个文件")
            self.log(f"跳过: {skipped_count} 个文件（未找到对应ExternalLoads）")
            self.log("=" * 80)
            
            if fail_count == 0 and skipped_count == 0:
                messagebox.showinfo("成功", f"ID批处理完成！\n\n成功处理 {success_count} 个文件\n输出文件夹: {output_dir_path}")
                return {'success': True, 'output_dir': str(output_dir_path), 'success_count': success_count}
            else:
                msg = f"ID批处理完成\n\n成功: {success_count} 个文件"
                if fail_count > 0:
                    msg += f"\n失败: {fail_count} 个文件"
                if skipped_count > 0:
                    msg += f"\n跳过: {skipped_count} 个文件"
                messagebox.showwarning("部分成功", msg)
                return {'success': True, 'output_dir': str(output_dir_path), 'success_count': success_count, 
                        'fail_count': fail_count, 'skipped_count': skipped_count}
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.log("\n" + "=" * 80)
            self.log("ID批处理出错！")
            self.log(error_msg)
            self.log("=" * 80)
            messagebox.showerror("错误", f"ID批处理出错:\n{str(e)}")
            return {'success': False, 'error': error_msg}

