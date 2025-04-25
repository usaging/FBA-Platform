from flask import Flask, render_template, send_from_directory
import cobra
from pathlib import Path
import pandas as pd
import re

app = Flask(__name__, template_folder='wiki')

# 全局变量存储模型
model = None

def display_reaction_info(model):
    rxn_csv_path = "./rxn.csv"
    try:
        rxn_df = pd.read_csv(rxn_csv_path, header=None, names=['reaction_id', 'name'])
        id_to_name = dict(zip(rxn_df['reaction_id'], rxn_df['name']))
    except FileNotFoundError:
        print(f"警告: 未找到反应名称映射文件 {rxn_csv_path}, 将使用反应ID作为名称")
        id_to_name = {}
    
    print("{:<15} {:<50} {:<15} {:<15} {:<15}".format(
        "ID", "Name", "Reaction", "Lower bound", "Upper bound"))
    print("="*110)
    
    for reaction in model.reactions:
        name = id_to_name.get(reaction.id, reaction.id)
        reaction_eq = reaction.build_reaction_string()
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

@app.route('/')
def home():
    return render_template('pages/confirm.html')

@app.route('/model/<id>')
def set_model(id):
    global model
    model_path = Path('models') / f'{id}.xml'
    model = cobra.io.read_sbml_model(str(model_path))
    display_reaction_info(model)
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
    print('Optimal flux:', solution.objective_value)
    print(model.objective.expression)
    print('Status:', solution.status)
    summary_str = str(model.summary())
    replaced_summary = replace_rs(summary_str)
    return f"Optimization complete. Objective value: {solution.objective_value}"

@app.route('/pages/<page>')
def pages(page):
    return render_template(f'pages/{page.lower()}.html')

if __name__ == "__main__":
    app.run(port=8080)
