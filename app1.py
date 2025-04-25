from os import path
import os
from pathlib import Path
import cobra
import pandas as pd
import re
from flask import send_from_directory
from flask import Flask, render_template

def display_reaction_info(model):
    """
    显示模型中所有反应的信息
    
    参数:
        model_path: 模型文件路径
        rxn_csv_path: 包含反应ID到名称映射的CSV文件路径
    """
    # 1. 加载模型
    rxn_csv_path="./rxn.csv"
    
    # 2. 读取反应ID到名称的映射
    try:
        rxn_df = pd.read_csv(rxn_csv_path, header=None, names=['reaction_id', 'name'])
        id_to_name = dict(zip(rxn_df['reaction_id'], rxn_df['name']))
    except FileNotFoundError:
        print(f"警告: 未找到反应名称映射文件 {rxn_csv_path}, 将使用反应ID作为名称")
        id_to_name = {}
    
    # 3. 遍历所有反应并显示信息
    print("{:<15} {:<50} {:<15} {:<15} {:<15}".format(
        "ID", "Name", "Reaction", "Lower bound", "Upper bound"))
    print("="*110)
    
    for reaction in model.reactions:
        # 获取反应名称
        name = id_to_name.get(reaction.id, reaction.id)  # 如果找不到映射，使用反应ID
        
        # 获取反应方程式
        reaction_eq = reaction.build_reaction_string()
        
        # 打印信息
        print("{:<15} {:<50} {:<15} {:<15.2f} {:<15.2f}".format(
            reaction.id,
            name,
            reaction_eq,
            reaction.lower_bound,
            reaction.upper_bound
        ))

def replace_rs(summary):
    met_df = pd.read_csv("./met.csv", header=None, names=['id', 'name'])
    rxn_df = pd.read_csv("./rxn.csv", header=None, names=['id', 'name'])
    
    # 构建字典（去除可能的空格）
    met_dict = dict(zip(met_df['id'].str.strip(), met_df['name'].str.strip()))
    rxn_dict = dict(zip(rxn_df['id'].str.strip(), rxn_df['name'].str.strip()))
     # 定义正则表达式匹配模式：s_xxxx[ce] 或 r_xxxx
    pattern = re.compile(r'(\b[sr]_\d+)(\[[a-z]+\])?\b')
    
    def replace_match(match):
        full_id = match.group(0)  # 完整匹配的ID（如 "s_0001[ce]"）
        base_id = match.group(1)  # 基础ID部分（如 "s_0001"）
        
        # 优先检查代谢物（s_前缀）
        if base_id.startswith('s_') and base_id in met_dict:
            return met_dict[base_id]
        # 检查反应（r_前缀）
        elif base_id.startswith('r_') and base_id in rxn_dict:
            return rxn_dict[base_id]
        # 未找到映射时返回原ID
        return full_id
    
    # 替换所有匹配的ID
    return pattern.sub(replace_match, summary)

def replace_r(summary):
    rxn_df = pd.read_csv("./rxn.csv", header=None, names=['id', 'name'])
    
    # 构建字典（去除可能的空格）
    rxn_dict = dict(zip(rxn_df['id'].str.strip(), rxn_df['name'].str.strip()))
     # 定义正则表达式匹配模式：s_xxxx[ce] 或 r_xxxx
    pattern = re.compile(r'(\b[sr]_\d+)(\[[a-z]+\])?\b')
    
    def replace_match(match):
        full_id = match.group(0)  # 完整匹配的ID（如 "s_0001[ce]"）
        base_id = match.group(1)  # 基础ID部分（如 "s_0001"）
        # 检查反应（r_前缀）
        if base_id.startswith('r_') and base_id in rxn_dict:
            return rxn_dict[base_id]
        # 未找到映射时返回原ID
        return full_id
    
    # 替换所有匹配的ID
    return pattern.sub(replace_match, summary)    


template_folder = path.abspath('./wiki')

app = Flask(__name__, template_folder=template_folder)
app.config['FREEZER_DESTINATION'] = 'public'
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_IGNORE_MIMETYPE_WARNINGS'] = True

@app.route('/model.json')
def serve_model():
    return send_from_directory('.', 'model.json')

@app.route('/')
def home():
    return render_template('pages/confirm.html')

@app.route('/model/<id>')
def set_model(id):
    model=cobra.io.read_sbml_model(str(Path('models')) + '/' + id + '.xml')
    display_reaction_info(model)
    @app.route('/objective/<reaction_id>')
    def set_objective(reaction_id):
        model.objective = model.reactions.get_by_id(reaction_id)
    @app.route('/reaction/<reaction_id>/<lower>/<upper>')
    def set_reaction(reaction_id, lower, upper):
        reaction = model.reactions.get_by_id(reaction_id)
        reaction.lower_bound = float(lower)
        reaction.upper_bound = float(upper)
    @app.route('/gene/<gene_id>')
    def knock_out_gene(gene_id):
        model.genes.get_by_id(gene_id).knock_out()
    @app.route('/optimize')
    def optimize():
        solution = model.optimize()
        print('Optimal flux:',solution.objective.value)
        print(model.objective.expression)
        print('Status: ',solution.status)
        print(replace_rs(model.summary()).tostring())

@app.route('/pages/<page>')
def pages(page):
    return render_template(str(Path('pages')) + '/' + page.lower() + '.html')

# Main Function, Runs at http://0.0.0.0:8080
if __name__ == "__main__":
    app.run(port=8080)

##############################################################################################

#直接运行 python app.py 会启动 Flask 开发服务器（动态模式，非静态站点）。
#主要用于调试，正式部署应使用 flask freeze 生成静态文件。

#flask run  # 动态调试

#flask freeze  # 生成静态文件到 ./public

#flask serve  # 启动本地静态服务器（默认 4000 端口）

#.gitlab-ci.yml 调用 flask freeze，自动上传 public/ 到 Pages。