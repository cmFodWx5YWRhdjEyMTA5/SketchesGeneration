import csv
import hashlib
import json
import operator
import os
import shutil
import time
from configparser import ConfigParser, ExtendedInterpolation
from datetime import datetime

import numpy as np
from PIL import Image
from anytree import Node, RenderTree

from utils.files import check_make_dir
from utils.widget import Widget, WidgetNode, WidgetColor

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('../config.ini')

# 路径
data_dir = cfg.get('dirs', 'nmt_data')
layout_sequences_fp = cfg.get('files', 'sequences')
index_map_fp = cfg.get('files', 'index_map')

rico_divided_dir = cfg.get('dirs', 'rico_divided')
cleaned_jsons_dir = cfg.get('dirs', 'cleaned_jsons')
colored_pics_divided_dir = cfg.get('dirs', 'colored_pics_divided')

WIDGET_CUT_OUT_PATH = cfg.get('debug', 'widget_flakes')
CSV_FILE_PATH = cfg.get('debug', 'csv_analysis')
COLUMN_TITLES = json.loads(cfg.get('debug', 'columns'))

# 画布长宽
SKETCH_WIDTH = cfg.getint('nmt', 'sketch_width')
SKETCH_HEIGHT = cfg.getint('nmt', 'sketch_height')

IMG_MODE = 'color'  # color 为色彩模式，sketch 为草图模式
TRAINING_DATA_MODE = True  # 构造训练集支持文件
CROP_WIDGET = False
ANALYSIS_MODE = False  # 存储属性分析文件
PRINT_LOG = False

# Layout 默认长宽
WIDTH = 1440
HEIGHT = 2560

FILE_READ_BUF_SIZE = 65536  # 用于 File Hash 的缓存大小
LEN_SHA1 = 10  # 节点 sha1 值的截取保留长度

# 用于 layout 层次间传递辅助参数
KEY_ANCESTOR_CLICKABLE = 'key_ancestor_clickable'
KEY_TREE_ROOT = 'tree_root'

seq_line = 0  # xml_sequence 的行号

widgets_count = {}
container_cnt = {}


def sketch_samples_generation(rico_dir, json_dir, sketches_dir, rico_index, seq_file, i2l_map_file):
    """
    读入 cleaned_json_dir 文件夹中的 json 布局文件，生成处理后的草图文件，保存到 sketches_out_dir 中
    :param rico_dir: Rico 文件夹存放的用于裁剪的屏幕截图
    :param json_dir: cleaned json 文件夹路径
    :param sketches_dir: 输出草图的存放文件夹路径
    :param rico_index: Rico 序号
    :param seq_file: layout tokens 序列文件路径
    :param i2l_map_file: index: line_number 字典文件路径
    :return:
    """
    global seq_line
    with open(os.path.join(json_dir, rico_index + '.json'), 'r') as f:
        root_json = json.load(f)

    # 去除冗余的外层嵌套
    while 'children' in root_json and len(root_json['children']) == 1:
        root_json = root_json['children'][0]

    # 用于裁剪的屏幕截图
    im_screenshot = Image.open(os.path.join(rico_dir, rico_index + '.jpg')) if CROP_WIDGET else None  # 可能为空
    # img_sha1 = hash_file_sha1(screenshot_path)  # 生成文件的 sha1 值

    # 空白草图画布
    im_sketch = Image.new('RGB', (SKETCH_WIDTH, SKETCH_HEIGHT), (255, 255, 255))
    out_sketch_path = os.path.join(sketches_dir, rico_index + '.png')

    removable_widgets = set()  # 待删除节点用集合表示
    nodes_dict = {}
    tree_root = Node(KEY_TREE_ROOT)

    args = {KEY_ANCESTOR_CLICKABLE: False}
    ancestor_clickable_stack = [False]  # 用于逐层存放 parent-clickable 属性
    csv_rows = []  # 分析模式生成 csv 文件
    tokens = []

    # 根据 rico json 文件构造树结构
    dfs_create_tree(root_json, args, ancestor_clickable_stack, tree_root, nodes_dict, rico_index)

    if PRINT_LOG:
        for pre, fill, node in RenderTree(tree_root):
            if node.name != 'tree_root':
                print("%s%s %s" % (pre, nodes_dict[node.name].w_type.name, nodes_dict[node.name].w_id))

    # 扫描去除大背景、面积过小的控件
    if len(tree_root.children) > 0:
        dfs_process_invalid_nodes(tree_root.children[0], nodes_dict)

    # 处理控件遮盖情形，并记录待清除元素到 removable_widgets
    if len(tree_root.children) > 0:
        dfs_process_overlapped_widgets(tree_root.children[0], nodes_dict, removable_widgets)

    # 扫描去除被遮盖的元素
    if len(tree_root.children) > 0:
        dfs_remove_covered_widgets(tree_root.children[0], removable_widgets)

    # 迭代执行多次清理/压缩树结构
    for i in range(3):
        if len(tree_root.children) > 0:
            dfs_compress_tree(tree_root.children[0], 0, nodes_dict)
        if len(tree_root.children) > 0:
            dfs_remove_invalid_leaf(tree_root.children[0], nodes_dict)

    # 列表的相同子项仅保留一个
    if len(tree_root.children) > 0:
        dfs_remove_extra_list_items(tree_root.children[0], nodes_dict)

    # 绘制草图
    if len(tree_root.children) > 0:
        dfs_create_sketch(tree_root.children[0], nodes_dict, im_screenshot, im_sketch, rico_index, csv_rows)

    # 生成 tokens 序列
    if len(tree_root.children) > 0:
        dfs_make_tokens(tree_root.children[0], tokens, nodes_dict)

    # 保存草图/制作训练文件
    if TRAINING_DATA_MODE:
        im_sketch.rotate(90, expand=1).save(out_sketch_path)
        open(seq_file, 'a').write(' '.join(tokens) + '\n')
        open(i2l_map_file, 'a').write(str(rico_index) + ' ' + str(seq_line) + '\n')
        seq_line += 1
    else:
        im_sketch.save(out_sketch_path)

    if ANALYSIS_MODE:
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(csv_rows)


