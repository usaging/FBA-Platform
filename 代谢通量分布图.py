import cobra
import pandas as pd
import json
import re
from escher import Builder
import matplotlib.pyplot as plt
import pickle

rxn_csv='./new_model/data/rxn.csv'
met_csv='./new_model/data/met.csv'

#csv读取
df_rxn = pd.read_csv(rxn_csv,header=None)
df_met = pd.read_csv(met_csv,header=None)
df_all=pd.concat([df_met,df_rxn])
id_col = df_all.columns[0]
name_col = df_all.columns[1]

def replace_rs(text):
    '''把r_xxxx 或 s_xxxx匹配成对于的 反应 和 代谢物 名字'''

    def replacer(match):
        rs_id = match.group(1)  # 获取匹配的 r_xxxx 或 s_xxxx
        # 在 df_all 中查找该 ID，并返回对应的名称
        matched_row = df_all[df_all[id_col].str[:6] == rs_id]
        if not matched_row.empty:
            return matched_row.iloc[0][name_col] # 返回名称
        else:
            return rs_id + '\t\t'  # 如果没找到，保留原字符串

    pattern = re.compile(r'\b([rs]_\d{4})\b')  # 匹配 r_xxxx 或 s_xxxx 格式
    replaced_text = pattern.sub(replacer, str(text))
    return replaced_text
#检查模型
print('参数加载完毕\n')

#反应参数说明
'''
摄取反应
葡萄糖：r_1714
半乳糖：r_1710
生物量:r_4041
'''
glucose_objective=[]
mix_objective=[]
model1 = cobra.io.read_sbml_model("new_model/yeast-GEM-new.xml")

#氧气输入
oxygen_exchange_rxn_id='r_1992'
oxygen_exchange_rxn = model1.reactions.get_by_id(oxygen_exchange_rxn_id)
oxygen_exchange_rxn.bounds=(-1000,0)

#葡萄糖输入
glucose_exchange_rxn_id='r_1714'
glucose_exchange_rxn = model1.reactions.get_by_id(glucose_exchange_rxn_id)
glucose_exchange_rxn.bounds=(-1,0)

# 人参皂苷合成
rh1_synthesis_rxn_id='r_5014'#人参皂苷合成
rh1_synthesis_rxn = model1.reactions.get_by_id(rh1_synthesis_rxn_id)
rh1_synthesis_rxn.bounds=(0,1000)

#半乳糖输入
galactose_exchange_rxn_id='r_1710'
galactose_exchange_rxn = model1.reactions.get_by_id(galactose_exchange_rxn_id)
galactose_exchange_rxn.bounds=(0,0)

#AHG输入
AHG_rxn_id='r_5015'#AHG交换
AHG_rxn = model1.reactions.get_by_id(AHG_rxn_id)
AHG_rxn.bounds=(0,0)

biomass_rxn_id = 'r_2111'  # 生物量r_2111/r_4041/r_4048
biomass_rxn = model1.reactions.get_by_id(biomass_rxn_id)
biomass_rxn.bounds = (0, 1000)

model1.objective = rh1_synthesis_rxn.flux_expression*0.45+biomass_rxn.flux_expression*0.55
model1.solver.objective_direction = 'max'
solution = model1.optimize()

non_zero_fluxes1 = solution.fluxes[solution.fluxes.abs() > 1e-6]
flux_dict1 = non_zero_fluxes1.to_dict()

#氧气输入
oxygen_exchange_rxn_id='r_1992'
oxygen_exchange_rxn = model1.reactions.get_by_id(oxygen_exchange_rxn_id)
oxygen_exchange_rxn.bounds=(-1000,0)

#葡萄糖输入
glucose_exchange_rxn_id='r_1714'
glucose_exchange_rxn = model1.reactions.get_by_id(glucose_exchange_rxn_id)
glucose_exchange_rxn.bounds=(0,0)

# 人参皂苷合成
rh1_synthesis_rxn_id='r_5014'#人参皂苷合成
rh1_synthesis_rxn = model1.reactions.get_by_id(rh1_synthesis_rxn_id)
rh1_synthesis_rxn.bounds=(0,1000)

#半乳糖输入
galactose_exchange_rxn_id='r_1710'
galactose_exchange_rxn = model1.reactions.get_by_id(galactose_exchange_rxn_id)
galactose_exchange_rxn.bounds=(-0.5,0)

#AHG输入
AHG_rxn_id='r_5015'#AHG交换
AHG_rxn = model1.reactions.get_by_id(AHG_rxn_id)
AHG_rxn.bounds=(-0.5,0)

model1.objective = rh1_synthesis_rxn.flux_expression*0.45+biomass_rxn.flux_expression*0.55
model1.solver.objective_direction = 'max'
solution = model1.optimize()

non_zero_fluxes2 = solution.fluxes[solution.fluxes.abs() > 1e-6]
flux_dict2 = non_zero_fluxes2.to_dict()


flux_comparison = {}

for rxn in set(flux_dict1) | set(flux_dict2):
    flux_comparison[replace_rs(rxn)] = {
        'glucose': flux_dict1.get(rxn, 0),
        'galactose_AHG': flux_dict2.get(rxn, 0)
    }
# 保存为 JSON
with open('flux_comparison.json', 'w') as f:
    json.dump(flux_comparison, f, indent=2)

# # 导出代谢物信息为JSON文件（中文）
# metabolite_data = {}

# # 遍历模型中的所有代谢物
# for met in model1.metabolites:
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
