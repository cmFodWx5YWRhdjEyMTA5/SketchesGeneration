try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import json
import operator
import os

from sketch.widget import Widget


# 深度优先遍历并添加 index
def dfs_add_index(json_obj, cnt_map):
    cnt_map[json_obj['type']].append(json_obj['index'])
    if 'children' not in json_obj:
        return
    for c in json_obj['children']:
        dfs_add_index(c, cnt_map)


# 获得根节点为索引 index 的子图
def get_subgraph(json_tree, index):
    if json_tree['index'] == index:
        return json_tree
    if 'children' in json_tree:
        for c in json_tree['children']:
            result = get_subgraph(c, index)
            if result is not None:
                return result
    return None


# 易读格式中的控件遍历序号
def get_component_cnt_index_map(json_obj):
    cnt_map = {}
    for name, widget in Widget.__members__.items():
        cnt_map[widget] = []
    dfs_add_index(json_obj, cnt_map)
    return cnt_map


# 计算得分
def cal_score(root1, root2):
    score = 0
    num_common_comp = 0
    queue1 = [root1]
    queue2 = [root2]
    while len(queue1) > 0 and len(queue2) > 0:
        comp_1 = queue1.pop(0)
        comp_2 = queue2.pop(0)

        # 类型相同的控件
        if comp_1['type'] == comp_2['type']:
            num_common_comp = num_common_comp + 1

        if 'children' in comp_1:
            for c in comp_1['children']:
                queue1.append(c)
        if 'children' in comp_2:
            for c in comp_2['children']:
                queue2.append(c)

        # 子控件数目不一致扣分
        if 'children' in comp_1 and 'children' in comp_2:
            score -= abs(len(comp_1['children']) - len(comp_2['children'])) * 5

    return score + num_common_comp * 10


# 对每个子图计算得分，并计算分值最大数
def cal_highest_score(middle_file_1, middle_file_2):
    with open(middle_file_1, 'r') as f:
        json_obj_1 = json.load(f)
    comp_cnt_map_1 = get_component_cnt_index_map(json_obj_1)

    with open(middle_file_2, 'r') as f:
        json_obj_2 = json.load(f)
    comp_cnt_map_2 = get_component_cnt_index_map(json_obj_2)

    scores = []
    num_matching = 0

    # 计算每个类型的控件出现次数
    for name, member in MiddleComponent.__members__.items():
        indices_1 = comp_cnt_map_1[str(member)]
        indices_2 = comp_cnt_map_2[str(member)]
        for i1 in indices_1:
            for i2 in indices_2:
                num_matching = num_matching + 1
                # print('## Pair ' + str(num_matching) + ': (' + str(i1) + ', ' + str(i2) + ')')
                subgraph_1 = get_subgraph(json_obj_1, i1)
                subgraph_2 = get_subgraph(json_obj_2, i2)
                # print('Sub graph 1 (' + str(i1) + '): ', subgraph_1)
                # print('Sub graph 2 (' + str(i2) + '): ', subgraph_2)
                score = cal_score(subgraph_1, subgraph_2)
                scores.append(score)
                # print('score = ' + str(score))

    print('# of matched pairs: ', num_matching)
    return max(scores) if scores else 0


# 计算两个中间结构的得分
def middle_structure_match(middle_file_1, middle_file_2):
    score = cal_highest_score(middle_file_1, middle_file_2)
    print('Score of ' + middle_file_1 + ' and ' + middle_file_2 + ':', score)
    return score


if __name__ == '__main__':
    layout_path = "./layout"
    output_path = "./output/brainly"

    print('##### Start processing ...')
    print("Generating Middle format of files in " + layout_path + " ...")

    if not os.path.exists(os.path.join(output_path)):
        os.makedirs(os.path.join(output_path))

    # 为 layout_path 中每个文件生成中间结构并存放在 output_path 中
    for file in os.listdir(layout_path):
        if file.endswith(".xml"):
            file_name = file.split('.')[0]
            middle_format_gen(os.path.join(layout_path, file),
                              os.path.join(output_path, file_name))
    # print(os.path.join(output_path, case_dir))

    print("Middle format of files created in " + output_path)

    # input_layout_path = os.path.join(output_path, "fragment_question.json")
    input_layout_path = './output/input_search_results.json'
    scores_dict = {}
    for file in os.listdir(output_path):
        if file.endswith('.m.json'):
            score = middle_structure_match(input_layout_path, os.path.join(output_path, file))
            scores_dict[file] = score

    sorted_scores = sorted(scores_dict.items(), key=operator.itemgetter(1))
    sorted_scores.reverse()
    print('=====> Most similar 20 layouts of ' + input_layout_path + ':', sorted_scores[:20])
    # for file in os.listdir(output_path):
    #     if file.endswith(".json"):
    #         file_name = file.split('.')[0]
    #         middle_structure_match(os.path.join(output_path, ""))