def are_equivalent(root1, root2, nodes_dict):
    children1 = root1.children
    children2 = root2.children

    if len(children1) != len(children2):
        return False
    else:
        # 两者子节点数目相等
        type1 = nodes_dict[root1.name].w_type
        type2 = nodes_dict[root2.name].w_type
        if len(children1) == 0:
            return type1 == type2
        for i in range(len(children1)):
            if not are_equivalent(children1[i], children2[i], nodes_dict):
                return False
        return True


def dfs_remove_extra_list_items(tree_node, nodes_dict):
    """
    递归遍历树结构，对于 List 类型的节点判断其唯一的表项根节点，删除其他节点
    :param tree_node:
    :param nodes_dict:
    :return:
    """
    widget_type = nodes_dict[tree_node.name].w_type

    if widget_type == Widget.List:
        children = tree_node.children
        if 0 < len(children) < 3:
            tree_node.children = [children[0]]
        elif len(children) >= 3:
            cnt_equal_to_first = 0
            cnt_equal_to_second = 0
            for child in children:
                if are_equivalent(children[0], child, nodes_dict):
                    cnt_equal_to_first += 1
                if are_equivalent(children[1], child, nodes_dict):
                    cnt_equal_to_second += 1
            tree_node.children = [children[0]] if cnt_equal_to_first >= cnt_equal_to_second else [children[1]]
        return

    for child in tree_node.children:
        dfs_remove_extra_list_items(child, nodes_dict)


def dfs_remove_invalid_leaf(tree_node, nodes_dict):
    """
    清理 Rico 数据集中孤立 Layout/List/Unclassified 节点
    :param tree_node: 树节点
    :param nodes_dict: node_sha1: WidgetNode 字典
    :return:
    """
    widget_type = nodes_dict[tree_node.name].w_type

    # 消除不含子节点的 layout/list 或未分类节点
    if (widget_type == Widget.Layout or widget_type == Widget.List) and len(tree_node.children) == 0 or \
            widget_type == Widget.Unclassified:
        tree_node.parent = None
    for child in tree_node.children:
        dfs_remove_invalid_leaf(child, nodes_dict)


def dfs_compress_tree(tree_node, idx, nodes_dict):
    """
    压缩树的深度（递归地合并单孩子节点）
    :param tree_node: 树节点
    :param idx: tree_node 在其父节点的孩子节点中的序号
    :param nodes_dict: node_sha1: WidgetNode 字典
    :return:
    """
    widget_type = nodes_dict[tree_node.name].w_type
    node_parent = tree_node.parent

    # 消除 Layout { Layout { ... } } 及 Layout { Layout { Layout { ... } } }
    if widget_type == Widget.Layout and len(tree_node.children) == 1:
        # prev_node 的作用是避免过度压缩导致叶子控件平层
        # prev_node = tree_node
        alt_node = tree_node.children[0]
        while nodes_dict[tree_node.name].w_type == Widget.Layout and len(alt_node.children) == 1:
            # prev_node = alt_node
            alt_node = alt_node.children[0]
        node_parent.children = node_parent.children[:idx] + (alt_node,) + node_parent.children[idx + 1:]
        # node_parent.children = node_parent.children[:idx] + (prev_node,) + node_parent.children[idx + 1:]
        tree_node = alt_node

    # 消除 List { List { ... } }
    if widget_type == Widget.List and len(tree_node.children) == 1:
        child_node = tree_node.children[0]
        if nodes_dict[child_node.name].w_type == Widget.List:
            node_parent.children = node_parent.children[:idx] + (child_node,) + node_parent.children[idx + 1:]

    for i, child in enumerate(tree_node.children):
        dfs_compress_tree(child, i, nodes_dict)


