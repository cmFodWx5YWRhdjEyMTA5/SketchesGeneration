import json
import os
import time
import hashlib
import shutil
import csv
from PIL import Image
from enum import Enum

# 程序运行参数
CLEAN_JSON = False
DRAW_SKETCHES = True

COLOR_MODE = True  # True 为色彩模式，False 为草图模式
CROP_WIDGET = False
TRAINING_DATA_MODE = True  # 构造训练集支持文件
ANALYSIS_MODE = False  # 存储属性分析文件

# 画布长宽
SKETCH_WIDTH = 576
SKETCH_HEIGHT = 1024

WIDGET_FRAME_MARGIN = 1
WIDGET_INNER_MARGIN = 2

FILE_READ_BUF_SIZE = 65536  # 用于 File Hash 的缓存大小
SEQ_LINE = 0  # xml_sequence 的行号

# 路径
RICO_DIR = 'E:\\sketches-test\\rico-data'
CLEANED_JSON_DIR = 'E:\\sketches-test\\cleaned-json'
SKETCH_OUT_DIR = 'E:\\sketches-test\\sketches'
DATA_DIR = 'E:\\sketches-test\\data'
LAYOUT_SEQ_FILE_NAME = 'layout_sequence.lst'
INDEX_LINE_MAP_FILE_NAME = 'index_map.lst'
WIDGET_CUT_OUT_PATH = './widget_cut'
CSV_FILE_PATH = './analysis_result.csv'

# Layout 默认长宽
WIDTH = 1440
HEIGHT = 2560

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
# im_toolbar = Image.open('./drawings/frameless/toolbar.png')

BLACK_RGB = (0, 0, 0)
GRAY_RGB = (128, 128, 128)
RED_RGB = (255, 0, 0)
LIME_RGB = (0, 255, 0)
BLUE_RGB = (0, 0, 255)
YELLOW_RGB = (255, 255, 0)
MAGENTA_RGB = (255, 0, 255)
CYAN_RGB = (0, 255, 255)
MAROON_RGB = (128, 0, 0)
GREEN_RGB = (0, 128, 0)
NAVY_RGB = (0, 0, 128)


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
    # Toolbar = 9


