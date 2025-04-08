import os
import json
from lxml import etree
from tqdm import tqdm  # 进度条
import multiprocessing
from collections import defaultdict

def parse_recipe(recipe_element):
    """解析单个食谱元素"""
    data = {
        "name": "",
        "class1": recipe_element.get("class1", ""),
        "class2": recipe_element.get("class2", ""),
        "ethnic_group": recipe_element.get("ethnicgroup", ""),
        "region": recipe_element.get("region", ""),
        "ingredients": list(set(
            ing.text.strip().rstrip(',;.') 
            for ing in recipe_element.xpath(".//ingredient") 
            if ing.text
        )),
        "implements": list(set(
            imp.text.strip().rstrip(',;.') 
            for imp in recipe_element.xpath(".//implement") 
            if imp.text
        )),
        "source_book": ""  # 将在后续填充
    }
    
    if purpose := recipe_element.find(".//purpose"):
        data["name"] = purpose.text.strip() if purpose.text else ""
    return data

def process_single_file(xml_path):
    """处理单个XML文件"""
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()
        book_id = root.get("bookID", os.path.splitext(os.path.basename(xml_path))[0])
        
        # 提取元数据
        metadata = {
            "title": (root.find(".//dcTitle").text.strip() 
                     if root.find(".//dcTitle") is not None 
                     else os.path.basename(xml_path)),
            "author": (root.find(".//dcCreator").text.strip() 
                      if root.find(".//dcCreator") is not None 
                      else "Unknown"),
            "book_id": book_id,
            "ethnic_group": root.get("ethnicgroup", ""),
            "region": root.get("region", "")
        }

        # 提取所有食谱
        recipes = []
        for recipe_elem in root.xpath("//recipe"):
            recipe_data = parse_recipe(recipe_elem)
            if recipe_data["name"]:
                recipe_data["source_book"] = f"{metadata['title']} ({book_id})"
                recipes.append(recipe_data)
        
        return {
            "metadata": metadata,
            "recipes": recipes,
            "source_file": xml_path
        }
    except Exception as e:
        print(f"Error processing {xml_path}: {str(e)}")
        return None

def batch_process_xml(input_dir, output_json="cookbooks_collection.json"):
    """批量处理目录中的所有XML文件"""
    all_data = {"books": [], "recipes": []}
    xml_files = [f for f in os.listdir(input_dir) if f.endswith(".xml")]
    
    print(f"Found {len(xml_files)} XML files to process...")
    
    # 使用多线程加速处理
    with multiprocessing.Pool(processes=min(4, multiprocessing.cpu_count())) as pool:
        results = list(tqdm(
            pool.imap(process_single_file, 
                     [os.path.join(input_dir, f) for f in xml_files]),
            total=len(xml_files)
        ))
    
    # 合并结果
    for result in results:
        if result:
            all_data["books"].append(result["metadata"])
            all_data["recipes"].extend(result["recipes"])
    
    # 保存结果
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing completed. Results saved to {output_json}")
    print(f"Total books: {len(all_data['books'])}")
    print(f"Total recipes: {len(all_data['recipes'])}")
    return all_data

# 使用示例
if __name__ == "__main__":
    input_directory = "cookbook_textencoded"  # 替换为实际路径
    batch_process_xml(input_directory)