def dfs_make_tokens(tree_node, tokens, nodes_dict):
    """
    生成 tokens 序列保存在 tokens 中
    :param tree_node: 树节点
    :param tokens: 待添加的 tokens 序列
    :param nodes_dict: node_sha1: WidgetNode 字典
    :return:
    """
    tokens.append(nodes_dict[tree_node.name].w_type.name)
    if len(tree_node.children) > 0:
        tokens.append('{')
        for child in tree_node.children:
            dfs_make_tokens(child, tokens, nodes_dict)
        tokens.append('}')


def infer_widget_type_from_std_class(string):
    """
    判断官方组件类名 string 中对应的控件类型
    :param string: 官方组件类名
    :return: 推测控件类型
    """
    if 'Toolbar' in string:
        return Widget.Toolbar
    if 'ListView' in string or 'RecyclerView' in string:
        return Widget.List
    if 'Layout' in string or string == 'android.view.ViewGroup':
        return Widget.Layout
    if string in ['android.widget.ToggleButton', 'android.widget.Switch',
                  'androidx.appcompat.widget.SwitchCompat', 'android.support.v7.widget.SwitchCompat']:
        return Widget.Switch
    if string == 'android.widget.RadioButton':
        return Widget.RadioButton
    if 'Button' in string:
        return Widget.Button
    if 'CheckBox' in string or 'CheckedTextView' in string:
        return Widget.CheckBox
    if 'ImageView' in string:
        return Widget.ImageView
    if 'AutoCompleteTextView' in string or 'EditText' in string:
        return Widget.EditText
    if 'TextView' in string:
        return Widget.TextView
    return Widget.Unclassified


def is_std_class(clz):
    return clz.startswith("android.widget") or clz == 'android.view.View' or clz == 'android.view.ViewGroup' or \
           clz in ['android.support.v7.widget.Toolbar', 'androidx.appcompat.widget.Toolbar',
                   'android.support.v7.widget.RecyclerView', 'androidx.recyclerview.widget.RecyclerView',
                   'androidx.appcompat.widget.SwitchCompat', 'android.support.v7.widget.SwitchCompat']


def get_std_class_name(clazz, ancestors):
    """
    获取继承树上的首个官方组件（待添加更多不以 android.widget 开头的确定类型的组件）
    :param clazz: 控件类名
    :param ancestors: 控件祖先列表
    :return: 首个官方组件类名和所在层次
    """
    if is_std_class(clazz):
        return clazz, 0
    for i, ancestor in enumerate(ancestors):
        if is_std_class(ancestor):
            return ancestor, i + 1
    return 'None', 'None'


def append_csv_row(node_sha1, json_obj, widget_type, rico_index, ancestor_clickable, csv_rows):
    if True:
        # if widget_type != Widget.Layout and widget_type != Widget.Unclassified and 'children' not in json_obj:
        std_clz_name, level = get_std_class_name(json_obj['class'], json_obj['ancestors'])
        csv_row = []
        for col_title in COLUMN_TITLES:
            if col_title == 'sha1':
                csv_row.append(node_sha1)
            elif col_title == 'rico-index':
                csv_row.append(rico_index)
            elif col_title == 'first-official-class':
                csv_row.append(std_clz_name)
            elif col_title == 'level':
                csv_row.append(level)
            elif col_title == 'parent-clickable':
                csv_row.append(ancestor_clickable)
            elif col_title == 'resource-id' or col_title == 'package':
                csv_row.append(json_obj[col_title] if 'resource-id' in json_obj else 'None')
            else:
                csv_row.append(json_obj[col_title])

        csv_rows.append(csv_row)


