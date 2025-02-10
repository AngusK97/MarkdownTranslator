import html
import re
from google.cloud import translate_v2 as translate

def translate_file(input_path, output_path, source_lang, target_lang, keep_obsidian_links):
    translate_client = translate.Client()
    with open(input_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    translated_lines = []
    for line in lines:
        line_content = line.rstrip('\n')
        if not line_content.strip():
            translated_lines.append('\n')
            continue
        translated_line = process_markdown_line(translate_client, line_content, source_lang, target_lang, keep_obsidian_links)
        translated_lines.append(translated_line + '\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(translated_lines)

def process_markdown_line(translate_client, line, source_lang, target_lang, keep_obsidian_links):
    # 定义正则表达式模式
    patterns = [
        (r'(\[\[.*?\]\])', 'obsidian_link'),
        (r'^(\s*[-*+]\s+)(.*)', 'list'),
        (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),
        (r'^(#+\s+)(.*)', 'header'),
        (r'(\[.*?\]\(.*?\))', 'markdown_link'),
        (r'(`.+?`)', 'inline_code')
    ]

    # 检查是否有 Obsidian 链接
    obsidian_links = re.findall(r'(\[\[.*?\]\])', line)
    if obsidian_links:
        if keep_obsidian_links:
            # 用占位符替换 Obsidian 链接
            for i, link in enumerate(obsidian_links):
                placeholder = f"@@link{i}@@"
                line = line.replace(link, placeholder)

            # 进行翻译
            translated_line = translate_client.translate(line, source_language=source_lang, target_language=target_lang)['translatedText']

            # 将占位符替换回原来的 Obsidian 链接
            for i, link in enumerate(obsidian_links):
                placeholder = f"@@link{i}@@"
                translated_line = translated_line.replace(placeholder, link)

            return html.unescape(translated_line)

        # 如果未勾选，直接翻译整行，包含 Obsidian 链接
        return html.unescape(translate_client.translate(line, source_language=source_lang, target_language=target_lang)['translatedText'])

    # 如果没有 Obsidian 链接，继续原来的逻辑
    for pattern, pattern_type in patterns:
        match = re.search(pattern, line)
        if match:
            if pattern_type in ['list', 'ordered_list', 'header']:
                symbol, content = match.groups()
                result = translate_client.translate(content, source_language=source_lang, target_language=target_lang)['translatedText']
                translated_content = html.unescape(result)
                return f"{symbol}{translated_content}"
            elif pattern_type in ['markdown_link', 'inline_code']:
                return line

    # 最终返回翻译结果
    result = translate_client.translate(line, source_language=source_lang, target_language=target_lang)['translatedText']
    return html.unescape(result)