import cobra
from pathlib import Path
import os
import json

def process_file(file_path):
    """
    模型文件处理函数
    返回一个包含模型信息的字典
    """
    file_info = {}

    # 加载代谢模型
    model = cobra.io.read_sbml_model(file_path)

    # 提取文件名（不含后缀）
    base, _ = os.path.splitext(os.path.basename(file_path))
    file_info['ID']                = base
    file_info['Metabolite_count']  = len(model.metabolites)
    file_info['Gene_count']        = len(model.genes)
    file_info['Reaction_count']    = len(model.reactions)

    return file_info

def scan_directory_and_generate_json(directory_path, output_json):
    """
    扫描模型目录并生成 JSON 报告
    
    参数:
        directory_path: 要扫描的目录路径
        output_json:     输出的 JSON 文件路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    # 收集所有文件信息
    all_files_info = []
    
    for root,files in os.walk(directory_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                info = process_file(file_path)
                all_files_info.append(info)
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
                continue
    
    if not all_files_info:
        print("没有找到任何有效的 SBML 文件。")
        return
    
    # 写入 JSON 文件
    with open(output_json, 'w', encoding='utf-8') as jf:
        json.dump(all_files_info, jf, ensure_ascii=False, indent=2)
    
    print(f"成功处理 {len(all_files_info)} 个文件，结果已保存到 {output_json}")

def export_reactions_json(model, output_json_path):
    """
    将模型反应信息导出为纯净JSON文件
    
    参数:
        model: SBML模型
        rxn_csv_path: 反应ID到名称的映射CSV路径
        output_json_path: 输出JSON路径
    """

    # 构建反应数据
    reactions = []
    for rxn in model.reactions:
        reactions.append({
            "name": rxn.id,
            "reaction": rxn.build_reaction_string(),
            "lower_bound": float(rxn.lower_bound),
            "upper_bound": float(rxn.upper_bound)
        })

    # 写入JSON文件
    Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(reactions, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 成功导出 {len(reactions)} 个反应到 {output_json_path}")

def export_genes_json(model,output_json_path):
    """
    将模型基因信息导出为纯净JSON文件
    
    参数:
        model: SBML模型
        output_json_path: 输出JSON路径
    """
    # 加载代谢模型
    

    # 构建反应数据
    genes = []
    for gene in model.genes:
        genes.append({
            "id": gene.id
        })

    # 写入JSON文件
    Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(genes, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 成功导出 {len(genes)} 个反应到 {output_json_path}")