def dfs_create_tree(json_obj, args, ancestor_clickable_stack, parent_node, nodes_dict, rico_index):
    """
    递归创建 anytree 树结构，将 json_obj 所指节点挂在树节点 parent_node 上；在方法内判断 json_obj 所指节点的控件类型
    :param json_obj: 当前 json 对象
    :param args: 传递的参数用于控件类型判断
    :param ancestor_clickable_stack: 用于保存隔层传递的 clickable 参数的栈
    :param parent_node: 当前控件在树上的父节点
    :param nodes_dict: node_sha1: WidgetNode 字典
    :param rico_index: Rico 序号
    :return:
    """
    widget_type = infer_widget_type(json_obj['class'], json_obj['ancestors'],
                                    json_obj['resource-id'] if 'resource-id' in json_obj else None,
                                    'children' in json_obj, json_obj['clickable'], json_obj['bounds'], args)
    # 有 children 节点的 Unclassified 控件修改为 Layout
    if widget_type == Widget.Unclassified and 'children' in json_obj or \
            widget_type == Widget.List and json_obj['bounds'][3] - json_obj['bounds'][1] < 600:
        widget_type = Widget.Layout

    node_sha1 = hashlib.sha1(str(json_obj).encode('utf-8')).hexdigest()
    tree_node_key = node_sha1[:LEN_SHA1]
    tree_node = Node(tree_node_key, parent=parent_node)

    widget_node = WidgetNode(widget_type, json_obj, json_obj['resource-id'] if 'resource-id' in json_obj else None,
                             json_obj['class'], json_obj['bounds'], args[KEY_ANCESTOR_CLICKABLE])
    nodes_dict[tree_node_key] = widget_node

    # 传递参数：如果外层 layout/list 的 clickable 属性为真，则传递该参数用于后续类型判断（递归传递）
    if widget_type == Widget.Layout or widget_type == Widget.List:
        ancestor_clickable_stack.append(json_obj['clickable'] or args[KEY_ANCESTOR_CLICKABLE])
        args[KEY_ANCESTOR_CLICKABLE] = ancestor_clickable_stack[-1]

    w = max(0, json_obj['bounds'][2] - json_obj['bounds'][0]) + 1
    h = max(0, json_obj['bounds'][3] - json_obj['bounds'][1]) + 1

    id_str = json_obj['resource-id'].lower() if 'resource-id' in json_obj else None

    # 判断抽屉控件（不为抽屉生成草图）
    is_drawer = 'NavigationView' in json_obj['class'] or 'NavigationMenu' in json_obj['class'] \
                or (widget_type == Widget.Layout or widget_type == Widget.List) and id_str is not None \
                and ('drawer' in id_str or 'slider_layout' in id_str or 'nav_layout' in id_str
                     or 'navigation_layout' in id_str or 'menulayout' in id_str) and 1.8 < h / w < 5 or \
                widget_type == Widget.List and json_obj['bounds'][0] < 50 and 800 <= json_obj['bounds'][2] <= 1200

    # 排除不需递归执行的情形（是 layout/list 且有 'children' 节点且非抽屉）
    if 'children' in json_obj and (widget_type == Widget.Layout or widget_type == Widget.List) and not is_drawer:
        len_children = len(json_obj['children'])
        midpoints = []
        if len_children > 1:
            mp_x = np.zeros(len_children)
            mp_y = np.zeros(len_children)
            for i in range(len_children):
                bounds = json_obj['children'][i]['bounds']
                mp_x[i] = (bounds[0] + bounds[2]) / 2
                mp_y[i] = (bounds[1] + bounds[3]) / 2
                midpoints.append((i, mp_x[i], mp_y[i]))

            if np.std(mp_x) > np.std(mp_y):
                sorted_child_midpoint = sorted(midpoints, key=operator.itemgetter(1, 2))
            else:
                sorted_child_midpoint = sorted(midpoints, key=operator.itemgetter(2, 1))

            for i in range(len_children):
                child_json_obj = json_obj['children'][sorted_child_midpoint[i][0]]
                dfs_create_tree(child_json_obj, args, ancestor_clickable_stack, tree_node, nodes_dict, rico_index)
        elif len_children == 1:
            dfs_create_tree(json_obj['children'][0], args, ancestor_clickable_stack, tree_node, nodes_dict, rico_index)

    # 清除传递的参数
    if widget_type == Widget.Layout:
        args[KEY_ANCESTOR_CLICKABLE] = ancestor_clickable_stack.pop()


def dfs_process_invalid_nodes(tree_node, nodes_dict):
    """
    在刚开始分析 XML 时从树上删除孤立 Layout/Unclassified 节点、面积过小的控件、面积过大的叶子控件
    :param tree_node:
    :param nodes_dict:
    :return:
    """
    widget_node = nodes_dict[tree_node.name]
    widget_type = widget_node.w_type
    widget_bounds = widget_node.w_bounds
    w = max(0, widget_bounds[2] - widget_bounds[0]) + 1
    h = max(0, widget_bounds[3] - widget_bounds[1]) + 1

    if (widget_type == Widget.Layout or widget_type == Widget.Unclassified or widget_type == Widget.List) and \
            len(tree_node.children) == 0 or w <= 40 or h <= 50 or widget_type == Widget.TextView and w <= 80 or \
            (w * h) / (WIDTH * HEIGHT) > 0.8 and widget_type != Widget.Layout and widget_type != Widget.List:
        tree_node.parent = None
    else:
        for child in tree_node.children:
            dfs_process_invalid_nodes(child, nodes_dict)


