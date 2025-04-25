from flask import Flask, render_template, send_from_directory
import cobra
from pathlib import Path
import pandas as pd
import re
import os
import io, sys
import json

app = Flask(__name__, template_folder='wiki')

# 全局变量存储模型
model = None
model_id=None
confirm=[]

def process_file(file_path):
    """
    自定义文件处理函数
    这里只是一个示例，你可以替换成任何你需要对文件进行的操作
    返回一个包含文件信息的字典
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
    扫描目录并生成 JSON 报告
    
    参数:
        directory_path: 要扫描的目录路径
        output_json:     输出的 JSON 文件路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    # 收集所有文件信息
    all_files_info = []
    
    for root, dirs, files in os.walk(directory_path):
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

def export_reactions_json(model, rxn_csv_path, output_json_path):
    """
    将模型反应信息导出为纯净JSON文件
    
    参数:
        model: SBML模型
        rxn_csv_path: 反应ID到名称的映射CSV路径
        output_json_path: 输出JSON路径
    """
    # 加载代谢模型
    
    # 读取ID-名称映射表
    name_mapping = {}
    try:
        rxn_df = pd.read_csv(rxn_csv_path, header=None, names=['id', 'name'])
        name_mapping = rxn_df.set_index('id')['name'].to_dict()
    except FileNotFoundError:
        print(f"⚠️ 未找到映射文件 {rxn_csv_path}，将直接使用反应ID作为名称")

    # 构建反应数据
    reactions = []
    for rxn in model.reactions:
        reactions.append({
            "id": rxn.id,
            "name": name_mapping.get(rxn.id, rxn.id),  # 自动回退到ID
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

def replace_rs(summary):
    met_df = pd.read_csv("./met.csv", header=None, names=['id', 'name'])
    rxn_df = pd.read_csv("./rxn.csv", header=None, names=['id', 'name'])
    met_dict = dict(zip(met_df['id'].str.strip(), met_df['name'].str.strip()))
    rxn_dict = dict(zip(rxn_df['id'].str.strip(), rxn_df['name'].str.strip()))
    pattern = re.compile(r'(\b[sr]_\d+)(\[[a-z]+\])?\b')
    
    def replace_match(match):
        full_id = match.group(0)
        base_id = match.group(1)
        if base_id.startswith('s_') and base_id in met_dict:
            return met_dict[base_id]
        elif base_id.startswith('r_') and base_id in rxn_dict:
            return rxn_dict[base_id]
        return full_id
    
    return pattern.sub(replace_match, summary)

@app.route('/model.json')
def serve_model():
    return send_from_directory('.', 'model.json')

@app.route('/reaction.json')
def serve_reaction():
    if model is None:
        return "No model loaded."
    r_path=model_id+'.json'
    return send_from_directory('reactions', r_path)

@app.route('/gene.json')
def serve_gene():
    if model is None:
        return "No model loaded."
    g_path=model_id+'.json'
    return send_from_directory('genes', g_path)

@app.route('/')
def home():
    # scan_directory_and_generate_json('./models', './model.json')
    return render_template('pages/model.html')

@app.route('/model/<id>')
def set_model(id):
    global model
    global model_id
    model_id=id
    model_path = Path('models') / f'{id}.xml'
    model = cobra.io.read_sbml_model(str(model_path))
    export_r_path='reactions/'+id+'.json'
    export_g_path='genes/'+id+'.json'
    export_reactions_json(model,'./rxn.csv',export_r_path )
    export_genes_json(model,export_g_path )
    return f"Model {id} loaded successfully."

@app.route('/objective/<reaction_id>')
def set_objective(reaction_id):
    global model
    if model is None:
        return "No model loaded."
    model.objective = model.reactions.get_by_id(reaction_id)
    return f"Objective set to reaction {reaction_id}."

@app.route('/reaction/<reaction_id>/<lower>/<upper>')
def set_reaction(reaction_id, lower, upper):
    global model
    if model is None:
        return "No model loaded."
    reaction = model.reactions.get_by_id(reaction_id)
    reaction.lower_bound = float(lower)
    reaction.upper_bound = float(upper)
    return f"Reaction {reaction_id} bounds set to [{lower}, {upper}]."

@app.route('/gene/<gene_id>')
def knock_out_gene(gene_id):
    global model
    if model is None:
        return "No model loaded."
    model.genes.get_by_id(gene_id).knock_out()
    return f"Gene {gene_id} knocked out."

@app.route('/optimize')
def optimize():
    global model
    if model is None:
        return "No model loaded."
    solution = model.optimize()
 # 1. 创建 StringIO 并替换 stdout
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    print()
    # 2. 执行原本会打印的逻辑
    print('Optimal flux:', solution.objective_value)
    print(model.objective.expression)
    print('Status:', solution.status)
    summary_str = str(model.summary())
    replaced_summary = replace_rs(summary_str)
    print(replaced_summary)

    # 3. 恢复 stdout，并获取输出内容
    sys.stdout = old_stdout
    output = buf.getvalue()
    buf.close()

    # 4. 渲染到模板
    return render_template('pages/result.html', result=output)

@app.route('/pages/<page>')
def pages(page):
    return render_template(f'pages/{page.lower()}.html')

if __name__ == "__main__":
    app.run(port=8080)
