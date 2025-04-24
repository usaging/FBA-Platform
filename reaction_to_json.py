import cobra
import pandas as pd

def display_reaction_info(model_path, rxn_csv_path):
    """
    显示模型中所有反应的信息
    
    参数:
        model_path: 模型文件路径
        rxn_csv_path: 包含反应ID到名称映射的CSV文件路径
    """
    # 1. 加载模型
    model = cobra.io.read_sbml_model(model_path)
    
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

# 使用示例
if __name__ == "__main__":
    model_path = "path/to/your/model.xml"  # 替换为你的模型文件路径
    rxn_csv_path = "rxn.csv"  # 替换为你的反应名称映射文件路径
    display_reaction_info(model_path, rxn_csv_path)