def dfs_process_overlapped_widgets(tree_node, nodes_dict, removable_widgets):
    """
    处理控件重叠情况，遍历完成后确定不需绘制的控件，将其加入到 removable_widgets
    :param tree_node: 树节点
    :param nodes_dict: 节点字典
    :param removable_widgets: 不需绘制的控件 sha1 值（方法最终返回后统一删除）
    :return:
    """
    widget_node = nodes_dict[tree_node.name]

    widget_type = widget_node.w_type
    widget_bounds = widget_node.w_bounds
    tree_node_area = (max(0, widget_bounds[2] - widget_bounds[0]) + 1) * (
            max(0, widget_bounds[3] - widget_bounds[1]) + 1)

    if widget_type != Widget.Layout and widget_type != Widget.Unclassified and widget_type != Widget.List:
        most_covered_widgets = set()  # 大部分被遮盖的控件
        part_covered_widgets = set()  # 部分被遮盖的控件
        identical_widgets = set()  # 完全重叠的控件

        for sha, node in nodes_dict.items():
            if sha != tree_node.name and node.w_type != Widget.Layout and node.w_type != Widget.Unclassified and node.w_type != Widget.List:
                node_bounds = node.w_bounds
                dict_node_area = (max(0, node_bounds[2] - node_bounds[0]) + 1) * (
                        max(0, node_bounds[3] - node_bounds[1]) + 1)
                # 不判断面积很大的控件、也可加入面积过小的判断
                if dict_node_area < 1000000:
                    xia = max(widget_bounds[0], node_bounds[0])
                    yia = max(widget_bounds[1], node_bounds[1])
                    xib = min(widget_bounds[2], node_bounds[2])
                    yib = min(widget_bounds[3], node_bounds[3])
                    intersection_area = max(0, xib - xia + 1) * max(0, yib - yia + 1)
                    union_area = tree_node_area + dict_node_area - intersection_area
                    # 回避相同位置重叠多个相同控件的情形
                    if intersection_area / dict_node_area > 0.95 and intersection_area / union_area < 0.99:  # 该控件绝大部分被当前控件覆盖
                        most_covered_widgets.add(sha)
                    elif 0.01 < intersection_area / union_area < 0.99:  # 该控件并未被完全覆盖但与当前控件有交叠
                        part_covered_widgets.add(sha)
                    elif intersection_area / union_area == 1.00:
                        identical_widgets.add(sha)

        # if len(most_covered_widgets) >= 4 or len(most_covered_widgets) > 1 and len(most_covered_widgets) > 3:
        if len(most_covered_widgets) >= 3:  # 覆盖很多其他控件的控件如背景图片
            tree_node.parent = None
        elif 0 < len(most_covered_widgets) < 3:  # 如果覆盖 1~2 个则保留该控件但删去被覆盖控件和有交叠的控件
            removable_widgets.update(most_covered_widgets)
            removable_widgets.update(part_covered_widgets)
        elif len(most_covered_widgets) == 0:
            # if len(part_covered_widgets) > 5:
            #     to_remove_widgets.extend(part_covered_widgets)
            pass

        if len(identical_widgets) > 0 and tree_node.name not in removable_widgets:
            removable_widgets.update(identical_widgets)

    for child in tree_node.children:
        dfs_process_overlapped_widgets(child, nodes_dict, removable_widgets)


def dfs_remove_covered_widgets(tree_node, removable_widgets):
    """
    递归删除 sha1 值在 removable_widgets 列表中的控件
    :param tree_node: 当前树节点
    :param removable_widgets: 待删除控件 sha1 值列表
    :return:
    """
    if tree_node.name in removable_widgets:
        tree_node.parent = None
    else:
        for child in tree_node.children:
            dfs_remove_covered_widgets(child, removable_widgets)


