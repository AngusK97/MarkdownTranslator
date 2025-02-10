import os
import html
import re
from google.cloud import translate_v2 as translate

def translate_file(input_path, output_path, source_lang, target_lang):
    translate_client = translate.Client()
    with open(input_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    translated_lines = []
    for line in lines:
        line_content = line.rstrip('\n')
        if not line_content.strip():
            translated_lines.append('\n')
            continue
        translated_line = process_markdown_line(translate_client, line_content, source_lang, target_lang)
        translated_lines.append(translated_line + '\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(translated_lines)

def process_markdown_line(translate_client, line, source_lang, target_lang):
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
            if pattern_type == 'obsidian_link':
                return line  # Return unmodified for obsidian links
            if pattern_type in ['list', 'ordered_list', 'header']:
                symbol, content = match.groups()
                result = translate_client.translate(content, source_language=source_lang, target_language=target_lang)['translatedText']
                translated_content = html.unescape(result)
                return f"{symbol}{translated_content}"
            elif pattern_type in ['markdown_link', 'inline_code']:
                return line
    result = translate_client.translate(line, source_language=source_lang, target_language=target_lang)['translatedText']
    return html.unescape(result)
