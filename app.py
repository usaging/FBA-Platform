from flask import Flask, render_template, send_from_directory,request, jsonify
import cobra
from pathlib import Path
import io, sys
import json
from werkzeug.utils import secure_filename
import os

import tools

app = Flask(__name__, template_folder='wiki')

app.config['UPLOAD_FOLDER'] = 'models/'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
app.config['ALLOWED_EXTENSIONS'] = {'xml', 'sbml'}  # 按需修改


# 全局变量存储模型
model = None
model_id=None
confirm={
            "model": None,               # 存储模型名称（字符串）
            "objective": [],             # 存储目标函数（字符串）
            "deleted_genes": [],         # 存储待删除基因（列表，如 ["gene1", "gene2"]）
            "modified_reactions": [],     # 存储修改的反应（列表，元素为字典）
            "modified_objective":[]       # 存储修改的目标函数（字符串）
        }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({"message": "未选择文件"}), 400

    files = request.files.getlist('files')
    success_files = []
    new_records = []
    
    for file in files:
        if file.filename == '':
            continue
            
        # 仅检查文件后缀
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

        # 构建记录信息
        file_info=tools.process_file(save_path)

        new_records.append(file_info)
        success_files.append(filename)

    # 更新JSON记录文件
    if new_records:
        tools.update_file_records(new_records)


    if not success_files:
        return jsonify({"message": "没有符合要求的文件"}), 400

    return jsonify({
        "message": f"成功上传 {len(success_files)} 个文件",
        "files": success_files
    })      
@app.route('/fba-config.json')
def serve_fba_config():
    return send_from_directory('.', 'fba_config.json')

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
    return render_template('pages/index.html')

@app.route('/model')
def model_page():
    return render_template('pages/model.html')

@app.route('/objective')
def objective_page():
    return render_template('pages/objective.html')

@app.route('/wSetting')
def wSetting_page():
    return render_template('pages/wSetting.html')

@app.route('/constraints')
def constraints_page():
    return render_template('pages/constraints.html')

@app.route('/gene')
def gene_page():
    return render_template('pages/gene.html')


@app.route('/model/<id>')
def set_model(id):
    global model
    global model_id
    global confirm

    model_id=id
    confirm['model']=model_id
    model_path = Path('models') / f'{id}.xml'
    model = cobra.io.read_sbml_model(str(model_path))
    export_r_path='reactions/'+id+'.json'
    export_g_path='genes/'+id+'.json'
    tools.export_reactions_json(model,export_r_path )
    tools.export_genes_json(model,export_g_path )
    return f"Model {id} loaded successfully."

@app.route('/objective/<reaction_id>')
def set_objective(reaction_id):
    global confirm
    global model
    if model is None:
        return "No model loaded."
    
    # 添加判重逻辑
    if reaction_id not in confirm['objective']:
        confirm['objective'].append(reaction_id)
        return f"Reaction {reaction_id} added to objectives."
    else:
        return f"Reaction {reaction_id} already exists in objectives."

@app.route('/reaction/<reaction_id>/<lower>/<upper>')
def set_reaction(reaction_id, lower, upper):
    global confirm
    global model
    if model is None:
        return "No model loaded."
    # reaction = model.reactions.get_by_id(reaction_id)
    # reaction.lower_bound = float(lower)
    # reaction.upper_bound = float(upper)
    confirm['modified_reactions'].append({
        "reaction": reaction_id,
        "lower_bound": float(lower),
        "upper_bound": float(upper)
    })
    return f"Reaction {reaction_id} bounds set to [{lower}, {upper}]."

@app.route('/gene/<gene_id>')
def knock_out_gene(gene_id):
    global confirm
    global model
    if model is None:
        return "No model loaded."
    
    # 添加判重逻辑
    if gene_id not in confirm['deleted_genes']:
        confirm['deleted_genes'].append(gene_id)
        return f"Gene {gene_id} added to deleted_genes."
    else:
        return f"Gene {gene_id} already exists in deleted_genes."

@app.route('/config')
def set_config():
    global model
    global confirm
    if model is None:
        return "No model loaded."
    
    if confirm["deleted_genes"]:
        for gene_id in confirm["deleted_genes"]:
            if gene_id in model.genes:
                model.genes.get_by_id(gene_id).knock_out()
            else:
                print(f"警告: 基因 {gene_id} 不存在于模型中")

    if confirm['modified_objective']:
        combined_objective=cobra.Model().problem.Objective(0)  # 初始化为零表达式
        for reaction in confirm['modified_objective']:
            reaction_id = reaction['reaction']
            if reaction_id in model.reactions:
                rxn = model.reactions.get_by_id(reaction_id)
                combined_objective += rxn.flux_expression * reaction['weight']
            else:
                print(f"警告: 反应 {reaction_id} 不存在于模型中")
        model.objective = combined_objective
    else:
        model.objective = "Biomass"

    if confirm["modified_reactions"]:
        for reaction in confirm["modified_reactions"]:
            reaction_id = reaction["reaction"]
            lower_bound = reaction["lower_bound"]
            upper_bound = reaction["upper_bound"]
            if reaction_id in model.reactions:
                model.reactions.get_by_id(reaction_id).lower_bound = lower_bound
                model.reactions.get_by_id(reaction_id).upper_bound = upper_bound
            else:
                print(f"警告: reaction {reaction_id} 不存在于模型中")

@app.route('/confirm')
def set_confirm():
    with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)
    return render_template('pages/confirm.html')

@app.route('/clear-models', methods=['POST'])  # 明确指定允许 POST 方法
def clear_models():
    global model
    try:
        model = None
        # 如果还有其他需要清理的数据，可以在此操作
        return jsonify({"status": "success", "message": "模型数据已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear-constraints', methods=['POST'])  # 明确指定允许 POST 方法
def clear_constraints():
    global confirm
    try:
        confirm['modified_reactions'] = []
        # 如果还有其他需要清理的数据，可以在此操作
        return jsonify({"status": "success", "message": "操作函数已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear-objective', methods=['POST'])  # 明确指定允许 POST 方法
def clear_objective():
    global confirm
    try:
        confirm['objective'] = []
        # 如果还有其他需要清理的数据，可以在此操作
        return jsonify({"status": "success", "message": "目标函数已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/clear-genes', methods=['POST'])  # 明确指定允许 POST 方法
def clear_genes():
    global confirm
    try:
        confirm['deleted_genes'] = []
        # 如果还有其他需要清理的数据，可以在此操作
        return jsonify({"status": "success", "message": "待删除基因已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500             

@app.route('/clear-config', methods=['POST'])
def clear_confirm():
    global confirm
    try:
       confirm={
            "model": None,               # 存储模型名称（字符串）
            "objective": [],             # 存储目标函数（字符串）
            "deleted_genes": [],         # 存储待删除基因（列表，如 ["gene1", "gene2"]）
            "modified_reactions": []     # 存储修改的反应（列表，元素为字典）
        }
       with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)
        return jsonify({"status": "success", "message": "配置已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500      
       

# @app.route('/setobjective')
# def set_objective(reaction_list):
#     #传入一个reaction-weight的数组，设置objective
#     global model


@app.route('/result')
def optimize():
    global model
    if model is None:
        return "No model loaded."

    # 查看数据结构
    print(json.dumps(confirm, indent=2))
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
    print(summary_str)

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