def dfs_create_sketch(tree_node, nodes_dict, im_screenshot, im_sketch, rico_index, csv_rows):
    """
    递归绘制草图
    :param tree_node: 当前树节点
    :param nodes_dict: node_sha1: WidgetNode 字典
    :param im_screenshot: 用于裁剪控件的屏幕截图 Pillow 对象
    :param im_sketch: 用于绘制草图的 Pillow 对象
    :param rico_index: Rico 序号
    :return:
    """
    widget_node = nodes_dict[tree_node.name]

    widget_type = widget_node.w_type
    widget_bounds = widget_node.w_bounds
    widget_id = widget_node.w_id
    widget_class = widget_node.w_class

    if widget_type != Widget.Layout:
        if CROP_WIDGET:
            crop_widget(im_screenshot, rico_index, widget_type, widget_bounds, widget_id, widget_class, tree_node.name)
        if widget_type != Widget.Unclassified:
            draw_widget(im_sketch, widget_type, widget_bounds)

    if ANALYSIS_MODE:
        append_csv_row(tree_node.name, widget_node.w_json, widget_type, rico_index,
                       widget_node.w_ancestor_clickable, csv_rows)

    for child in tree_node.children:
        dfs_create_sketch(child, nodes_dict, im_screenshot, im_sketch, rico_index, csv_rows)


def crop_widget(im_screenshot, rico_index, widget_type, widget_bounds, widget_id, widget_class, node_sha1):
    """
    裁剪控件并保存到指定路径
    :param im_screenshot: 屏幕截图的 Pillow 对象
    :param rico_index: Rico 序号
    :param widget_type: 控件的推断类型
    :param widget_bounds: 控件 bounds
    :param widget_id: 控件 id
    :param widget_class: 控件类名
    :param node_sha1: 控件 sha1 值
    :return:
    """
    jpg_bounds = (int(widget_bounds[0] / WIDTH * im_screenshot.size[0]),
                  int(widget_bounds[1] / HEIGHT * im_screenshot.size[1]),
                  int(widget_bounds[2] / WIDTH * im_screenshot.size[0]),
                  int(widget_bounds[3] / HEIGHT * im_screenshot.size[1]))

    # class_tokens = widget_class.rsplit('.', 1)
    # file_name = [rico_index, '-', class_tokens[1] if len(class_tokens) > 1 else widget_class, '-', node_sha1]
    # if widget_id is not None:
    #     file_name.append('-')
    #     file_name.append(widget_id.split('/')[-1])
    # file_name.append('.jpg')
    # outfile_path = os.path.join(WIDGET_CUT_OUT_PATH, widget_type.name, ''.join(file_name))

    file_name = node_sha1 + '.jpg'
    outfile_path = os.path.join(WIDGET_CUT_OUT_PATH, file_name)

    im_screenshot.crop(jpg_bounds).save(outfile_path)


def infer_widget_type(cn, ancestors, id, has_children, clickable, bounds, args):
    """
    接收json节点，返回关键词匹配后根据规则推断的控件类型
    :param cn: 类名
    :param ancestors: 祖先列表
    :param id: 控件id
    :param has_children: 是否有子孙
    :param clickable: clickable 属性
    :param bounds: 范围
    :param args: 隔层传递的属性值
    :return: 推断的控件类型结果
    """
    # 执行这些规则后，返回最终推断类型；规则的先后顺序对结果有影响。

    # 次序1：官方控件中的特殊情况
    # if 'ActionMenuItemView' in cn or 'AppCompatImageButton' in cn:
    #     # print(cn, ancestors)
    #     return Widget.Button

    # 次序2：其他特殊情况
    # if not has_children and (id is not None and ('btn' in id or 'button' in id)):
    #     print(cn, ancestors)
    #     return Widget.Button

    android_std_cn, _ = get_std_class_name(cn, ancestors)
    widget_type = infer_widget_type_from_std_class(android_std_cn)

    if 'android.view.ViewGroup' not in ancestors:
        widgets_count[android_std_cn] = 1 if android_std_cn not in widgets_count else widgets_count[android_std_cn] + 1
    else:
        container_cnt[android_std_cn] = 1 if android_std_cn not in container_cnt else container_cnt[android_std_cn] + 1

    if widget_type == Widget.Unclassified:
        if 'android.widget.AbsListView' in ancestors:
            return Widget.List
        if 'android.view.ViewGroup' in ancestors:
            return Widget.Layout

    # if widget_type == Widget.Unclassified and cn != 'android.view.View' and android_std_cn != 'android.view.View' and
    #         cn not in std_class_map:
    #     std_class_map[cn] = ancestors

    # # 次序2：判断class_name是否存在明确的控件类型标识
    # widget_type = infer_widget_type_from_string(cn)

    # 不再考虑 TextLink 类型
    # 到此为止的Button不区分图形、文字。名称中不含Image的图形按钮也会被认为是Button
    # 如果button属性是文字类型，将其统一成TextLink
    # if widget_type == Widget.Button:
    #     for ancestor in ancestors:
    #         if 'TextView' in ancestor:
    #             widget_type = Widget.TextLink
    #             break

    # 次序3：判断未明确分类节点的任何一个祖先是否存在明确标识(解决祖先内的判断问题)
    # if widget_type == Widget.Unclassified:
    #     for ancestor in ancestors:
    #         widget_type = infer_widget_type_from_std_class(ancestor)
    #         if widget_type != Widget.Unclassified:
    #             break

    # 不再考虑 TextLink 类型
    # 次序4：确定嵌套在layout内部属性不可点击但实际行为可点击情况
    # if widget_type == Widget.TextView and (clickable or args[KEY_ANCESTOR_CLICKABLE]):
    #     widget_type = Widget.TextLink

    if widget_type == Widget.ImageView and (clickable or args[KEY_ANCESTOR_CLICKABLE]):
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        # 将面积较大的图转换成 ImageLink
        # FIXME 需要确定面积阈值
        widget_type = Widget.ImageView if w > 200 and h > 200 else Widget.Button  # ImageLink 仅出现在这种情形
    if PRINT_LOG:
        print(cn, ancestors, id, widget_type.name)
    return widget_type


