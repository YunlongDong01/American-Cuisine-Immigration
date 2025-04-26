import os
import json
from lxml import etree
from tqdm import tqdm
import multiprocessing
import re

from parse_recipe import parse_recipe


def process_single_file(xml_path):
    """处理单个 XML 文件"""
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        # 使用文件名作为唯一标识符
        file_id = os.path.splitext(os.path.basename(xml_path))[0]

        # 提取 bookid
        bookid = root.get("bookID", "").strip()
        if not bookid:  # 如果 bookid 为空，跳过该文件: 已验证那些文件是空的
            print(f"Skipping file {xml_path} due to empty book content.")
            return None
        
        # 提取所有作者
        authors = []
        for creator in root.xpath(".//dcCreator"):
            raw_author = creator.text.strip()
            if "," in raw_author:
                # 如果作者字段包含逗号，重新排序
                parts = raw_author.split(",")
                formatted_author = f"{parts[1].strip()} {parts[0].strip()}"
            else:
                formatted_author = raw_author
            authors.append(formatted_author)
        # author = "; ".join(authors)  # 使用分号分隔多个作者
        
        # 提取元数据
        publisher = root.findtext(".//dcPublisher", "").strip()
        subregion = root.get("subregion", "").strip()
        publishregion = ""

        if publisher:
            # 特殊处理规则
            if file_id == "amwh":
                publishregion = "New York, Boston"
            elif file_id == "favd":
                publishregion = "Chicago"
            elif file_id == "hosf":
                publishregion = "Chicago"
            elif file_id == "oldv":
                publishregion = "Richmond"
            elif file_id == "scie":
                publishregion = "Chicago"
            else:
                # 默认处理逻辑
                if ":" in publisher:
                    publishregion = publisher.split(":")[0].strip()
                    if "," in publishregion:
                        publishregion = publishregion.split(",")[0].strip()
                elif "," in publisher:
                    publishregion = publisher.split(",")[0].strip()
                
                elif ";" in publisher:
                    publishregion = publisher.split(";")[0].strip()
                else:
                    publishregion = publisher
            if " and " in publishregion:
                    publishregion = "; ".join(publishregion.split(" and "))

        metadata = {
            "fileid": file_id,
            "bookid": bookid,
            "title": (root.findtext(".//dcTitle", "").strip() or root.findtext(".//doctitle", "").strip()).replace(".", ""),
            "subject": [
                subject.strip().replace(" ", "") for subject in re.split(r'[;.]', 
                root.findtext(".//dcSubject", "").strip()) if subject.strip()
            ],  # 使用分号和句号分隔多个主题，并去掉所有空格
            # "description": root.findtext(".//dcDescription", "").strip(),
            "author": authors, 
            # "creator_nationality": root.findtext(".//dcCreatorNation", "").strip(),  # 如果需要的话可能只能手动添加
            "publisher": publisher,
            "publish_region": publishregion,  
            "date": root.findtext(".//dcDate", "").strip(),
            "language": root.findtext(".//dcLanguage", "").strip(),
            "region": root.get("region", ""),  # 默认值设为 general
            "subregion": subregion, 
            "ethnic_group": root.get("ethnicgroup", ""), 
            "type": root.get("type", ""),
            "class1": root.get("class1", ""),
            "class2": root.get("class2", ""),
        }

        # 提取所有食谱
        recipes = []
        for recipe_elem in root.xpath("//recipe"):
            recipe_data = parse_recipe(recipe_elem, file_id, metadata["title"])
            if recipe_data["name"]:
                # 提取更完整的食谱内容
                recipe_data.update({
                    "id": file_id,  # 在每个食谱中添加文件名作为标识符
                    "ingredients": [
                        ingredient.text.strip() for ingredient in recipe_elem.xpath(".//ingredient") if ingredient.text
                    ],
                    "process": [
                        process.text.strip() for process in recipe_elem.xpath(".//process") if process.text
                    ],
                    "implements": [
                        implement.text.strip() for implement in recipe_elem.xpath(".//implement") if implement.text
                    ],
                    "variations": [
                        variation.text.strip() for variation in recipe_elem.xpath(".//variation") if variation.text
                    ],
                })
                recipes.append(recipe_data)

        return {
            "metadata": metadata,
            "recipes": recipes,
            "source_file": xml_path
        }
    except Exception as e:
        print(f"Error processing {xml_path}: {str(e)}")
        return None


def batch_process_xml(input_dir, metadata_output="cookbooks_extracted_metadata.json", recipes_output="cookbooks_extracted_recipes.json"):
    """批量处理目录中的所有 XML 文件"""
    metadata_list = []
    recipes_list = []
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
            metadata_list.append(result["metadata"])
            recipes_list.extend(result["recipes"])

    # 保存元数据
    with open(metadata_output, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)

    # 保存食谱数据
    with open(recipes_output, "w", encoding="utf-8") as f:
        json.dump(recipes_list, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing completed.")
    print(f"Metadata saved to {metadata_output}")
    print(f"Recipes saved to {recipes_output}")
    print(f"Total books: {len(metadata_list)}")
    print(f"Total recipes: {len(recipes_list)}")
    return metadata_list, recipes_list


# 使用示例
if __name__ == "__main__":
    input_directory = "cookbook_textencoded"
    batch_process_xml(input_directory)