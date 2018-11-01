import json
import os
import time
import hashlib
import shutil
from pprint import pprint
from PIL import Image
from enum import Enum

# 程序运行参数
CLEAN_JSON = False
LEVEL = 1
DRAW_SKETCHES = True
COLOR_MODE = False  # True 为色彩模式，False 为草图模式
CUT_WIDGET = True

# Layout 默认长宽
WIDTH = 1440
HEIGHT = 2560

# 画布长宽
SKETCH_WIDTH = 576
SKETCH_HEIGHT = 1024

# 用于 File Hash 的缓存大小
FILE_READ_BUF_SIZE = 65536

# 用于 layout 层次间传递辅助参数
KEY_PARENT_CLICKABLE = 'key_parent_clickable'

# 控件对应的图像
im_button = Image.open('./drawings/frameless/button.png')
im_edit_text = Image.open('./drawings/frameless/edit_text.png')
im_image_view = Image.open('./drawings/frameless/image_view.png')
im_text_view = Image.open('./drawings/frameless/text_view.png')
im_image_link = Image.open('./drawings/frameless/image_link.png')
im_text_link = Image.open('./drawings/frameless/text_link.png')
im_checkbox = Image.open('./drawings/frameless/checkbox.png')

BLACK_RGB = (0, 0, 0)
RED_RGB = (255, 0, 0)
GREEN_RGB = (0, 255, 0)
BLUE_RGB = (0, 0, 255)
YELLOW_RGB = (255, 255, 0)
DARKRED_RGB = (255, 0, 255)
CYAN_RGB = (0, 255, 255)

# 路径
JSON_LAYOUT_PATH = "./Top Apps"
JSON_OUT_PATH = "./output"
SKETCH_OUT_DIR = "./Top Apps"
LAYOUT_SEQ_OUT_PATH = "./layout_sequence.lst"
WIDGET_CUT_OUT_PATH = './widget_cut'


class Widget(Enum):
    Layout = 0
    Unclassified = 1
    Button = 2
    TextView = 3
    TextLink = 4
    ImageView = 5
    ImageLink = 6
    EditText = 7
    CheckBox = 8


def json_handler(read_json_path, write_json_path):
    """
    读入json文件，输出清理后的简洁json文件
    :param read_json_path: 待处理json文件路径
    :param write_json_path: 处理后json文件路径
    :return:
    """
    with open(read_json_path, 'r') as f:
        json_obj = json.load(f)

    # FIXME 检查 Rico 数据集中 layout 是否从 root.children[0] 开始
    root = json_obj['activity']['root']
    top_framelayout = root['children'][0]

    dfs_clean_json(top_framelayout)

    with open(write_json_path, 'w') as f:
        json.dump(top_framelayout, f, indent=2)


def dfs_clean_json(json_obj):
    """
    通过深度优先搜索的方式清理冗余的json属性，保留
    :param json_obj:
    :return:
    """
    delete_unrelated_attrs(json_obj)

    if 'children' in json_obj:
        for i in range(len(json_obj['children'])):
            dfs_clean_json(json_obj['children'][i])


def delete_unrelated_attrs(json_node):
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


def sketch_samples_generation(layout_json_path, output_img_path):
    """
    读入布局文件，生成处理后的草图文件并保存到指定路径中
    :param layout_json_path: 待处理json格式布局文件的路径
    :param output_img_path: 生成的草图图片的保存路径
    :return:
    """
    with open(layout_json_path, 'r') as f:
        json_obj = json.load(f)

    # FIXME 检查 Rico 数据集中 layout 是否从 root.children[0] 开始
    root = json_obj['activity']['root']
    top_framelayout = root['children'][0]

    # 准备裁剪控件
    screenshot_path = os.path.splitext(layout_json_path)[0] + ".jpg"
    im_screenshot = Image.open(screenshot_path)
    rico_index = os.path.basename(layout_json_path).split('.')[0]
    img_sha1 = hash_file_sha1(screenshot_path)

    # 新建空白草图画布，DFS后将绘制的草图保存到文件
    im_sketch = Image.new('RGB', (SKETCH_WIDTH, SKETCH_HEIGHT), (255, 255, 255))

    args = {KEY_PARENT_CLICKABLE: False}
    tokens = [str(rico_index)]
    dfs_draw_widget(top_framelayout, im_screenshot, im_sketch, args, tokens, rico_index)

    im_sketch.save(output_img_path)

    with open(LAYOUT_SEQ_OUT_PATH, "a") as f:
        f.write(" ".join(tokens) + '\n')


