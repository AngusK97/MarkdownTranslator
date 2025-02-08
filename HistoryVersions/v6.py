import os
import time
import re
import threading
import json
from tkinter import Tk, Button, Label, filedialog, messagebox, StringVar, Entry, Frame, Text, Checkbutton, BooleanVar
from tkinter.ttk import Progressbar
from google.cloud import translate_v2 as translate

CONFIG_FILE = "config.json"

# ======================== 样式配置 ========================
COLOR_BG = "#2d2d2d"         # 背景色 - 深灰
COLOR_FG = "#ffffff"         # 前景色 - 白色
COLOR_BUTTON = "#3d3d3d"     # 按钮背景色
COLOR_HOVER = "#4d4d4d"      # 按钮悬停色
FONT_NAME = "微软雅黑"        # 主要字体
FONT_SIZE = 10               # 基础字号
WINDOW_WIDTH = 680
WINDOW_HEIGHT = 580

class TranslationApp:
    def __init__(self, master):
        self.master = master
        master.title("Markdown 翻译工具")
        master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")  

        # ===== 新增窗口居中代码 =====
        # 计算窗口位置
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2  # 680是窗口宽度
        y = (screen_height - WINDOW_HEIGHT) // 2  # 580是窗口高度
        master.geometry(f"+{x}+{y}")  # 设置窗口位置
        # ===== 位置设置结束 =====

        master.configure(bg=COLOR_BG)  # 设置主窗口背景色

        # ======================== 字体定义 ========================
        self.font_normal = (FONT_NAME, FONT_SIZE)
        self.font_title = (FONT_NAME, FONT_SIZE+2, "bold")
        self.font_mono = ("Consolas", FONT_SIZE)  # 等宽字体用于路径显示

        # ======================== 变量初始化 ========================
        self.folder_path = StringVar()
        self.output_folder = StringVar()
        self.credentials_path = StringVar()
        
        # 设置初始值
        self.folder_path.set("未选择输入文件夹")
        self.output_folder.set("未选择输出文件夹")
        self.credentials_path.set("未选择 Google 认证文件")
        
        # 添加变量追踪
        self.folder_path.trace_add("write", lambda *_: self.check_ready())
        self.output_folder.trace_add("write", lambda *_: self.check_ready())
        self.credentials_path.trace_add("write", lambda *_: self.check_ready())
        
        # ======================== 主框架 ========================
        self.main_frame = Frame(master, bg=COLOR_BG)
        self.main_frame.pack(padx=20, pady=15, fill="both", expand=True)

        # ======================== Google 认证部分 ========================
        self.cred_frame = Frame(self.main_frame, bg=COLOR_BG)
        self.cred_frame.pack(fill="x", pady=5)
        
        self.cred_button = self.create_button(self.cred_frame, "选择 Google 认证文件", self.select_credentials)
        self.cred_button.pack(side="left", padx=5)
        
        self.cred_label = Label(self.cred_frame, 
                              textvariable=self.credentials_path,
                              wraplength=500,
                              font=self.font_mono,
                              fg="#a0a0a0",  # 浅灰色文字
                              bg=COLOR_BG,
                              anchor="w")
        self.cred_label.pack(side="left", fill="x", expand=True)

        # ======================== 输入输出路径部分 ========================
        self.create_path_section("输入文件夹", self.select_input_folder, self.folder_path)
        self.create_path_section("输出文件夹", self.select_output_folder, self.output_folder)

        # ======================== Obsidian 选项 ========================
        self.obsidian_var = BooleanVar(value=False)
        self.obsidian_check = Checkbutton(self.main_frame,
                                        text="保留 Obsidian 双链引用 [[]]",
                                        variable=self.obsidian_var,
                                        command=self.check_ready,
                                        font=self.font_normal,
                                        fg=COLOR_FG,
                                        bg=COLOR_BG,
                                        selectcolor=COLOR_BG,
                                        activebackground=COLOR_BG,
                                        activeforeground=COLOR_FG)
        self.obsidian_check.pack(pady=10)

        # ======================== 操作按钮 ========================
        self.btn_frame = Frame(self.main_frame, bg=COLOR_BG)
        self.btn_frame.pack(pady=15)
        
        self.translate_button = self.create_button(self.btn_frame, "开始翻译", self.start_translation, state="disabled")
        self.translate_button.pack(side="left", padx=10)

        self.close_button = self.create_button(self.btn_frame, "关闭程序", master.quit)
        self.close_button.pack(side="left", padx=10)

        # ======================== 进度条 ========================
        self.progress = Progressbar(self.main_frame,
                                  orient="horizontal",
                                  length=500,
                                  mode="determinate",
                                  style="custom.Horizontal.TProgressbar")
        self.progress.pack(pady=10)

        # ======================== 日志文本框 ========================
        self.log_text = Text(self.main_frame,
                           height=12,
                           width=80,
                           wrap="word",
                           font=self.font_mono,
                           bg="#1a1a1a",  # 深色背景
                           fg="#c0c0c0",  # 浅灰文字
                           insertbackground=COLOR_FG)  # 光标颜色
        self.log_text.pack()
        self.log_text.insert("end", ">>> 准备就绪，等待开始翻译...\n")

        # ======================== 初始化配置 ========================
        self.load_credentials()
        self.check_ready()
        self.setup_style()

    # ======================== 自定义样式方法 ========================
    def setup_style(self):
        """配置进度条样式"""
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('default')
        style.configure("custom.Horizontal.TProgressbar",
                        thickness=15,
                        troughcolor=COLOR_BG,
                        bordercolor=COLOR_BG,
                        background="#4CAF50",  # 进度条绿色
                        lightcolor="#66BB6A",
                        darkcolor="#388E3C")

    def create_button(self, parent, text, command, state="normal"):
        """创建统一风格的按钮"""
        return Button(parent,
                    text=text,
                    command=command,
                    state=state,
                    font=self.font_normal,
                    bg=COLOR_BUTTON,
                    fg=COLOR_FG,
                    activebackground=COLOR_HOVER,
                    activeforeground=COLOR_FG,
                    relief="flat",
                    padx=12,
                    pady=6)

    def create_path_section(self, title, command, variable):
        """创建路径选择模块"""
        frame = Frame(self.main_frame, bg=COLOR_BG)
        frame.pack(fill="x", pady=5)
        
        Label(frame,
            text=f"{title}:",
            font=self.font_normal,
            fg=COLOR_FG,
            bg=COLOR_BG,
            width=10,
            anchor="w").pack(side="left", padx=5)
            
        # 根据标题保存按钮实例
        btn = self.create_button(frame, f"选择{title}", command)
        btn.pack(side="left", padx=5)
        
        # 新增：保存按钮引用到实例变量
        if title == "输入文件夹":
            self.input_button = btn
        elif title == "输出文件夹":
            self.output_button = btn
        
        entry = Entry(frame,
                    textvariable=variable,
                    state='readonly',
                    font=self.font_mono,
                    fg="#a0a0a0",
                    readonlybackground="#404040",
                    relief="flat",
                    width=40)
        entry.pack(side="left", fill="x", expand=True)

    # ======================== 原有功能方法保持不变 ========================
    def load_credentials(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_path = data.get("credentials", "")
                    if saved_path and os.path.exists(saved_path):
                        self.credentials_path.set(saved_path)
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = saved_path
            except Exception as e:
                self.log(f"加载配置失败: {e}")

    def save_credentials(self, path):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"credentials": path}, f, ensure_ascii=False, indent=4)

    def select_credentials(self):
        file_selected = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_selected:
            self.credentials_path.set(file_selected)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = file_selected
            self.save_credentials(file_selected)
            self.check_ready()

    def select_input_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.check_ready()

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)
            os.makedirs(folder_selected, exist_ok=True)
            self.check_ready()

    def check_ready(self, *args):
        ready_conditions = [
            self.credentials_path.get() != "未选择 Google 认证文件",
            self.folder_path.get() not in ["未选择输入文件夹", ""],
            self.output_folder.get() not in ["未选择输出文件夹", ""]
        ]
        
        if all(ready_conditions):
            self.translate_button.config(state="normal", bg=COLOR_BUTTON)
        else:
            self.translate_button.config(state="disabled", bg="#404040")  # 禁用状态颜色
        
        # 强制刷新界面
        self.master.update_idletasks()


    def start_translation(self):
        folder = self.folder_path.get()
        output_folder = self.output_folder.get()

        if not os.path.exists(folder):
            messagebox.showerror("错误", "输入文件夹不存在！")
            return

        self.toggle_buttons(False)
        thread = threading.Thread(target=self.run_translation, args=(folder, output_folder))
        thread.start()

    def run_translation(self, input_folder, output_folder):
        try:
            self.progress["value"] = 0
            files = [f for f in os.listdir(input_folder) if f.endswith('.md')]
            total_files = len(files)

            for idx, filename in enumerate(files):
                self.log(f"正在处理: {filename} ({idx+1}/{total_files})")
                file_path = os.path.join(input_folder, filename)
                translated_file_path = os.path.join(output_folder, filename)
                self.translate_file(file_path, translated_file_path)
                self.progress["value"] = (idx + 1) / total_files * 100
                self.master.update_idletasks()

            self.log("✅ 所有文件翻译完成！")
            messagebox.showinfo("完成", "翻译任务已完成！")
        except Exception as e:
            self.log(f"❌ 发生错误: {str(e)}")
            messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(e)}")
        finally:
            self.toggle_buttons(True)
            self.progress["value"] = 0

    def translate_file(self, input_path, output_path):
        translate_client = translate.Client()
        with open(input_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        translated_lines = []
        for line in lines:
            line_content = line.rstrip('\n')
            if not line_content.strip():
                translated_lines.append('\n')
                continue
            translated_line = self.process_markdown_line(translate_client, line_content)
            translated_lines.append(translated_line + '\n')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)

    def process_markdown_line(self, translate_client, line):
        patterns = [
            (r'(\[\[.*?\]\])', 'obsidian_link'),
            (r'^(\s*[-*+]\s+)(.*)', 'list'),
            (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),
            (r'^(#+\s+)(.*)', 'header'),
            (r'(\[.*?\]\(.*?\))', 'markdown_link'),
            (r'(`.+?`)', 'inline_code')
        ]

        for pattern, pattern_type in patterns:
            match = re.search(pattern, line)
            if match:
                if pattern_type == 'obsidian_link' and self.obsidian_var.get():
                    return line
                if pattern_type in ['list', 'ordered_list', 'header']:
                    symbol, content = match.groups()
                    translated_content = translate_client.translate(content, target_language='en')['translatedText']
                    return f"{symbol}{translated_content}"
                elif pattern_type in ['markdown_link', 'inline_code']:
                    return line
        return translate_client.translate(line, target_language='en')['translatedText']

    # ======================== 辅助方法 ========================
    def toggle_buttons(self, enable=True):
        state = "normal" if enable else "disabled"
        self.translate_button.config(state=state)
        self.cred_button.config(state=state)
        self.input_button.config(state=state)
        self.output_button.config(state=state)

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.master.update_idletasks()

if __name__ == '__main__':
    root = Tk()
    app = TranslationApp(root)
    
    root.mainloop()