import sqlite3
import re
from pathlib import Path

class HTMLToPythonConverter:
    def __init__(self, db_name='html_analysis.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS html_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL,
                tag_content TEXT,
                line_number INTEGER,
                file_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS py_conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id INTEGER,
                py_code TEXT,
                conversion_type TEXT,
                FOREIGN KEY (tag_id) REFERENCES html_tags (id)
            )
        ''')
        conn.commit()
        conn.close()
    
    def extract_html_tags(self, html_file_path):
        html_file = Path(html_file_path)
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'<(\w+)[^>]*>(.*?)</\1>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        for i, (tag, content) in enumerate(matches):
            clean_content = re.sub(r'<[^>]+>', '', content).strip()
            if clean_content:
                cursor.execute('''
                    INSERT INTO html_tags (tag_name, tag_content, line_number, file_name)
                    VALUES (?, ?, ?, ?)
                ''', (tag, clean_content, i+1, html_file.name))
        
        conn.commit()
        conn.close()
        return len(matches)
    
    def convert_to_python_script(self, html_file_path, output_py_file='html_generated.py'):
        self.extract_html_tags(html_file_path)
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tag_name, tag_content FROM html_tags')
        tags_data = cursor.fetchall()
        
        py_lines = [
            '#!/usr/bin/env python3',
            '# -*- coding: utf-8 -*-',
            '# 自动生成的Python脚本 - 源自HTML转换',
            '',
            'import re',
            'from datetime import datetime',
            '',
            'class HTMLProcessor:',
            '    def __init__(self):',
            '        self.content = []',
            '        self.tags_count = {}',
            '',
            '    def process_content(self):'
        ]
        
        conversion_rules = {
            'h1': lambda text: f'        print("标题: {text}")',
            'h2': lambda text: f'        print("子标题: {text}")',
            'h3': lambda text: f'        print("三级标题: {text}")',
            'p': lambda text: f'        self.content.append(\'{{"type": "paragraph", "text": "{text}"}}\')',
            'div': lambda text: f'        print(f"容器内容: {{len(\"{text[:50]}...\" if len(\"{text}\") > 50 else \"{text}\")}}字符")',
            'span': lambda text: f'        print(f"行内元素: {text}")',
            'a': lambda text: f'        print(f"链接文本: {text}")'
        }
        
        for tag, content in tags_data:
            if tag in conversion_rules:
                py_code = conversion_rules[tag](content)
                py_lines.append(py_code)
                
                cursor.execute('''
                    INSERT INTO py_conversions (tag_id, py_code, conversion_type)
                    SELECT id, ?, ? FROM html_tags 
                    WHERE tag_name=? AND tag_content=?
                ''', (py_code, 'auto', tag, content))
            else:
                default_py = f'        print(f"未知标签<{tag}>: {content}")'
                py_lines.append(default_py)
        
        py_lines.extend([
            '',
            '    def generate_output(self):',
            '        return {',
            '            "total_elements": len(self.content),',
            '            "timestamp": datetime.now().isoformat(),',
            '            "content": self.content',
            '        }',
            '',
            'def main():',
            '    processor = HTMLProcessor()',
            '    print("开始处理HTML内容...")',
            '    processor.process_content()',
            '    result = processor.generate_output()',
            '    print(f"处理完成! 共处理{len(processor.content)}个元素")',
            '    return result',
            '',
            'if __name__ == "__main__":',
            '    main()'
        ])
        
        with open(output_py_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(py_lines))
        
        conn.commit()
        conn.close()
        
        print(f"Python脚本已生成: {output_py_file}")
        print(f"数据库文件: {self.db_name}")
        return output_py_file
    
    def generate_smart_conversion(self, html_file_path, output_py_file='smart_html_processor.py'):
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        structure = self.analyze_html_structure(html_content)
        
        py_code = self.create_smart_processor(structure, html_file_path)
        
        with open(output_py_file, 'w', encoding='utf-8') as f:
            f.write(py_code)
        
        cursor.execute('''
            INSERT INTO py_conversions (tag_id, py_code, conversion_type)
            VALUES (NULL, ?, ?)
        ''', (py_code[:500] + '...' if len(py_code) > 500 else py_code, 'smart'))
        
        conn.commit()
        conn.close()
        
        return output_py_file
    
    def analyze_html_structure(self, html_content):
        structure = {
            'tags': {},
            'depths': [],
            'text_blocks': []
        }
        
        lines = html_content.split('\n')
        depth = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            opening_tags = re.findall(r'<(\w+)[^>]*>', line)
            closing_tags = re.findall(r'</(\w+)>', line)
            
            for tag in opening_tags:
                if tag not in structure['tags']:
                    structure['tags'][tag] = 0
                structure['tags'][tag] += 1
            
            depth += len(opening_tags) - len(closing_tags)
            structure['depths'].append(depth)
            
            text_match = re.search(r'>([^<]+)<', line)
            if text_match:
                structure['text_blocks'].append(text_match.group(1).strip())
        
        return structure
    
    def create_smart_processor(self, structure, original_file):
        tag_functions = []
        
        for tag, count in structure['tags'].items():
            func_template = f'''
    def process_{tag}(self, text):
        """
        处理{tag.upper()}标签内容
        出现次数: {count}
        """
        # 基本处理逻辑
        if not text or not text.strip():
            return None
        
        processed = text.strip()
        
        # 根据标签类型应用不同处理
        if "{tag}" in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            return {{"type": "heading", "level": int("{tag}"[1]), "text": processed}}
        elif "{tag}" in ["p", "div", "span"]:
            return {{"type": "text_block", "tag": "{tag}", "text": processed}}
        elif "{tag}" == "a":
            # 链接特殊处理
            return {{"type": "link", "text": processed}}
        else:
            return {{"type": "element", "tag": "{tag}", "text": processed}}