def json_handler(dir_name, rico_index):
    """
    将 RICO_DIR/dir_name 文件夹中的 json 文件清理后输出全包含可见控件的 json 文件保存到 CLEANED_JSON_DIR/dir_name 中
    :param dir_name: RICO_DIR 中子文件夹名称
    :param rico_index: Rico 序号
    :return:
    """
    with open(os.path.join(RICO_DIR, dir_name, rico_index + '.json'), 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']['children'][0]

    new_root = {k: root[k] for k, v in root.items() if k != 'children'}

    dfs_clean_json(root, new_root)

    with open(os.path.join(CLEANED_JSON_DIR, dir_name, rico_index + '.json'), 'w') as f:
        json.dump(new_root, f, indent=2)


def dfs_clean_json(json_obj, new_root):
    """
    通过深度优先搜索的方式清理 visible-to-user 值为 false 的控件
    :param json_obj: 原始 json 节点
    :param new_root: 已清理的 json_obj 副本
    :return:
    """
    # delete_unrelated_attrs(json_obj)
    if 'children' in json_obj:
        new_root['children'] = []
        for child in json_obj['children']:
            if child is not None and child['visible-to-user']:
                child_copy = {k: child[k] for k, v in child.items() if k != 'children'}
                new_root['children'].append(child_copy)
                dfs_clean_json(child, child_copy)


def delete_unrelated_attrs(json_node):
    """
    确定节点 json_node 保留的 json 属性
    :param json_node: 待处理的字典格式的 json 节点
    :return:
    """
    reserved_list = ['class', 'children', 'visibility']
    key_list = [key for key in json_node.keys() if key not in reserved_list]
    for k in key_list:
        del json_node[k]


def sketch_samples_generation(dir_name, rico_index):
    """
    读入 CLEANED_JSON_DIR/dir_name 文件夹中的 json 布局文件，生成处理后的草图文件，保存到 SKETCH_OUT_DIR/dir_name 中
    :param dir_name: 子文件夹名称
    :param rico_index: Rico 序号
    :return:
    """
    global SEQ_LINE
    with open(os.path.join(CLEANED_JSON_DIR, dir_name, rico_index + '.json'), 'r') as f:
        root = json.load(f)

    # 去除冗余的外层嵌套
    # TODO 检查正确性
    while 'children' in root and len(root['children']) == 1:
        root = root['children'][0]

    # 准备裁剪控件
    screenshot_path = os.path.join(RICO_DIR, dir_name, rico_index + '.jpg')
    im_screenshot = Image.open(screenshot_path)
    img_sha1 = hash_file_sha1(screenshot_path)  # 生成文件的 sha1 值，暂未使用

    # 新建空白草图画布，DFS 后将绘制的草图保存到文件
    im_sketch = Image.new('RGB', (SKETCH_WIDTH, SKETCH_HEIGHT), (255, 255, 255))

    args = {KEY_PARENT_CLICKABLE: False}
    tokens = []  # 用于 layout sequence
    # tokens = [str(rico_index)]  # 用于 layout sequence
    csv_rows = []  # 用于生成 csv 分析文件

    dfs_draw_widget(root, im_screenshot, im_sketch, args, tokens, rico_index, csv_rows)

    # im_sketch.rotate(90, expand=1).save(output_img_path)
    im_sketch.save(os.path.join(SKETCH_OUT_DIR, dir_name, rico_index + '-sketch.png'))

    if TRAINING_DATA_MODE:

        # FIXME 处理空白画布情况
        if len(tokens) == 1:
            tokens.append(Widget.Layout.name)

        with open(os.path.join(DATA_DIR, LAYOUT_SEQ_FILE_NAME), 'a') as f:
            f.write(' '.join(tokens) + '\n')

        with open(os.path.join(DATA_DIR, INDEX_LINE_MAP_FILE_NAME), 'a') as f:
            f.write(str(rico_index) + ' ' + str(SEQ_LINE) + '\n')

        SEQ_LINE = SEQ_LINE + 1

    # 将控件属性保存到文件中
    if ANALYSIS_MODE:
        with open(CSV_FILE_PATH, 'a', newline='') as f:
            csv.writer(f).writerows(csv_rows)


def hash_file_sha1(file_path):
    """
    将路径为 file_path 的文件转换成其 sha1 值
    :param file_path:
    :return:
    """
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(FILE_READ_BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def dfs_draw_widget(json_obj, im_screenshot, im_sketch, args, tokens, rico_index, csv_rows):
    """
    通过深度优先搜索的方式按节点绘制草图，将其直接绘制在 Pillow 对象上
    :param json_obj: 待分析的 json 节点
    :param im_screenshot: 布局对应的截图 Pillow 对象
    :param im_sketch: 待绘制的草图 Pillow 对象
    :param args: 其他需要逐层传递的参数
    :param tokens: 待添加的 token 序列
    :param rico_index: Rico 序号
    :param csv_rows: 用于将控件属性信息记录到 csv 分析文件
    :return:
    """
    # 不绘制属性visible-to-user值为真的控件
    # if not json_obj['visible-to-user']:
    #     return

    # 修改或加入更多规则判断，调用 im.paste 绘制相应的图形；在 args 中增加其他属性辅助判断，如上层的 clickable 属性

    widget_type = infer_widget_type(json_obj, args)

    # csv 文件中的一行数据
    # TODO 在这里添加 CSV 文件每一行内容
    if ANALYSIS_MODE:
        if widget_type != Widget.Layout:
            csv_row = [widget_type, rico_index, json_obj['clickable'], json_obj['focusable'], json_obj['focused'],
                       json_obj['selected'], json_obj['draw'], json_obj['ancestors']]
            csv_rows.append(csv_row)

    # 传递参数：如果外层 layout 的 clickable 属性为真，则传递该参数用于后续类型判断
    if widget_type == Widget.Layout and json_obj['clickable']:
        args[KEY_PARENT_CLICKABLE] = True

    # 将 Layout DFS-sequence 保存到文件中
    # FIXME 有 children 节点的 Unclassified 控件修改为 Layout；若没有，不输出。
    if 'children' in json_obj:
        tokens.append(Widget.Layout.name)
    else:
        tokens.append(widget_type.name)
    # if widget_type != Widget.Unclassified:
    #     tokens.append(widget_type.name)
    # elif 'children' in json_obj:
    #     tokens.append(Widget.Layout.name)

    # DFS 绘制控件
    if widget_type != Widget.Layout:

        # 不绘制仍无法判断类型的控件
        if widget_type != Widget.Unclassified:
            draw_widget(im_sketch, widget_type, json_obj['bounds'])

        if CROP_WIDGET:
            crop_widget(json_obj, im_screenshot, rico_index, widget_type)

    # 当json_obj无children属性时，不再递归执行；确定其他不再需要递归访问的情形
    if 'children' in json_obj and (widget_type == Widget.Unclassified or widget_type == Widget.Layout):
        tokens.append('{')
        for i in range(len(json_obj['children'])):
            dfs_draw_widget(json_obj['children'][i], im_screenshot, im_sketch, args, tokens, rico_index, csv_rows)
        tokens.append('}')

    # 要在这里清除传递的参数
    args[KEY_PARENT_CLICKABLE] = False


def crop_widget(json_obj, im_screenshot, rico_index, widget_type):
    """
    裁剪控件并保存到指定路径
    :param json_obj: 控件的 json 对象
    :param im_screenshot: 屏幕截图的 Pillow 对象
    :param rico_index: Rico 序号
    :param widget_type: 控件的推断类型
    """
    w = json_obj['bounds'][2] - json_obj['bounds'][0]
    h = json_obj['bounds'][3] - json_obj['bounds'][1]

    if w > 5 and h > 5:
        node_sha1 = hashlib.sha1(str(json_obj).encode('utf-8'))
        jpg_bounds = (int(json_obj['bounds'][0] / WIDTH * im_screenshot.size[0]),
                      int(json_obj['bounds'][1] / HEIGHT * im_screenshot.size[1]),
                      int(json_obj['bounds'][2] / WIDTH * im_screenshot.size[0]),
                      int(json_obj['bounds'][3] / HEIGHT * im_screenshot.size[1]))
        class_tokens = json_obj['class'].rsplit('.', 1)
        outfile_name = os.path.join(WIDGET_CUT_OUT_PATH, widget_type.name,
                                    ''.join([rico_index, '-',
                                             class_tokens[1] if len(class_tokens) > 1 else json_obj['class'], '-',
                                             node_sha1.hexdigest()[0:6], '.jpg']))

        im_screenshot.crop(jpg_bounds).save(outfile_name)


def infer_widget_type(json_node, args):
    """
    接收json节点，返回关键词匹配后根据规则推断的控件类型
    :param json_node: 待分析json节点
    :param args: 其他属性
    :return: 推断的控件类型结果
    """
    # 执行这些规则后，返回最终推断类型；规则的先后顺序对结果有影响。

    # 次序1：官方提供的特殊情况
    if 'ActionMenuItemView' in json_node['class'] or 'AppCompatImageButton' in json_node['class']:
        return Widget.Button
    # 次序2：其他特殊情况
    if 'NavItemView' in json_node['class'] or 'ToolBarItemView' in json_node['class'] or 'DrawerToolBarItemView' in \
            json_node['class']:
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
        # 将面积较大的图转换成 ImageLink
        # FIXME 确定 ImageLink 面积阈值
        widget_type = Widget.ImageLink if w > 200 and h > 200 else Widget.Button  # ImageLink 仅出现在这种情形

    return widget_type


def infer_widget_type_from_string(class_name):
    """
    当控件类型名称明确地包括于字符串中时，直接确定该控件类型；否则返回 Unclassified
    :param class_name: 待检查字符串
    :return: 控件类型
    """
    # 判断顺序对结果有影响
    if 'Layout' in class_name or 'ListView' in class_name or 'RecyclerView' in class_name:
        return Widget.Layout
    # if 'Toolbar' in class_name:
    #     return Widget.Toolbar
    if 'CheckBox' in class_name:
        return Widget.CheckBox
    if 'EditText' in class_name:
        return Widget.EditText
    if 'Image' in class_name:
        return Widget.ImageView
    if 'Button' in class_name or 'BadgableGlyphView' in class_name:
        return Widget.Button
    if 'TextView' in class_name:
        return Widget.TextView

    return Widget.Unclassified


def draw_widget(im, widget_type, bounds):
    """
    在im对象中绘制范围为bounds的控件草图
    :param im: 待绘制的图片对象
    :param widget_type: 待绘制的控件类型
    :param bounds: 待绘制的控件范围
    :return:
    """

    bounds_sketch = (int((bounds[0]) / WIDTH * SKETCH_WIDTH),
                     int((bounds[1]) / HEIGHT * SKETCH_HEIGHT),
                     int((bounds[2]) / WIDTH * SKETCH_WIDTH),
                     int((bounds[3]) / HEIGHT * SKETCH_HEIGHT))

    # 将长宽按比例缩小到画布上后确定草图元素缩放范围
    bounds_inner = (bounds_sketch[0] + WIDGET_INNER_MARGIN, bounds_sketch[1] + WIDGET_INNER_MARGIN,
                    bounds_sketch[2] - WIDGET_INNER_MARGIN, bounds_sketch[3] - WIDGET_INNER_MARGIN)

    w = bounds_inner[2] - bounds_inner[0]
    h = bounds_inner[3] - bounds_inner[1]

    # 不绘制面积过小的控件
    if w <= 1 or h <= 1:
        return

    if COLOR_MODE:
        if widget_type == Widget.Button:
            im.paste(im=RED_RGB, box=bounds_inner)
        elif widget_type == Widget.TextView:
            im.paste(im=YELLOW_RGB, box=bounds_inner)
        elif widget_type == Widget.TextLink:
            im.paste(im=BLACK_RGB, box=bounds_inner)
        elif widget_type == Widget.EditText:
            im.paste(im=BLUE_RGB, box=bounds_inner)
        elif widget_type == Widget.ImageView:
            im.paste(im=LIME_RGB, box=bounds_inner)
        elif widget_type == Widget.ImageLink:
            im.paste(im=CYAN_RGB, box=bounds_inner)
        elif widget_type == Widget.CheckBox:
            im.paste(im=MAGENTA_RGB, box=bounds_inner)
        # elif widget_type == Widget.Toolbar:
        #     im.paste(im=GRAY_RGB, box=bounds_inner)
    else:
        im.paste(im=BLACK_RGB, box=(
            bounds_sketch[0] + WIDGET_FRAME_MARGIN, bounds_sketch[1] + WIDGET_FRAME_MARGIN,
            bounds_sketch[2] - WIDGET_FRAME_MARGIN, bounds_sketch[3] - WIDGET_FRAME_MARGIN))
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
        # elif widget_type == Widget.Toolbar:
        #     im.paste(im_toolbar.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))


if __name__ == '__main__':
    start_time = time.time()

    print('## Program configuration ##')
    print('# CLEAN_JSON >', CLEAN_JSON)
    print('# DRAW_SKETCHES >', DRAW_SKETCHES)
    print('# COLOR_MODE >', COLOR_MODE)
    print('# CUT_WIDGET >', CROP_WIDGET)
    print('# ANALYSIS_MODE >', ANALYSIS_MODE)

    # 遍历布局文件访问节点清理结构
    if CLEAN_JSON:
        print('---------------------------------')
        print('>>> Start cleaning json files in', RICO_DIR, '...')

        # 检查输出文件夹状态
        if not os.path.exists(CLEANED_JSON_DIR):
            print('### Making directories to save cleaned json files ... OK')
            os.makedirs(CLEANED_JSON_DIR)
        print('### Checking directories to save cleaned json files:', CLEANED_JSON_DIR, '... OK')

        for case_name in os.listdir(RICO_DIR):
            if not case_name.startswith('.'):  # hidden files
                input_case_dir = os.path.join(RICO_DIR, case_name)
                output_case_dir = os.path.join(CLEANED_JSON_DIR, case_name)
                print('>>> Processing', output_case_dir, '...', end=' ')

                if not os.path.exists(output_case_dir):
                    os.makedirs(output_case_dir)
                for file in os.listdir(input_case_dir):
                    if file.endswith('.json'):
                        json_handler(case_name, file.split('.')[0])
                print('OK')

        print('<<< Cleaned json files saved in ' + CLEANED_JSON_DIR)

    # 初始化放置控件裁切的位置
    if CROP_WIDGET:
        for widget in Widget:
            if widget != Widget.Layout:
                dir_path = os.path.join(WIDGET_CUT_OUT_PATH, widget.name)
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                os.makedirs(dir_path)
        print('### Checking/Making directories to save widget crops ... OK')

    # 根据布局信息生成草图
    if DRAW_SKETCHES:
        print('---------------------------------')
        print('>>> Start generating sketches based on cleaned json files in', CLEANED_JSON_DIR, '...')

        # 检查输出文件夹状态
        if not os.path.exists(SKETCH_OUT_DIR):
            print('### Making directories to save generated sketches ... OK')
            os.makedirs(SKETCH_OUT_DIR)
        print('### Checking directories to save generated sketches:', SKETCH_OUT_DIR, '... OK')

        if TRAINING_DATA_MODE:
            # 先创建/覆盖文件用于添加内容
            if not os.path.exists(DATA_DIR):
                print('### Making data directory to save training related files ... OK')
                os.makedirs(DATA_DIR)
            print('### Checking data directory to save training related files:', DATA_DIR, '... OK')
            open(os.path.join(DATA_DIR, LAYOUT_SEQ_FILE_NAME), 'w', newline='')
            open(os.path.join(DATA_DIR, INDEX_LINE_MAP_FILE_NAME), 'w', newline='')
            print('### Creating raining related files ... OK')

        if ANALYSIS_MODE:
            with open(CSV_FILE_PATH, 'w', newline='') as f:
                # TODO 在这里添加 CSV 文件页眉
                csv.writer(f).writerow(['type', 'rico-index', 'clickable', 'focusable', 'focused', 'selected', 'draw', 'ancestors'])

        for case_name in os.listdir(RICO_DIR):
            if not case_name.startswith('.'):  # hidden files
                input_case_dir = os.path.join(CLEANED_JSON_DIR, case_name)
                output_case_dir = os.path.join(SKETCH_OUT_DIR, case_name)
                print('>>> Processing', output_case_dir, '...', end=' ')

                if not os.path.exists(output_case_dir):
                    os.makedirs(output_case_dir)
                for file in os.listdir(input_case_dir):
                    if file.endswith('.json'):
                        sketch_samples_generation(case_name, file.split('.')[0])
                print('OK')

        print('<<< Generated sketches saved in', SKETCH_OUT_DIR)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
