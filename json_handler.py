import json
import os
from pprint import pprint
from PIL import Image
from enum import Enum

CLEAN_JSON = False
LEVEL = 1
CREATE_DRAWINGS = True

# 控件对应的图像
im_button = Image.open('./drawings/button.png')
im_edit_text = Image.open('./drawings/edit_text.png')
im_image_view = Image.open('./drawings/image_view.png')
im_text_view = Image.open('./drawings/text_view.png')
im_image_button = Image.open('./drawings/image_button.png')
im_text_link = Image.open('./drawings/text_link.png')
im_checkbox = Image.open('./drawings/checkbox.png')


class Component(Enum):
    Button = 1
    EditText = 2
    ImageView = 3
    TextView = 4
    ImageButton = 5
    TextLink = 6
    CheckBox = 7
    Unclassified = 8


def json_handler(read_json_path, write_json_path):
    """
    读入json文件，输出清理后的简洁json文件
    :param read_json_path: 待处理json文件路径
    :param write_json_path: 处理后json文件路径
    :return:
    """
    with open(read_json_path, 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']
    root_children = root['children']

    # FIXME 检查Rico数据集中layout是否从root.children[0]开始
    top_layout = root_children[0]
    dfs_clean(top_layout)
    # pprint(top_layout)

    with open(write_json_path, 'w') as f:
        json.dump(top_layout, f, indent=2)


def sketch_generation(layout_json_path, output_img_path):
    """
    读入json文件，生成处理后的草图文件
    :param layout_json_path: 待处理json文件路径
    :param output_img_path: 输出的草图图片格式文件路径
    :return:
    """
    with open(layout_json_path, 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']
    root_children = root['children']
    img_bounds = root['bounds']

    # FIXME 检查Rico数据集中layout是否从root.children[0]开始
    top_layout = root_children[0]

    im = Image.new('RGB', (img_bounds[2], img_bounds[3]), (255, 255, 255))
    dfs_draw_component(top_layout, im)

    im.save(output_img_path, "JPEG")


def dfs_clean(json_obj):
    """
    通过深度优先搜索的方式清理冗余的json属性，保留
    :param json_obj:
    :return:
    """
    remove_unrelated_keys(json_obj)

    if 'children' not in json_obj:
        return
    else:
        for i in range(len(json_obj['children'])):
            dfs_clean(json_obj['children'][i])


def remove_unrelated_keys(json_node):
    """
    按LEVEL等级确定对于节点json_dict保留的json属性。
    :param json_node: 待处理的字典格式的json节点
    :return:
    """
    if LEVEL == 1:
        reserved_list = ['class', 'children', 'visibility']
    elif LEVEL == 2:
        reserved_list = ['class', 'children', 'visibility', 'bounds']
    else:
        reserved_list = ['class', 'children']

    key_list = [key for key in json_node.keys() if key not in reserved_list]
    for k in key_list:
        del json_node[k]


def dfs_draw_component(json_obj, im):
    """
    通过深度优先搜索的方式按节点绘制草图，将其直接绘制在im对象上
    :param json_obj: 待分析的json节点
    :param im: 待绘制的图片对象
    :return:
    """
    # 不绘制属性visible-to-user值为真的控件
    if not json_obj['visible-to-user']:
        return

    # TODO 修改或加入更多规则判断并调用 im.paste 绘制相应的图形；修改或增加参数来确定额外属性，如上层传递的 clickable 属性

    component_type = infer_component_type(json_obj, False)

    # 经过规则推断仍无法判断控件类型的，不绘制
    if component_type is not Component.Unclassified:
        draw_component(im, component_type, json_obj['bounds'])

    # 当json_obj无children属性时，不再递归执行
    if 'children' in json_obj:
        for i in range(len(json_obj['children'])):
            dfs_draw_component(json_obj['children'][i], im)


def infer_component_type(json_node, clickable):
    """
    接收json节点，返回根据规则推断的控件类型
    :param json_node: 待分析json节点
    :param clickable: 其他属性
    :return: 推断的控件类型结果
    """
    # TODO 在这个函数内部编写规则，返回相应的推断类型；

    # 先判断class_name是否存在明确的控件类型标识
    component_type = infer_component_from_string(json_node['class'])
    if component_type is not Component.Unclassified:
        return component_type

    # 再遍历地判断当前节点的所有祖先是否存在明确标识
    for ancestor in json_node['ancestors']:
        component_type = infer_component_from_string(ancestor)
        if component_type is not Component.Unclassified:
            break
    if component_type is not Component.Unclassified:
        return component_type

    # TODO 还要结合clickable等其他属性判断结果
    return component_type


def infer_component_from_string(str):
    """
    当控件类型名称明确地出现在str中时，返回对应的控件类型；如果均未出现，返回Component.Unclassified
    :param str: 待匹配字符串
    :return: 控件类型
    """
    # TODO 注意这里的判断顺序对结果有影响
    if "CheckBox" in str:
        return Component.CheckBox
    if "EditText" in str:
        return Component.EditText
    if "Button" in str:
        return Component.Button
    if "TextView" in str:
        return Component.TextView
    if "Image" in str:
        return Component.ImageView

    return Component.Unclassified


def draw_component(im, component_type, bounds):
    """
    在im对象中绘制范围为bounds的控件草图
    :param im: 待绘制的图片对象
    :param component_type: 待绘制的控件类型
    :param bounds: 待绘制的控件范围
    :return:
    """
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    # 不绘制面积为0的控件
    if w <= 0 or h <= 0:
        return

    if component_type is Component.Button:
        im.paste(im_button.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.ImageView:
        im.paste(im_image_view.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.EditText:
        im.paste(im_edit_text.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.TextView:
        im.paste(im_text_view.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.CheckBox:
        im.paste(im_checkbox.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.ImageButton:
        im.paste(im_image_button.resize((w, h)), box=(bounds[0], bounds[1]))
    elif component_type is Component.TextLink:
        im.paste(im_text_link.resize((w, h)), box=(bounds[0], bounds[1]))


if __name__ == '__main__':
    main_path = "./Top Apps"
    output_path = "./output"

    if CLEAN_JSON:
        print("Start cleaning json files ...")
        for case_dir in os.listdir(main_path):
            if not case_dir.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(main_path, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        json_handler(os.path.join(main_path, case_dir, file),
                                     os.path.join(output_path, case_dir, file_name + "." + str(LEVEL) + ".json"))
                print(os.path.join(output_path, case_dir))
        print("Output cleaned json files saved in " + output_path)

    output_path = "./Top Apps"
    # turn screenshots to sketches
    if CREATE_DRAWINGS:
        print("Start generating sketches ...")
        for case_dir in os.listdir(main_path):
            if not case_dir.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(main_path, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        sketch_generation(os.path.join(main_path, case_dir, file),
                                          os.path.join(output_path, case_dir, file_name + '-sketch.jpg'))
                print(os.path.join(output_path, case_dir))
        print("Output drawings saved in " + output_path)