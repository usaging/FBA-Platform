from flask import Flask, send_from_directory, render_template, jsonify, abort
from pathlib import Path
import cobra
from os import path
import os
from pathlib import Path
import cobra
import pandas as pd
import re
from flask import send_from_directory
from flask import Flask, render_template

app = Flask(__name__)

# 全局模型变量
current_model = None


def display_reaction_info(model):
    """
    显示模型中所有反应的信息

    参数:
        model_path: 模型文件路径
        rxn_csv_path: 包含反应ID到名称映射的CSV文件路径
    """
    # 1. 加载模型
    rxn_csv_path = "./rxn.csv"

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
    print("=" * 110)

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
    """
    提供前端下载 model.json（如果存在）。
    """
    model_path = Path('.') / 'model.json'
    if model_path.exists():
        return send_from_directory('.', 'model.json')
    else:
        abort(404, description="model.json not found")

@app.route('/')
def home():
    """
    首页，渲染确认页面。
    """
    return render_template('pages/confirm.html')

@app.route('/model/<model_id>', methods=['GET'])
def set_model(model_id):
    """
    加载指定 ID 的 SBML 模型并打印反应信息。
    """
    global current_model
    sbml_file = Path('models') / f'{model_id}.xml'
    if not sbml_file.exists():
        return jsonify({'error': '模型文件不存在'}), 404

    # 读取模型
    current_model = cobra.io.read_sbml_model(str(sbml_file))
    # 打印反应信息到服务器日志（或根据需求返回给前端）
    display_reaction_info(current_model)
    return jsonify({'status': 'model loaded', 'model_id': model_id})

@app.route('/objective/<reaction_id>', methods=['POST'])
def set_objective(reaction_id):
    """
    设置模型的目标反应 (objective)。
    """
    if current_model is None:
        return jsonify({'error': '尚未加载模型'}), 400

    try:
        current_model.objective = current_model.reactions.get_by_id(reaction_id)
    except KeyError:
        return jsonify({'error': '反应 ID 无效'}), 404

    return jsonify({'status': 'objective set', 'objective': reaction_id})

@app.route('/reaction/<reaction_id>/<float:lower>/<float:upper>', methods=['POST'])
def set_reaction_bounds(reaction_id, lower, upper):
    """
    设置某一反应的上下限。
    """
    if current_model is None:
        return jsonify({'error': '尚未加载模型'}), 400

    try:
        rxn = current_model.reactions.get_by_id(reaction_id)
        rxn.lower_bound = lower
        rxn.upper_bound = upper
    except KeyError:
        return jsonify({'error': '反应 ID 无效'}), 404

    return jsonify({
        'status': 'bounds updated',
        'reaction': reaction_id,
        'lower': lower,
        'upper': upper
    })

@app.route('/gene/<gene_id>', methods=['POST'])
def knock_out_gene(gene_id):
    """
    基因敲除。
    """
    if current_model is None:
        return jsonify({'error': '尚未加载模型'}), 400

    try:
        gene = current_model.genes.get_by_id(gene_id)
        gene.knock_out()
    except KeyError:
        return jsonify({'error': '基因 ID 无效'}), 404

    return jsonify({'status': 'gene knocked out', 'gene': gene_id})

@app.route('/optimize', methods=['GET'])
def optimize():
    """
    优化模型并打印结果。
    """
    if current_model is None:
        return jsonify({'error': '尚未加载模型'}), 400

    sol = current_model.optimize()
    summary_str = replace_rs(current_model.summary()).tostring()

    return jsonify({
        'objective_value': sol.objective.value,
        'status': sol.status,
        'objective_expression': str(current_model.objective.expression),
        'summary': summary_str
    })

@app.route('/pages/<page>')
def pages(page):
    """
    渲染 pages 目录下的静态 HTML 页面。
    """
    template_path = Path('pages') / f'{page.lower()}.html'
    if template_path.exists():
        # render_template 会自动寻找 templates/ 目录下的文件，
        # 如果你的 pages 在 templates/pages 下，则直接写 'pages/<page>.html'
        return render_template(f'pages/{page.lower()}.html')
    else:
        abort(404, description="Page not found")

if __name__ == "__main__":
    # debug=True 方便开发调试，生产环境请关闭
    app.run(host='0.0.0.0', port=8080, debug=True)
