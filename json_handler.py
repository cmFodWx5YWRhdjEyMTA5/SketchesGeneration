import json
import os
from pprint import pprint
from PIL import Image
from enum import Enum

CLEAN_JSON = False
LEVEL = 1
CREATE_SKETCHES = True

WIDTH = 1440
HEIGHT = 2560

KEY_PARENT_CLICKABLE = 'key_parent_clickable'

# 控件对应的图像
im_button = Image.open('./drawings/button.png')
im_edit_text = Image.open('./drawings/edit_text.png')
im_image_view = Image.open('./drawings/image_view.png')
im_text_view = Image.open('./drawings/text_view.png')
im_image_button = Image.open('./drawings/image_button.png')
im_text_link = Image.open('./drawings/text_link.png')
im_checkbox = Image.open('./drawings/checkbox.png')


class Widget(Enum):
    Layout = 0
    Button = 1
    EditText = 2
    ImageView = 3
    TextView = 4
    ImageLink = 5
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
    读入布局文件，生成处理后的草图文件并保存到指定路径中
    :param layout_json_path: 待处理json格式布局文件的路径
    :param output_img_path: 生成的草图图片的保存路径
    :return:
    """
    with open(layout_json_path, 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']
    root_children = root['children']
    img_bounds = root['bounds']

    # FIXME 检查Rico数据集中layout是否从root.children[0]开始
    top_layout = root_children[0]

    im = Image.new('RGB', (WIDTH, HEIGHT), (255, 255, 255))
    args = {KEY_PARENT_CLICKABLE: False}
    dfs_draw_widget(top_layout, im, args)

    im.save(output_img_path, "PNG")


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


def dfs_draw_widget(json_obj, im, args):
    """
    通过深度优先搜索的方式按节点绘制草图，将其直接绘制在im对象上
    :param json_obj: 待分析的json节点
    :param im: 待绘制的图片对象
    :param args: 其他需要逐层传递的参数
    :return:
    """
    # 不绘制属性visible-to-user值为真的控件
    if not json_obj['visible-to-user']:
        return

    # TODO 修改或加入更多规则判断并调用 im.paste 绘制相应的图形；修改或增加参数来确定额外属性，如上层传递的 clickable 属性

    widget_type = infer_widget_type(json_obj, args)

    # 如果外层layout的clickable属性为真，则传递该参数用于后续类型判断
    if widget_type == Widget.Layout and json_obj['clickable']:
        args[KEY_PARENT_CLICKABLE] = True

    # 经过规则推断仍无法判断控件类型的，不绘制
    if widget_type != Widget.Unclassified and widget_type != Widget.Layout:
        draw_widget(im, widget_type, json_obj['bounds'])


    # 当json_obj无children属性时，不再递归执行
    # TODO 是否还有其他不再需要递归访问的情形
    if 'children' in json_obj and (widget_type == Widget.Unclassified or widget_type == Widget.Layout):
        for i in range(len(json_obj['children'])):
            dfs_draw_widget(json_obj['children'][i], im, args)
    args[KEY_PARENT_CLICKABLE] = False


def infer_widget_type(json_node, args):
    """
    接收json节点，返回根据规则推断的控件类型
    :param json_node: 待分析json节点
    :param args: 其他属性
    :return: 推断的控件类型结果
    """
    # TODO 在这个函数内编写规则，返回相应的推断类型；注意规则放置的先后顺序对结果有影响。
    # 次序1：判断class_name是否存在明确的控件类型标识
    widget_type = infer_widget_from_string(json_node['class'])

    #如果button属性是文字类型，将其统一成textlink
    if widget_type == Widget.Button:
        for ancestor in json_node['ancestors']:
            if 'TextView' in ancestor:
                widget_type = Widget.TextLink
                break
    #return Widget.Button

    # 次序2：ActionMenuItemView
    if 'ActionMenuItemView' in json_node['class']:
        return Widget.Button

    # 次序3：判断当前节点的任何一个祖先是否存在明确标识
    if widget_type == Widget.Unclassified:
        for ancestor in json_node['ancestors']:
            widget_type = infer_widget_from_string(ancestor)
            if widget_type != Widget.Unclassified:  # 当找到某个可判断类型的祖先时退出
                break

    # 次序4：确定嵌套在layout内部属性不可点击但实际行为可点击情况
    if widget_type != Widget.Unclassified:
        if widget_type == Widget.TextView and (json_node['clickable'] or args[KEY_PARENT_CLICKABLE]):
            widget_type = Widget.TextLink
        elif widget_type == Widget.ImageView and (json_node['clickable'] or args[KEY_PARENT_CLICKABLE]):
                widget_type = Widget.ImageLink
        #return widget_type

    return widget_type


def infer_widget_from_string(class_name):
    """
    当控件类型名称明确地出现在字符串中时，返回对应的控件类型；如果均未出现，返回Widget.Unclassified
    :param class_name: 待检查字符串
    :return: 控件类型
    """
    # TODO 注意这里的判断顺序对结果有影响
    if "Layout" in class_name:
        return Widget.Layout
    if "CheckBox" in class_name:
        return Widget.CheckBox
    if "EditText" in class_name:
        return Widget.EditText
    # if "ImageButton" in class_name:
    #     return Widget.ImageButton
    if "Button" in class_name:
        return Widget.Button
    if "TextView" in class_name:
        return Widget.TextView
    if "Image" in class_name:
        return Widget.ImageView

    return Widget.Unclassified


def draw_widget(im, widget_type, bounds):
    """
    在im对象中绘制范围为bounds的控件草图
    :param im: 待绘制的图片对象
    :param widget_type: 待绘制的控件类型
    :param bounds: 待绘制的控件范围
    :return:
    """
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    # 不绘制面积过小的控件
    # TODO 确定不需要绘制的面积阈值
    if w <= 0 or h <= 0:
        return

    if widget_type == Widget.Button:
        im.paste(im_button.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.ImageView:
        im.paste(im_image_view.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.EditText:
        im.paste(im_edit_text.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.TextView:
        im.paste(im_text_view.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.CheckBox:
        im.paste(im_checkbox.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.ImageLink:
        im.paste(im_image_button.resize((w, h)), box=(bounds[0], bounds[1]))
    elif widget_type == Widget.TextLink:
        im.paste(im_text_link.resize((w, h)), box=(bounds[0], bounds[1]))


if __name__ == '__main__':
    app_layout_dir = "./Top Apps"
    output_path = "./output"

    # 遍历布局文件访问节点清理结构
    if CLEAN_JSON:
        print("Start cleaning json files ...")
        for case_dir in os.listdir(app_layout_dir):
            if not case_dir.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(app_layout_dir, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        json_handler(os.path.join(app_layout_dir, case_dir, file),
                                     os.path.join(output_path, case_dir, file_name + "." + str(LEVEL) + ".json"))
                print(os.path.join(output_path, case_dir))
        print("Output cleaned json files saved in " + output_path)

    # 根据布局信息生成草图
    output_path = "./Top Apps"
    if CREATE_SKETCHES:
        print("Start generating sketches ...")
        for case_dir in os.listdir(app_layout_dir):
            if not case_dir.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(app_layout_dir, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        sketch_generation(os.path.join(app_layout_dir, case_dir, file),
                                          os.path.join(output_path, case_dir, file_name + '-sketch.png'))
                print(os.path.join(output_path, case_dir), "finished")
        print("Output sketches saved in", output_path, "ended in -sketch.png")