def get_margin_scale(w, h):
    if w < 10:
        x_scale = 0
    elif w < 25:
        x_scale = 1
    elif w < 40:
        x_scale = 2
    elif w < 70:
        x_scale = 3
    elif w < 90:
        x_scale = 5
    elif w < 120:
        x_scale = 7
    elif w < 150:
        x_scale = 9
    elif w < 180:
        x_scale = 11
    elif w < 210:
        x_scale = 13
    elif w < 240:
        x_scale = 15
    elif w < 270:
        x_scale = 17
    else:
        x_scale = 19

    if h < 30:
        y_scale = 1
    elif h < 60:
        y_scale = 2
    elif h < 100:
        y_scale = 3
    elif h < 150:
        y_scale = 5
    elif h < 180:
        y_scale = 6
    elif h < 210:
        y_scale = 8
    elif h < 240:
        y_scale = 10
    elif h < 270:
        y_scale = 12
    else:
        y_scale = 14

    return x_scale, y_scale


def draw_widget(im, widget_type, bounds):
    """
    在im对象中绘制范围为bounds的控件草图
    :param im: 待绘制的图片对象
    :param widget_type: 待绘制的控件类型
    :param bounds: 待绘制的控件范围
    :return:
    """

    bounds_sketch = (int((bounds[0]) / WIDTH * SKETCH_WIDTH), int((bounds[1]) / HEIGHT * SKETCH_HEIGHT),
                     int((bounds[2]) / WIDTH * SKETCH_WIDTH), int((bounds[3]) / HEIGHT * SKETCH_HEIGHT))

    w = bounds_sketch[2] - bounds_sketch[0] + 1
    h = bounds_sketch[3] - bounds_sketch[1] + 1

    if widget_type == Widget.List:
        x_scale, y_scale = 2, 2
    else:
        x_scale, y_scale = get_margin_scale(w, h)

    # 将长宽按比例缩小到画布上后确定草图元素缩放范围
    bounds_inner = (bounds_sketch[0] + x_scale, bounds_sketch[1] + y_scale,
                    bounds_sketch[2] - x_scale, bounds_sketch[3] - y_scale)

    if IMG_MODE == 'color':
        draw_colored_image(im, widget_type, bounds_inner)

    elif IMG_MODE == 'sketch':
        raise Exception("Unsupported sketch mode.")
        # im.paste(im=WidgetColor.BLACK_RGB, box=(
        #     bounds_sketch[0] + WIDGET_FRAME_MARGIN, bounds_sketch[1] + WIDGET_FRAME_MARGIN,
        #     bounds_sketch[2] - WIDGET_FRAME_MARGIN, bounds_sketch[3] - WIDGET_FRAME_MARGIN))
        # if widget_type == Widget.Button:
        #     im.paste(WidgetSketch.IM_BUTTON.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.ImageView:
        #     im.paste(WidgetSketch.IM_IMAGE_VIEW.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.EditText:
        #     im.paste(WidgetSketch.IM_EDIT_TEXT.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.TextView:
        #     im.paste(WidgetSketch.IM_TEXT_VIEW.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.CheckBox:
        #     im.paste(WidgetSketch.IM_CHECK_BOX.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.ImageLink:
        #     im.paste(WidgetSketch.IM_IMAGE_LINK.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))
        # elif widget_type == Widget.TextLink:
        #     im.paste(WidgetSketch.IM_TEXT_LINK.resize((w, h)), box=(bounds_inner[0], bounds_inner[1]))