def hash_file_sha1(file_path):
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(FILE_READ_BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def dfs_draw_widget(json_obj, im_screenshot, im_sketch, args, tokens, rico_index):
    """
    通过深度优先搜索的方式按节点绘制草图，将其直接绘制在im对象上
    :param json_obj: 待分析的json节点
    :param im_screenshot: 布局对应的截图对象
    :param im_sketch: 待绘制的草图对象
    :param args: 其他需要逐层传递的参数
    :param tokens: 待添加的 token 序列
    :param rico_index: Rico 序号
    :return:
    """
    # 不绘制属性visible-to-user值为真的控件
    if not json_obj['visible-to-user']:
        return

    # TODO 修改或加入更多规则判断，调用 im.paste 绘制相应的图形；在 args 中增加其他属性辅助判断，如上层的 clickable 属性

    widget_type = infer_widget_type(json_obj, args)

    # 如果外层 layout 的 clickable 属性为真，则传递该参数用于后续类型判断
    if widget_type == Widget.Layout and json_obj['clickable']:
        args[KEY_PARENT_CLICKABLE] = True

    # 在文件中保存 DFS-Tree
    tokens.append(widget_type.name)

    # 在草图中绘制除 Layout 以外的控件
    if widget_type != Widget.Layout:
        # 经过规则推断仍无法判断控件类型的，不绘制
        if widget_type != Widget.Unclassified:
            draw_widget(im_sketch, widget_type, json_obj['bounds'])
        # 裁切其他控件便于分析
        if CUT_WIDGET:
            w = json_obj['bounds'][2] - json_obj['bounds'][0]
            h = json_obj['bounds'][3] - json_obj['bounds'][1]

            if w > 5 and h > 5:
                node_sha1 = hashlib.sha1(str(json_obj).encode("utf-8"))
                jpg_bounds = (int(json_obj['bounds'][0] / WIDTH * im_screenshot.size[0]),
                              int(json_obj['bounds'][1] / HEIGHT * im_screenshot.size[1]),
                              int(json_obj['bounds'][2] / WIDTH * im_screenshot.size[0]),
                              int(json_obj['bounds'][3] / HEIGHT * im_screenshot.size[1]))
                class_tokens = json_obj['class'].rsplit('.', 1)
                outfile_name = os.path.join(WIDGET_CUT_OUT_PATH, widget_type.name,
                                            "".join([rico_index, '-',
                                                     class_tokens[1] if len(class_tokens) > 1 else json_obj['class'],
                                                     '-', node_sha1.hexdigest()[0:6], '.jpg']))
                im_screenshot.crop(jpg_bounds).save(outfile_name)

    # 当json_obj无children属性时，不再递归执行
    # TODO 考虑其他不再需要递归访问的情形
    if 'children' in json_obj and (widget_type == Widget.Unclassified or widget_type == Widget.Layout):
        tokens.append("{")
        for i in range(len(json_obj['children'])):
            dfs_draw_widget(json_obj['children'][i], im_screenshot, im_sketch, args, tokens, rico_index)
        tokens.append("}")

    args[KEY_PARENT_CLICKABLE] = False


def infer_widget_type(json_node, args):
    """
    接收json节点，返回关键词匹配后根据规则推断的控件类型
    :param json_node: 待分析json节点
    :param args: 其他属性
    :return: 推断的控件类型结果
    """
    # TODO 在这里规则，返回的类型是最终推断类型；规则的先后顺序对结果有影响。

    # 次序1：官方提供的特殊情况
    if 'ActionMenuItemView' in json_node['class'] or 'AppCompatImageButton' in json_node['class'] or 'ActionMenuView' in json_node['class']:
        return Widget.Button
    # 次序2：其他特殊情况
    if 'NavItemView' in json_node['class'] or 'ToolBarItemView' in json_node['class'] or 'DrawerToolBarItemView' in json_node['class']:
        return Widget.Button

    # 次序2：判断class_name是否存在明确的控件类型标识
    widget_type = infer_widget_type_from_string(json_node['class'])

    # 到此为止的Button不区分图形、文字。如果名称中不含Image的图形按钮也会被认为是Button
    # 如果button属性是文字类型，将其统一成TextLink
    if widget_type == Widget.Button:
        for ancestor in json_node['ancestors']:
            if 'TextView' in ancestor:
                widget_type = Widget.TextLink
                break

    # 次序3：判断未明确分类节点的任何一个祖先是否存在明确标识
    if widget_type == Widget.Unclassified:
        for ancestor in json_node['ancestors']:
            widget_type = infer_widget_type_from_string(ancestor)
            if widget_type != Widget.Unclassified:
                break

    # 次序4：确定嵌套在layout内部属性不可点击但实际行为可点击情况
    if widget_type == Widget.TextView and (json_node['clickable'] or args[KEY_PARENT_CLICKABLE]):
        widget_type = Widget.TextLink
    elif widget_type == Widget.ImageView and (json_node['clickable'] or args[KEY_PARENT_CLICKABLE]):
        w = json_node['bounds'][2] - json_node['bounds'][0]
        h = json_node['bounds'][3] - json_node['bounds'][1]
        if w > 300 and h > 300:
            widget_type = Widget.ImageLink  # ImageLink 仅出现在这种情形
        else:
            widget_type = Widget.Button

    return widget_type


def infer_widget_type_from_string(class_name):
    """
    当控件类型名称明确地出现在字符串中时，返回对应的控件类型；如果均未出现，返回Widget.Unclassified
    :param class_name: 待检查字符串
    :return: 控件类型
    """
    # TODO 判断顺序对结果有影响
    if "Layout" in class_name:
        return Widget.Layout
    if "CheckBox" in class_name:
        return Widget.CheckBox
    if "EditText" in class_name:
        return Widget.EditText
    if "Image" in class_name:
        return Widget.ImageView
    if "Button" in class_name:
        return Widget.Button
    if "TextView" in class_name:
        return Widget.TextView
    if "BadgableGlyphView" in class_name:
        return Widget.Button

    return Widget.Unclassified


def draw_widget(im, widget_type, bounds):
    """
    在im对象中绘制范围为bounds的控件草图
    :param im: 待绘制的图片对象
    :param widget_type: 待绘制的控件类型
    :param bounds: 待绘制的控件范围
    :return:
    """
    margin = 1
    margin_inner = 4
    bounds = (int((bounds[0]) / WIDTH * SKETCH_WIDTH),
              int((bounds[1]) / HEIGHT * SKETCH_HEIGHT),
              int((bounds[2]) / WIDTH * SKETCH_WIDTH),
              int((bounds[3]) / HEIGHT * SKETCH_HEIGHT))
    bounds_inner = (bounds[0] + margin_inner, bounds[1] + margin_inner, bounds[2] - margin_inner, bounds[3] - margin_inner)

    w = bounds_inner[2] - bounds_inner[0]
    h = bounds_inner[3] - bounds_inner[1]

    # 不绘制面积过小的控件
    # TODO 确定不需要绘制的面积阈值
    if w <= 1 or h <= 1:
        return

    if COLOR_MODE:
        if widget_type == Widget.Button:
            im.paste(im=RED_RGB, box=bounds_inner)
        elif widget_type == Widget.ImageView:
            im.paste(im=GREEN_RGB, box=bounds_inner)
        elif widget_type == Widget.EditText:
            im.paste(im=BLUE_RGB, box=bounds_inner)
        elif widget_type == Widget.TextView:
            im.paste(im=YELLOW_RGB, box=bounds_inner)
        elif widget_type == Widget.CheckBox:
            im.paste(im=DARKRED_RGB, box=bounds_inner)
        elif widget_type == Widget.ImageLink:
            im.paste(im=CYAN_RGB, box=bounds_inner)
        elif widget_type == Widget.TextLink:
            im.paste(im=BLACK_RGB, box=bounds_inner)
    else:
        im.paste(im=BLACK_RGB, box=(bounds[0] + margin, bounds[1] + margin, bounds[2] - margin, bounds[3] - margin))
        if widget_type == Widget.Button:
            im.paste(im_button.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.ImageView:
            im.paste(im_image_view.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.EditText:
            im.paste(im_edit_text.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.TextView:
            im.paste(im_text_view.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.CheckBox:
            im.paste(im_checkbox.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.ImageLink:
            im.paste(im_image_link.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        elif widget_type == Widget.TextLink:
            im.paste(im_text_link.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))


if __name__ == '__main__':
    start_time = time.time()
    # 遍历布局文件访问节点清理结构
    if CLEAN_JSON:
        print(">>> Start cleaning json files ...")
        for case_dir_name in os.listdir(JSON_LAYOUT_PATH):
            if not case_dir_name.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(JSON_OUT_PATH, case_dir_name)):
                    os.makedirs(os.path.join(JSON_OUT_PATH, case_dir_name))
                for file in os.listdir(os.path.join(JSON_LAYOUT_PATH, case_dir_name)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        json_handler(os.path.join(JSON_LAYOUT_PATH, case_dir_name, file),
                                     os.path.join(JSON_OUT_PATH, case_dir_name,
                                                  "".join([file_name, '.', str(LEVEL), ".json"])))
                print(os.path.join(JSON_OUT_PATH, case_dir_name))
        print("<<< Cleaned json files saved in " + JSON_OUT_PATH)

    # 初始化放置控件裁切的位置
    if CUT_WIDGET:
        for widget in Widget:
            if widget != Widget.Layout:
                dir_path = os.path.join(WIDGET_CUT_OUT_PATH, widget.name)
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                os.makedirs(dir_path)
        print("### Preparing directories to save widget crops ... OK")

    # 根据布局信息生成草图
    if DRAW_SKETCHES:
        print(">>> Start generating sketches ...")
        open(LAYOUT_SEQ_OUT_PATH, "w")
        for case_dir_name in os.listdir(JSON_LAYOUT_PATH):
            if not case_dir_name.startswith("."):  # hidden files
                if not os.path.exists(os.path.join(SKETCH_OUT_DIR, case_dir_name)):
                    os.makedirs(os.path.join(SKETCH_OUT_DIR, case_dir_name))
                for file in os.listdir(os.path.join(JSON_LAYOUT_PATH, case_dir_name)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        sketch_samples_generation(os.path.join(JSON_LAYOUT_PATH, case_dir_name, file),
                                                  os.path.join(SKETCH_OUT_DIR, case_dir_name,
                                                               "".join([file_name, '-sketch.png'])))
                print(os.path.join(SKETCH_OUT_DIR, case_dir_name), ">> OK")
        print("<<< All generated sketches saved in", SKETCH_OUT_DIR, "ended with *sketch.png")
    print('Duration: {:.2f} s'.format(time.time() - start_time))
