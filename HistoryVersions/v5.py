import os
import time
import re
import threading
import json
from tkinter import Tk, Button, Label, filedialog, messagebox, StringVar, Entry, Frame, Text, Scrollbar, Checkbutton, BooleanVar
from tkinter.ttk import Progressbar
from google.cloud import translate_v2 as translate

CONFIG_FILE = "config.json"

class TranslationApp:
    def __init__(self, master):
        self.master = master
        master.title("Markdown 翻译工具")
        master.geometry("600x500")  # 调整窗口大小

        # 变量初始化
        self.folder_path = StringVar(value="未选择输入文件夹")
        self.output_folder = StringVar(value="未选择输出文件夹")
        self.credentials_path = StringVar(value="未选择 Google 认证文件")
        self.progress_text = StringVar(value="等待开始翻译...\n")

        # **读取 Google 认证 JSON 路径**
        self.load_credentials()

        # 创建主框架
        self.main_frame = Frame(master)
        self.main_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # 选择 Google 认证文件
        self.cred_button = Button(self.main_frame, text="选择 Google 认证文件", command=self.select_credentials, width=20)
        self.cred_button.pack(pady=5)

        self.cred_label = Label(self.main_frame, textvariable=self.credentials_path, wraplength=500, fg="blue")
        self.cred_label.pack()

        # 选择输入文件夹
        self.input_button = Button(self.main_frame, text="选择输入文件夹", command=self.select_input_folder, width=20)
        self.input_button.pack(pady=5)

        self.input_label = Label(self.main_frame, textvariable=self.folder_path, wraplength=500, fg="blue")
        self.input_label.pack()

        # 选择输出文件夹
        self.output_button = Button(self.main_frame, text="选择输出文件夹", command=self.select_output_folder, width=20)
        self.output_button.pack(pady=5)

        self.output_label = Label(self.main_frame, textvariable=self.output_folder, wraplength=500, fg="blue")
        self.output_label.pack()

        # 新增 Obsidian 双链选项
        self.obsidian_var = BooleanVar(value=False)  # 默认不启用
        self.obsidian_check = Checkbutton(
            self.main_frame,
            text="保留 Obsidian 双链引用 [[]]",
            variable=self.obsidian_var,
            command=self.check_ready
        )
        self.obsidian_check.pack(pady=5)

        # 翻译按钮
        self.button_frame = Frame(self.main_frame)
        self.button_frame.pack(pady=10)

        self.translate_button = Button(self.button_frame, text="开始翻译", command=self.start_translation, state="disabled", width=15)
        self.translate_button.pack(side="left", padx=5)
        
        # 进度条
        self.progress = Progressbar(self.main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        # 进度文本框
        self.progress_text_box = Text(self.main_frame, height=20, width=70, wrap="word")
        self.progress_text_box.pack(pady=5)
        self.progress_text_box.insert("end", self.progress_text.get())

        # **检查是否满足翻译条件**
        self.check_ready()

    def load_credentials(self):
        """从 config.json 读取 Google 认证文件路径"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_path = data.get("credentials", "")
                    if saved_path and os.path.exists(saved_path):  # 确保路径存在
                        self.credentials_path.set(saved_path)
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = saved_path
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_credentials(self, path):
        """将 Google 认证文件路径保存到 config.json"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"credentials": path}, f, ensure_ascii=False, indent=4)

    def select_credentials(self):
        """选择 Google 认证文件"""
        file_selected = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_selected:
            self.credentials_path.set(file_selected)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = file_selected
            self.save_credentials(file_selected)  # **保存路径**
            self.check_ready()

    def select_input_folder(self):
        """选择输入文件夹"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.check_ready()

    def select_output_folder(self):
        """选择输出文件夹"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)
            os.makedirs(folder_selected, exist_ok=True)  # 确保输出文件夹存在
            self.check_ready()

    def check_ready(self):
        """检查是否满足翻译条件"""
        if self.credentials_path.get() != "未选择 Google 认证文件" and \
           self.folder_path.get() != "未选择输入文件夹" and \
           self.output_folder.get() != "未选择输出文件夹":
            self.translate_button.config(state="normal")

    def start_translation(self):
        """启动翻译进程"""
        folder = self.folder_path.get()
        output_folder = self.output_folder.get()

        if not os.path.exists(folder):
            messagebox.showerror("错误", "输入文件夹不存在！")
            return

        # 禁用按钮防止重复点击
        self.translate_button.config(state="disabled")
        self.input_button.config(state="disabled")
        self.output_button.config(state="disabled")

        # 运行翻译任务
        thread = threading.Thread(target=self.run_translation, args=(folder, output_folder))
        thread.start()

    def run_translation(self, input_folder, output_folder):
        """执行翻译任务"""
        try:
            self.progress["value"] = 0
            files = [f for f in os.listdir(input_folder) if f.endswith('.md')]
            total_files = len(files)

            for idx, filename in enumerate(files):
                progress_message = f"正在翻译 {filename} ({idx+1}/{total_files})"
                self.update_progress(progress_message)
                
                file_path = os.path.join(input_folder, filename)
                translated_file_path = os.path.join(output_folder, filename)
                self.translate_file(file_path, translated_file_path)

                self.progress["value"] = (idx + 1) / total_files * 100
                self.master.update_idletasks()

            self.update_progress("翻译任务完成！")
            messagebox.showinfo("完成", "翻译任务已完成！")
        except Exception as e:
            self.update_progress(f"发生错误: {str(e)}")
            messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(e)}")
        finally:
            self.translate_button.config(state="normal")
            self.input_button.config(state="normal")
            self.output_button.config(state="normal")
            self.progress["value"] = 0

    def translate_file(self, input_path, output_path):
        """翻译单个文件"""
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
        """翻译 Markdown 内容（新增 Obsidian 双链处理）"""
        patterns = [
            # 新增 Obsidian 双链匹配规则（优先处理）
            (r'(\[\[.*?\]\])', 'obsidian_link'),
            # 原有匹配规则
            (r'^(\s*[-*+]\s+)(.*)', 'list'),
            (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),
            (r'^(#+\s+)(.*)', 'header'),
            (r'(\[.*?\]\(.*?\))', 'markdown_link'),
            (r'(`.+?`)', 'inline_code')
        ]

        for pattern, pattern_type in patterns:
            match = re.search(pattern, line)
            if match:
                # 处理 Obsidian 双链
                if pattern_type == 'obsidian_link' and self.obsidian_var.get():
                    return line  # 完全保留原始内容
                
                # 处理其他类型
                if pattern_type in ['list', 'ordered_list', 'header']:
                    symbol, content = match.groups()
                    translated_content = translate_client.translate(content, target_language='en')['translatedText']
                    return f"{symbol}{translated_content}"
                elif pattern_type in ['markdown_link', 'inline_code']:
                    return line  # 保留标准 Markdown 语法
                
        # 普通文本翻译
        return translate_client.translate(line, target_language='en')['translatedText']

    def update_progress(self, message):
        """更新进度信息"""
        self.progress_text_box.insert("end", message + "\n")
        self.progress_text_box.see("end")
        self.master.update_idletasks()

if __name__ == '__main__':
    root = Tk()
    app = TranslationApp(root)
    root.mainloop()