def draw_colored_image(im, widget_type, bounds):
    """
    在 Image 对象上绘制与控件类型对应的彩色图
    :param im: Image 对象
    :param widget_type: 控件类型（据此绘制颜色不同的色块）
    :param bounds: 实际绘制到 im 上的坐标值
    :return:
    """
    if widget_type == Widget.Button:
        im.paste(im=WidgetColor.BLUE_RGB, box=bounds)
    elif widget_type == Widget.TextView:
        im.paste(im=WidgetColor.BLACK_RGB, box=bounds)
    # elif widget_type == Widget.TextLink:
    #     im.paste(im=WidgetColor.NAVY_RGB, box=bounds)
    elif widget_type == Widget.EditText:
        im.paste(im=WidgetColor.LIME_RGB, box=bounds)
    elif widget_type == Widget.ImageView:
        im.paste(im=WidgetColor.RED_RGB, box=bounds)
    # elif widget_type == Widget.ImageLink:
    #     im.paste(im=WidgetColor.MAROON_RGB, box=bounds)
    elif widget_type == Widget.CheckBox:
        im.paste(im=WidgetColor.MAGENTA_RGB, box=bounds)
    elif widget_type == Widget.Switch:
        im.paste(im=WidgetColor.CYAN_RGB, box=bounds)
    elif widget_type == Widget.RadioButton:
        im.paste(im=WidgetColor.YELLOW_RGB, box=bounds)
    elif widget_type == Widget.Toolbar:
        im.paste(im=WidgetColor.GREEN_RGB, box=bounds)
    elif widget_type == Widget.List:
        im.paste(im=WidgetColor.GRAY_RGB, box=bounds)


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


if __name__ == '__main__':

    start_time = time.time()
    print('---------------------------------')
    print('### Cleaned json files location:', cleaned_jsons_dir)

    print('### Checking directories to save generated sketches:', colored_pics_divided_dir, '...', end=' ')
    check_make_dir(colored_pics_divided_dir)
    print('OK')

    # 初始化放置控件裁切的位置
    if CROP_WIDGET:
        print('### Directories to save widget crops:', WIDGET_CUT_OUT_PATH)
        # for widget in Widget:
        #     dir_path = os.path.join(WIDGET_CUT_OUT_PATH, widget.name)
        #     if os.path.exists(dir_path):
        #         shutil.rmtree(dir_path)
        #     os.makedirs(dir_path)
        if os.path.exists(WIDGET_CUT_OUT_PATH):
            shutil.rmtree(WIDGET_CUT_OUT_PATH)
        os.makedirs(WIDGET_CUT_OUT_PATH)

    if TRAINING_DATA_MODE:
        # 先创建/覆盖文件用于添加内容
        check_make_dir(data_dir)
        print('### Checking data directory to save training related files:', data_dir, '... OK')

        open(layout_sequences_fp, 'w', newline='')
        open(index_map_fp, 'w', newline='')
        print('### Creating training related files ... OK')

    if ANALYSIS_MODE:
        with open(CSV_FILE_PATH, 'w', newline='') as f:
            csv.writer(f).writerow(COLUMN_TITLES)

    for case_name in os.listdir(rico_divided_dir):
        if not case_name.startswith('.'):  # hidden files
            input_case_dir = os.path.join(cleaned_jsons_dir, case_name)
            output_case_dir = os.path.join(colored_pics_divided_dir, case_name)
            print('[' + datetime.now().strftime('%m-%d %H:%M:%S') + '] >>> Processing', output_case_dir, '...', end=' ')

            check_make_dir(output_case_dir)
            for file in os.listdir(input_case_dir):
                if file.endswith('.json'):
                    sketch_samples_generation(os.path.join(rico_divided_dir, case_name),
                                              os.path.join(cleaned_jsons_dir, case_name),
                                              os.path.join(colored_pics_divided_dir, case_name),
                                              file.split('.')[0], layout_sequences_fp, index_map_fp)
            print('OK')

    print('<<< Generated sketches saved in', colored_pics_divided_dir)

    if CROP_WIDGET:
        print('<<< Cropped widget images saved in', WIDGET_CUT_OUT_PATH)
    if ANALYSIS_MODE:
        print('<<< Analysis csv file saved in ', CSV_FILE_PATH)

    sorted_map = sorted(widgets_count.items(), key=operator.itemgetter(1), reverse=True)
    cnt_sum = 0
    for i, (key, value) in enumerate(sorted_map):
        print(i + 1, key, value)
        cnt_sum += value
    print('Total widget counts:', cnt_sum)

    sorted_map = sorted(container_cnt.items(), key=operator.itemgetter(1), reverse=True)
    cnt_sum = 0
    for i, (key, value) in enumerate(sorted_map):
        print(i + 1, key, value)
        cnt_sum += value
    print('Total container counts:', cnt_sum)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
