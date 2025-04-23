from os import path
from pathlib import Path
import cobra
import pandas as pd
import re

from flask import Flask, render_template
from flask_frozen import Freezer

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

template_folder = path.abspath('./wiki')

app = Flask(__name__, template_folder=template_folder)
app.config['FREEZER_DESTINATION'] = 'public'
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_IGNORE_MIMETYPE_WARNINGS'] = True
freezer = Freezer(app)

@app.cli.command()
def freeze():
    freezer.freeze()

@app.cli.command()
def serve():
    freezer.run()

@app.route('/')
def home():
    return render_template('pages/confirm.html')


@app.route('/model/<id>')
def set_model(id):
    model=cobra.io.read_sbml_model(str(Path('models')) + '/' + id + '.xml')
    
    @app.route('/objective/<reaction_id>')
    def set_objective(reaction_id):
        model.objective = model.reactions.get_by_id(reaction_id)
    @app.route('/reaction/<reaction_id>/<lower>/<upper>')
    def set_reaction(reaction_id, lower, upper):
        reaction=model.reactions.get_by_id(reaction_id)
        reaction.lower_bound = float(lower)
        reaction.upper_bound = float(upper)
    @app.route('/gene/<gene_id>')
    def knock_out_gene(gene_id):
        model.genes.get_by_id(gene_id).knock_out()
    @app.route('/optimize')
    def optimize():
        solution=model.optimize()
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