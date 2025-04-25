# X-Plane-CSL-to-GLB-Model-Converter
X-Plane CSL to GLB Model Converter

# 工具脚本说明

## glb_convert

功能：将3D模型文件转换为GLB格式

详细功能：
- 支持合并多个OBJ文件为一个GLB模型
- 自动处理纹理映射和UV坐标
- 支持顶点、面片和纹理数据的标准化处理
- 生成符合glTF 2.0标准的GLB文件

依赖项：
- Python 3.x
- trimesh库
- Pillow库

使用方法：
```bash
python main.py
```

## obj_convert

功能：处理OBJ格式的3D模型文件，支持纹理转换和格式标准化

详细功能：
- 解析X-Plane格式的OBJ文件并转换为标准OBJ格式
- 自动提取和处理纹理文件
- 支持航空公司涂装(livery)映射
- 生成包含纹理的GLB模型文件
- 输出航空公司与模型映射关系(airline_mapping.json)

依赖项：
- Python 3.x
- trimesh库
- Pillow库

使用方法：
```bash
python main.py [输入文件] [纹理目录] [输出路径]
```

注意：两个工具都需要安装依赖库，可通过以下命令安装：
```bash
pip install trimesh pillow
```