'''
            tag_functions.append(func_template)
        
        main_processor = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 智能HTML处理器
# 源文件: {original_file}
# 分析统计:
{chr(10).join([f"# - {tag}: {count}次" for tag, count in structure['tags'].items()])}

import re
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class HTMLElement:
    tag: str
    content: str
    attributes: Dict[str, str]
    depth: int

class SmartHTMLProcessor:
    """智能HTML内容处理器"""
    
    def __init__(self):
        self.elements: List[HTMLElement] = []
        self.stats = {{tag: 0 for tag in {list(structure['tags'].keys())}}}
    
{chr(10).join(tag_functions)}
    
    def parse_html(self, html_content: str):
        """解析HTML内容"""
        pattern = r'<(\w+)([^>]*)>([^<]*)</\\1>'
        matches = re.findall(pattern, html_content, re.DOTALL)
        
        for tag, attrs, content in matches:
            self.stats[tag] = self.stats.get(tag, 0) + 1
            
            # 提取属性
            attr_dict = {{}}
            attr_matches = re.findall(r'(\w+)="([^"]*)"', attrs)
            for name, value in attr_matches:
                attr_dict[name] = value
            
            element = HTMLElement(
                tag=tag,
                content=content.strip(),
                attributes=attr_dict,
                depth=0
            )
            self.elements.append(element)
    
    def generate_python_code(self):
        """生成Python代码表示"""
        code_lines = [
            '# 自动生成的HTML处理代码',
            'def process_html_data():',
            '    data = []'
        ]
        
        for element in self.elements:
            processor_func = f"process_{element.tag}"
            code_lines.append(f'    # 处理 <{element.tag}> 元素')
            if element.content:
                code_lines.append(f'    text = "{element.content}"')
                code_lines.append(f'    processed = self.{processor_func}(text)')
                code_lines.append('    if processed:')
                code_lines.append('        data.append(processed)')
            code_lines.append('')
        
        code_lines.extend([
            '    return data',
            '',
            'def print_statistics():',
            f'    stats = {structure['tags']}',
            '    for tag, count in stats.items():',
            '        print(f"标签<{tag}>: {{count}}次")',
            '',
            'if __name__ == "__main__":',
            '    processor = SmartHTMLProcessor()',
            '    print("HTML智能处理器已启动")',
            '    print_statistics()'
        ])
        
        return chr(10).join(code_lines)

def main():
    processor = SmartHTMLProcessor()
    print("智能HTML处理器初始化完成")
    print("各标签处理函数已生成")
    
    # 示例：显示生成的代码结构
    print("\\n生成的Python代码结构:")
    for tag in {list(structure['tags'].keys())}:
        print(f"  - process_{tag}() 函数")
    
    return processor

if __name__ == "__main__":
    main()
'''
        
        return main_processor

def main():
    converter = HTMLToPythonConverter()
    
    html_file = input("请输入HTML文件路径: ").strip()
    
    if not Path(html_file).exists():
        print(f"错误: 文件 {html_file} 不存在")
        return
    
    print(f"正在处理: {html_file}")
    
    tags_count = converter.extract_html_tags(html_file)
    print(f"提取了 {tags_count} 个HTML标签")
    
    output_file = converter.convert_to_python_script(html_file, "output_html.py")
    
    print("\\n=== 转换选项 ===")
    print("1. 基本转换 (已生成)")
    print("2. 智能转换 (推荐)")
    
    choice = input("请选择转换类型 (1-2, 默认2): ").strip()
    
    if choice == "1":
        print(f"基本转换完成: {output_file}")
    else:
        smart_file = converter.generate_smart_conversion(html_file, "smart_html_processor.py")
        print(f"智能转换完成: {smart_file}")
    
    print("\\n=== 使用说明 ===")
    print("1. 运行生成的Python文件: python output_html.py")
    print("2. 查看数据库: sqlite3 html_analysis.db")
    print("3. 查询提取的内容: SELECT * FROM html_tags;")

if __name__ == "__main__":
    main()
