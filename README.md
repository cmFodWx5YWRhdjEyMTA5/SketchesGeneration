# SketchesGeneration

## 运行步骤

基于 RICO 原始数据集构造 NMT 训练样本分为几个步骤：

1. 先调整好 `config.ini` 中的路径。

    项目中主要的文件、目录路径都定义在 `config.ini` 文件中。

2. `utils/files.py`

    调整参数 `MODE = divide_rico`。运行脚本，RICO 原始数据集中的文件（0.jpg/0.json/.../72219.jpg/72219.json）将被拆分为 0-999/1000-1999/.../72200-72219 这些子文件夹，保存到 `files/rico-output/rico-data` 中。
    
3. `rico/json_cleaner.py`

    RICO 文件夹 json 文件内容很多。这一步将分别读取上述拆分后的若干子文件夹，将其中的 json 文件中的必要信息提取出来。输出到 `files/rico-output/cleaned-json` 目录中。
    
4. `rico/generator.py`

    这一步骤比较复杂，读取简化后的 json 文件，将其转换为用于 NMT 模型训练用的组件块着色图（以及必要的 NMT 训练支持文件），输出后的文件保存在 `files/rico-output/sketches` 中和 `files/rico-output/data` 中。`files/rico-output/data` 也是最终 NMT 模型训练相关文件的根目录。
    
5. `rico/nmt_file_maker.py`

    生成剩下的 NMT 模型训练相关文件（保存在 `files/rico-output/data` 中）。
    
6. `utils/files.py`

    调整参数 `MODE = divide_rico`。第 4 步生成的 NMT 训练用组件块着色图是分开在子文件夹中的。这一步将其合并到 `files/rico-output/data/processedImage` 中。
    此时，`files/rico-output/data` 已经包含了 NMT 训练所用的所有数据。