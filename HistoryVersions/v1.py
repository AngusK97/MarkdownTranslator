import os
import time
import re
from tkinter import Tk, filedialog
from google.cloud import translate_v2 as translate

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"E:\Download\united-column-450109-f0-98230610e0a0.json"
translate_client = translate.Client()


def select_folder():
    Tk().withdraw()
    return filedialog.askdirectory()


def translate_text(text, target_language='en'):
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result['translatedText']
    except Exception as e:
        print(f"翻译时出错: {e}")
        return None


def process_markdown_line(line):
    """处理单行 Markdown，保留符号并翻译内容"""
    # 匹配 Markdown 列表项、标题等
    patterns = [
        (r'^(\s*[-*+]\s+)(.*)', 'list'),  # 列表项：- 内容
        (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),  # 有序列表：1. 内容
        (r'^(#+\s+)(.*)', 'header'),  # 标题
        (r'^(\s*`{3,}\s*.*)', 'code_block'),  # 代码块标记
        (r'(\[.*?\]\(.*?\))', 'link'),  # 链接
        (r'(`.+?`)', 'inline_code')  # 行内代码
    ]

    for pattern, pattern_type in patterns:
        match = re.match(pattern, line)
        if match:
            if pattern_type in ['list', 'ordered_list', 'header']:
                # 分离符号和内容，只翻译内容部分
                symbol, content = match.groups()
                translated_content = translate_text(content) if content.strip() else ""
                return f"{symbol}{translated_content}"
            elif pattern_type in ['code_block', 'inline_code', 'link']:
                # 保留代码块、行内代码、链接不翻译
                return line
    # 普通文本直接翻译整行
    return translate_text(line) if line.strip() else line


def process_files(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('.md'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            translated_lines = []
            print(f"正在翻译: {filename}")
            for line in lines:
                line_content = line.rstrip('\n')  # 保留行首行尾空格（除了换行符）
                if not line_content.strip():  # 处理空行
                    translated_lines.append('\n')
                    continue
                # 翻译并保留换行符
                translated_line = process_markdown_line(line_content)
                translated_lines.append(translated_line + '\n')
                time.sleep(0.5)

            # 保存文件
            translated_file_path = os.path.join(folder_path, 'translated', filename)
            os.makedirs(os.path.dirname(translated_file_path), exist_ok=True)
            with open(translated_file_path, 'w', encoding='utf-8') as f:
                f.writelines(translated_lines)
            print(f"翻译成功: {filename}")


def main():
    folder_path = select_folder()
    if folder_path:
        print(f"选择的文件夹路径: {folder_path}")
        process_files(folder_path)
    else:
        print("未选择文件夹")


if __name__ == '__main__':
    main()
