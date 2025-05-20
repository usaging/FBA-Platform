from flask import Flask, render_template, send_from_directory,request, jsonify
import cobra
from pathlib import Path
import io, sys
import json
from werkzeug.utils import secure_filename
import os
# from escher import Builder


# import pandas as pd
# import re
# import matplotlib.pyplot as plt
# import pickle

import tools

# rxn_csv='./new_model/data/rxn.csv'
# met_csv='./new_model/data/met.csv'

# #csv读取
# df_rxn = pd.read_csv(rxn_csv,header=None)
# df_met = pd.read_csv(met_csv,header=None)
# df_all=pd.concat([df_met,df_rxn])
# id_col = df_all.columns[0]
# name_col = df_all.columns[1]

# def replace_rs(text):
#     '''把r_xxxx 或 s_xxxx匹配成对于的 反应 和 代谢物 名字'''

#     def replacer(match):
#         rs_id = match.group(1)  # 获取匹配的 r_xxxx 或 s_xxxx
#         # 在 df_all 中查找该 ID，并返回对应的名称
#         matched_row = df_all[df_all[id_col].str[:6] == rs_id]
#         if not matched_row.empty:
#             return matched_row.iloc[0][name_col] # 返回名称
#         else:
#             return rs_id + '\t\t'  # 如果没找到，保留原字符串

#     pattern = re.compile(r'\b([rs]_\d{4})\b')  # 匹配 r_xxxx 或 s_xxxx 格式
#     replaced_text = pattern.sub(replacer, str(text))
#     return replaced_text
# #检查模型
# print('参数加载完毕\n')


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
            "weights":[]       # 存储修改的目标函数（字符串）
        }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# @app.route('/refresh', methods=['POST'])
# def refresh_model():
#     tools.scan_directory_and_generate_json('models', 'model.json')
#     return jsonify({"message": "刷新成功"}), 400

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
        file_info=tools.process_file(save_path,False)


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
    if model_id is None:
        return "No model loaded."
    r_path=model_id+'.json'
    return send_from_directory('reactions', r_path)

@app.route('/gene.json')
def serve_gene():
    if model_id is None:
        return "No model loaded."
    g_path=model_id+'.json'
    return send_from_directory('genes', g_path)

@app.route('/')
def home():
    global confirm
    confirm={
            "model": None,               # 存储模型名称（字符串）
            "objective": [],             # 存储目标函数（字符串）
            "deleted_genes": [],         # 存储待删除基因（列表，如 ["gene1", "gene2"]）
            "modified_reactions": [],     # 存储修改的反应（列表，元素为字典）
             "weights":[]
        }
    with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)
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
    export_r_path='reactions/'+id+'.json'
    export_g_path='genes/'+id+'.json'
    if not os.path.exists(export_r_path):
        tools.export_reactions_json(model,export_r_path )
    if not os.path.exists(export_r_path):
        tools.export_genes_json(model,export_g_path )
    confirm={
            "model": model_id,               # 存储模型名称（字符串）
            "objective": [],             # 存储目标函数（字符串）
            "deleted_genes": [],         # 存储待删除基因（列表，如 ["gene1", "gene2"]）
            "modified_reactions": [],     # 存储修改的反应（列表，元素为字典）
            "weights":[]
        }
    with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)

    return f"Model {id} loaded successfully."

@app.route('/objective/<reaction_id>')
def set_objective(reaction_id):
    global confirm
    global model
    if model_id is None:
        return "No model loaded."
    
    # 添加判重逻辑
    if reaction_id not in confirm['objective']:
        confirm['objective'].append(reaction_id)
        return f"Reaction {reaction_id} added to objectives."
    else:
        return f"Reaction {reaction_id} already exists in objectives."
    
@app.route('/weight/<reaction_id>/<weight>')
def set_weight(reaction_id,weight):
    global confirm
    global model
    if model_id is None:
        return "No model loaded."
    
    existing_reactions = {item["reaction"] for item in confirm['weights']}
    if reaction_id not in existing_reactions:
        confirm['weights'].append({
            "reaction": reaction_id,
            "weight": weight
    })
    return f"Reaction {reaction_id} weight added to objectives."
    # else:
    #     return f"Reaction {reaction_id} already exists in objectives."

@app.route('/reaction/<reaction_id>/<lower>/<upper>')
def set_reaction(reaction_id, lower, upper):
    global confirm
    global model
    if model_id is None:
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
    if model_id is None:
        return "No model loaded."
    
    # 添加判重逻辑
    if gene_id not in confirm['deleted_genes']:
        confirm['deleted_genes'].append(gene_id)
        return f"Gene {gene_id} added to deleted_genes."
    else:
        return f"Gene {gene_id} already exists in deleted_genes."

def apply_knockouts(model, genes):
    for gid in genes:
        if gid in model.genes:
            model.genes.get_by_id(gid).knock_out()
        else:
            print(f"警告: 基因 {gid} 不存在于模型中")


def set_objective(model, obj_list=None, weights=None):
    # 优先使用加权目标
    if weights:
        expr = 0
        for w in weights:
            rid = w['reaction']
            try:
                weight = float(w['weight'])/100
            except ValueError:
                print(f"错误: 权重 '{w['weight']}' 无法转换为浮点数")
                continue
            if rid in model.reactions:
                rxn = model.reactions.get_by_id(rid)
                expr += rxn.flux_expression * weight
            else:
                print(f"警告: 反应 {rid} 不存在于模型中")
        model.objective = model.problem.Objective(expr, direction='max')
    # 其次使用单纯目标列表
    elif obj_list:
        obj_dict = {}
        for rid in obj_list:
            if rid in model.reactions:
                obj_dict[rid] = 1.0
            else:
                print(f"警告: 反应 {rid} 不存在于模型中")
        model.objective = obj_dict
    else:
        model.objective = 'Biomass'


