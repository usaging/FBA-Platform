import cobra
import json
from escher import Builder

# 读取模型
model = cobra.io.read_sbml_model("new_model/yeast-GEM-new.xml")

# 读取 flux_comparison.json
with open('flux_comparison.json', encoding='utf-8') as f:
    raw_flux = json.load(f)
with open('metabolites.json', encoding='utf-8') as f:
    met = json.load(f)
# 选择要显示的模式，例如 'glucose'
selected_mode ='galactose_AHG' #'glucose'

# 提取平面通量字典（reaction_id: flux_value）
flat_flux_data = {
    rxn_id: mode_flux[selected_mode]
    for rxn_id, mode_flux in raw_flux.items()
    if selected_mode in mode_flux
}

# 构建 Escher builder
builder = Builder(
    model=model,
    map_json='iMM904.Central carbon metabolism.json'
)

# 设置通量数据
builder.reaction_data = flat_flux_data
builder.metabolite_data=met
# 保存 HTML 显示通量
builder.save_html(f'flux_map_{selected_mode}.html')
print(f"完成：已保存 {selected_mode} 通量地图")
