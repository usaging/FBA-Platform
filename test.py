import cobra
import json

# 读取模型
model = cobra.io.read_sbml_model("./models/iYO844.xml")

# 示例配置，后续可改为从文件或命令行读取
confirm = {
    "model": "iYO844",
    "objective": [
        "EX_drib_e",
        "EX_5mtr_e"
    ],
    "deleted_genes": [
        "BSU16730",
        "BSU16740"
    ],
    "modified_reactions": [
        {"reaction": "ADEt2", "lower_bound": 10.0, "upper_bound": 999999.0},
        {"reaction": "EX_etha_e", "lower_bound": 0.0, "upper_bound": 999999.0}
    ],
    "weights": [
        {"reaction": "EX_drib_e", "weight": "25"},
        {"reaction": "EX_5mtr_e", "weight": "75"}
    ]
}



def main():


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

if __name__ == '__main__':
    main()