def modify_bounds(model, mods):
    for m in mods:
        rid = m['reaction']
        lb, ub = m['lower_bound'], m['upper_bound']
        if rid in model.reactions:
            rxn = model.reactions.get_by_id(rid)
            rxn.lower_bound = lb
            rxn.upper_bound = ub
        else:
            print(f"警告: 反应 {rid} 不存在于模型中")


@app.route('/config',methods=['POST'])
def set_config():
    global model
    global confirm
    if model_id is None:
        return "No model loaded."
    model_path = Path('models') / f'{id}.xml'
    model = cobra.io.read_sbml_model(str(model_path))
    
  # 应用基因敲除
    apply_knockouts(model, confirm.get('deleted_genes', []))
    # 设置目标函数
    set_objective(model,
                  obj_list=confirm.get('objective'),
                  weights=confirm.get('weights'))
    # 修改反应通量界限
    modify_bounds(model, confirm.get('modified_reactions', []))

    
#######################################################################
        # 打印配置
    print(json.dumps(confirm, indent=2, ensure_ascii=False))

    # 运行优化
    solution = model.optimize()

    # 输出结果
    print(f"Optimal flux: {solution.objective_value}")
    print(f"Status: {solution.status}")
    # 仅在可行或最优时打印 summary
    if solution.status == 'optimal' or solution.status == 'feasible':
        try:
            summary = model.summary()
            print(str(summary))
        except Exception as e:
            print(f"生成 summary 时出错: {e}")
    else:
        print("模型不可行，无法生成 summary。")

#########################################################################  

    #     # 导出代谢物信息为JSON文件（中文）
    # metabolite_data = {}

    # # 遍历模型中的所有代谢物
    # for met in model.metabolites:
    #     # 获取代谢物ID和名称
    #     met_id = met.id
    #     met_name = replace_rs(met.name)  # 使用您现有的函数转换名称

    #     # 获取代谢物其他信息
    #     metabolite_data[met_name] = {
    #         "name": met_name,
    #         "formula": met.formula,
    #         "charge": met.charge,
    #         "compartments": met.compartment,
    #     }

    # # 保存为中文文件名的JSON文件
    # output_filename = "metablites.json"  # 中文文件名

    # with open(output_filename, 'w', encoding='utf-8') as f:
    #     json.dump(metabolite_data, f, ensure_ascii=False, indent=2)

    # print(f"模型代谢物信息已保存到 {output_filename}")


    # # 读取模型
    # model = cobra.io.read_sbml_model("new_model/yeast-GEM-new.xml")

    # # 读取 flux_comparison.json
    # with open('flux_comparison.json', encoding='utf-8') as f:
    #     raw_flux = json.load(f)
    # with open('metabolites.json', encoding='utf-8') as f:
    #     met = json.load(f)
    # # 选择要显示的模式，例如 'glucose'
    # selected_mode ='galactose_AHG' #'glucose'

    # # 提取平面通量字典（reaction_id: flux_value）
    # flat_flux_data = {
    #     rxn_id: mode_flux[selected_mode]
    #     for rxn_id, mode_flux in raw_flux.items()
    #     if selected_mode in mode_flux
    # }

    # # 构建 Escher builder
    # builder = Builder(
    #     model=model,
    #     map_json='iMM904.Central carbon metabolism.json'
    # )

    # # 设置通量数据
    # builder.reaction_data = flat_flux_data
    # builder.metabolite_data=met
    # # 保存 HTML 显示通量
    # builder.save_html(f'flux_map_{selected_mode}.html')
    # print(f"完成：已保存 {selected_mode} 通量地图")

###################################################################################


    return jsonify({"status": "success", "message": "配置已提交"})
    

@app.route('/confirm')
def set_confirm():
    with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)
    return render_template('pages/confirm.html')

# @app.route('/clear-models', methods=['POST'])  # 明确指定允许 POST 方法
# def clear_models():
#     global model
#     try:
#         model = None
#         # 如果还有其他需要清理的数据，可以在此操作
#         return jsonify({"status": "success", "message": "模型数据已清空"})
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500

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
            "modified_reactions": [],     # 存储修改的反应（列表，元素为字典）
            "weights":[]
        }
       with open("fba_config.json", "w") as f:
        json.dump(confirm, f, indent=2)
        return jsonify({"status": "success", "message": "配置已清空"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500      
       

@app.route('/result')
def result():
    return render_template('./flux_map_galactose_AHG.html')
# def optimize():
#     global model
#     if model is None:
#         return "No model loaded."

#     # 查看数据结构
#     print(json.dumps(confirm, indent=2))
#     solution = model.optimize()
#  # 1. 创建 StringIO 并替换 stdout
#     buf = io.StringIO()
#     old_stdout = sys.stdout
#     sys.stdout = buf
#     print()
#     # 2. 执行原本会打印的逻辑
#     print('Optimal flux:', solution.objective_value)
#     print(model.objective.expression)
#     print('Status:', solution.status)
#     summary_str = str(model.summary())
#     print(summary_str)

#     # 3. 恢复 stdout，并获取输出内容
#     sys.stdout = old_stdout
#     output = buf.getvalue()
#     buf.close()

#     # 4. 渲染到模板
#     return render_template('pages/result.html', result=output)

@app.route('/pages/<page>')
def pages(page):
    return render_template(f'pages/{page.lower()}.html')

if __name__ == "__main__":
    #tools.scan_directory_and_generate_json("models","./model.json")
    app.run(port=8080)
