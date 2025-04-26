import os
from lxml import etree
import json

def parse_recipe(recipe_element, book_id, cookbook_title):
    """解析单个食谱元素，提取关键信息"""
    data = {
        "name": "",
        "class1": recipe_element.get("class1", ""),
        "class2": recipe_element.get("class2", ""),  # 如果有 class2，记得提取
        "ethnic_group": recipe_element.get("ethnicgroup", ""),
        "region": recipe_element.get("region", ""),  # 如果有 region，记得提取
        "ingredients": [],
        "implements": [],
        "book_id": book_id,  # 传递 book_id
        "cookbook_title": cookbook_title  # 传递 cookbook_title
    }
    
    # 提取菜名（从purpose元素），将其中的ingredient一并加入
    purpose = recipe_element.find(".//purpose")
    if purpose is not None:
        name_parts = []
        
        # 遍历purpose元素中的所有子元素（包括文本和ingredient）
        for elem in purpose.iter():
            if elem.tag == "ingredient" and elem.text:
                name_parts.append(elem.text.strip())
            elif elem.tag == "purpose":
                # 将<purpose>标签内的文本加入菜名
                if elem.text:
                    name_parts.append(elem.text.strip())
        
        # 拼接成完整的菜名
        data["name"] = " ".join(name_parts).strip()
    
    # 提取所有食材（去重）
    ingredients = set()
    for ing in recipe_element.xpath(".//ingredient"):
        if ing.text:
            ingredients.add(ing.text.strip().rstrip(',;.'))  # 去除末尾标点
    data["ingredients"] = sorted(list(ingredients))
    
    # 提取所有工具（去重）
    implements = set()
    for imp in recipe_element.xpath(".//implement"):
        if imp.text:
            implements.add(imp.text.strip().rstrip(',;.'))
    data["implements"] = sorted(list(implements))
    
    return data


def parse_cookbook(xml_path):
    """解析整个食谱XML文件"""
    try:
        tree = etree.parse(xml_path)
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return None
    
    # 提取元数据
    metadata = {
        "title": "",
        "author": "",
        "book_id": tree.getroot().get("bookID", "")
    }
    
    # 提取标题（从dcTitle或doctitle部分）
    title_elem = tree.find(".//dcTitle")
    if title_elem is not None and title_elem.text:
        metadata["title"] = title_elem.text.strip()
    else:
        doctitle_elem = tree.find(".//doctitle")
        if doctitle_elem is not None and doctitle_elem.text:
            metadata["title"] = doctitle_elem.text.strip()
    
    # 如果没有找到标题，打印文件名
    if not metadata["title"]:
        print(f"Warning: No title found in file: {xml_path}")
    
    # 提取作者（从dcCreator或docauthor）
    author_elem = tree.find(".//dcCreator")
    if author_elem is not None and author_elem.text:
        metadata["author"] = author_elem.text.strip()
    else:
        docauthor = tree.find(".//docauthor")
        if docauthor is not None and docauthor.text:
            metadata["author"] = docauthor.text.strip()
    
    # 提取所有食谱
    recipes = []
    for recipe_elem in tree.xpath("//recipe"):
        recipe_data = parse_recipe(recipe_elem, metadata["book_id"], metadata["title"])
        if recipe_data["name"]:  # 只保留有名称的食谱
            recipes.append(recipe_data)
    
    return {
        "metadata": metadata,
        "recipes": recipes
    }

def save_results(data, original_path):
    """保存提取结果到JSON文件"""
    base_name = os.path.splitext(os.path.basename(original_path))[0]  # 提取文件名，不包含路径
    output_dir = "single_cookbook_extractions"
    
    # 确保保存文件的目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保持 .json 扩展名，保存为JSON
    output_path = f"{output_dir}/{base_name}_extracted.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_path}")
    return output_path

def process_single_cookbook(xml_path):
    """处理单个食谱XML文件"""
    print(f"Processing {xml_path}...")
    
    # 解析文件
    cookbook_data = parse_cookbook(xml_path)
    if not cookbook_data:
        return
    
    # 保存结果
    save_results(cookbook_data, xml_path)
    
    # 打印摘要信息
    print(f"Extracted {len(cookbook_data['recipes'])} recipes from:")
    print(f"Title: {cookbook_data['metadata']['title']}")
    print(f"Author: {cookbook_data['metadata']['author']}")
    print(f"Book ID: {cookbook_data['metadata']['book_id']}")

if __name__ == "__main__":
    xml_file = "cookbook_textencoded/miss.xml"      
    if os.path.exists(xml_file):
        process_single_cookbook(xml_file)
    else:
        print(f"File not found: {xml_file}")
