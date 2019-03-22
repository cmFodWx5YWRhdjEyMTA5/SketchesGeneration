import operator
import os
import time

import networkx as nx
import numpy as np

from decomp.layout_utils import optimize_sequence, create_layout_tree, post_order_traversal, split_list_item_subtree
from sketch import config

# Layout = 0
# TextView = 1
# TextLink = 2
# EditText = 3
# ImageView = 4
# ImageLink = 5
# Button = 6
# RadioButton = 7
# Switch = 8
# CheckBox = 9
# Unclassified = 10
# List = 11
# Toolbar = 12


#           0  1  2  3  4  5  6  7  8  9  10 11 12
weights = [[5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 0],  # 0
           [0, 15, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 1
           [0, 5, 15, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0],  # 2
           [0, 0, 0, 60, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 3
           [0, 0, 0, 0, 20, 20, 5, 0, 0, 0, 0, 0, 0],  # 4
           [0, 0, 0, 0, 20, 20, 0, 0, 0, 0, 0, 0, 0],  # 5
           [0, 0, 5, 0, 5, 0, 25, 0, 0, 0, 0, 0, 0],  # 6
           [0, 0, 0, 0, 0, 0, 0, 60, 0, 0, 0, 0, 0],  # 7
           [0, 0, 0, 0, 0, 0, 0, 0, 60, 0, 0, 0, 0],  # 8
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 60, 0, 0, 0],  # 9
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 10
           [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 75, 0],  # 11
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20]]  # 12

dist_penalty = 5
num_children_penalty = 5


def max_score(nd1, post_order1, nd2, post_order2):
    """
    计算两棵布局树的最大匹配子图的值
    :param nd1: node dict for Layout tree 1
    :param post_order1: post order traversal sequence list for Layout tree 1
    :param nd2: node dict for Layout tree 2
    :param post_order2: post order traversal sequence list for Layout tree 2
    :param items_nd_dict: 保存供查询的所有表项的 nodes dict 的 map，key 为 文件名（可能为空）
    :return: 最大近似度分数
    """
    num_nodes1 = len(nd1)
    num_nodes2 = len(nd2)
    # print('seq 1 len: ' + str(num_nodes1) + ', seq 2 len: ' + str(num_nodes2))
    matrix = np.zeros((num_nodes1, num_nodes2, 2))

    for u in post_order1:
        u_children = nd1[u].tree_node.children
        for v in post_order2:
            v_children = nd2[v].tree_node.children

            m1a = max([matrix[int(c.name)][int(v)][0] for c in u_children]) if len(u_children) > 0 else 0
            m1b = max([matrix[int(c.name)][int(v)][1] for c in u_children]) if len(u_children) > 0 else 0
            m2a = max([matrix[int(u)][int(c.name)][0] for c in v_children]) if len(v_children) > 0 else 0
            m2b = max([matrix[int(u)][int(c.name)][1] for c in v_children]) if len(v_children) > 0 else 0

            matrix[int(u)][int(v)][1] = max(m1a, m1b, m2a, m2b) - dist_penalty

            bi_graph = nx.Graph()
            bi_graph.add_nodes_from([int(c.name) for c in u_children])
            bi_graph.add_nodes_from([int(c.name) + 1000 for c in v_children])

            max_weighted_match = 0
            children_mismatch_penalty = 0
            if len(u_children) > 0 and len(v_children) > 0:
                for uc in u_children:
                    for vc in v_children:
                        weight = max(matrix[int(uc.name)][int(vc.name)][1],
                                     matrix[int(uc.name)][int(vc.name)][0] + 0)
                        bi_graph.add_edge(int(uc.name), int(vc.name) + 1000, weight=weight)
                pairs = nx.max_weight_matching(bi_graph)
                max_weighted_match = sum([bi_graph[pair[0]][pair[1]]['weight'] for pair in pairs])

                # 加入惩罚机制。子节点数目不匹配的两个节点，按照子节点数目
                children_mismatch_penalty = abs(len(u_children) - len(v_children)) * num_children_penalty

            matrix[int(u)][int(v)][0] = weights[nd1[u].widget_type.value][nd2[v].widget_type.value] + \
                                        max_weighted_match - children_mismatch_penalty

    # print(matrix[:, :, 0].max())
    # node1_idx, node2_idx = unravel_index(matrix[:, :, 0].argmax(), matrix[:, :, 0].shape)
    # print(str(node1_idx) + ':', nd1[str(node1_idx)])
    # print(str(node2_idx) + ':', nd2[str(node2_idx)])

    # for r in matrix:
    #     for c in r:
    #         print(c[0], end=' ')
    #     print()

    return matrix[:, :, 0].max()


if __name__ == '__main__':
    start_time = time.time()
    print('---------------------------------')

    seq_dir = config.DIRECTORY_CONFIG['apk_sequences_dir']
    scores_map = {}

    seq_to_match = 'Layout { Layout { Button TextView } Layout { ImageView Layout { Layout { EditText EditText } Button } } }'

    # 建树，获得 node dict
    tree_root, nd1 = create_layout_tree(optimize_sequence(seq_to_match))

    item_roots = []
    split_list_item_subtree(tree_root, nd1, item_roots)

    post_order_main = post_order_traversal(tree_root)
    contains_list = len(item_roots) > 0

    # 新建变量代表待匹配 item 树根节点及其后序遍历，仅当 has_item 为真时有效
    item_root = None
    post_order_item = None

    self_score = max_score(nd1, post_order_main, nd1, post_order_main)

    if contains_list:
        # todo 目前只处理了所有表项的第一个
        item_root = item_roots[0]
        post_order_item = post_order_traversal(item_root)
        self_score += max_score(nd1, post_order_item, nd1, post_order_item)

    for file_name in os.listdir(seq_dir):
        if file_name.endswith('.lst'):
            with open(os.path.join(seq_dir, file_name), 'r') as f:

                # 新建变量代表当需要 item 匹配时记录当前最大近似的 item 文件名和分值
                max_match_item_self_score = 0
                max_match_item_score = 0
                max_match_item_simi_score = 0
                max_item_fname = None

                for line in f:
                    line_sp = line.split()
                    apk_package = line_sp[0]
                    file_type = int(line_sp[1])
                    file_name = line_sp[2]
                    tokens = line_sp[3:]
                    layout_id = apk_package + ':' + file_name

                    # 优化树结构
                    cfile_tree_root, cfile_nd = create_layout_tree(optimize_sequence(' '.join(tokens)))
                    cfile_pot = post_order_traversal(cfile_tree_root)

                    # 文件中 2(item) 总是放在 1(layout) 前面
                    if file_type == 2 and contains_list:
                        current_item_score = max_score(nd1, post_order_item, cfile_nd, cfile_pot)
                        item_self_score = max_score(cfile_nd, cfile_pot, cfile_nd, cfile_pot)
                        current_item_simi_score = current_item_score / item_self_score
                        if current_item_simi_score > max_match_item_simi_score:
                            max_match_item_self_score = item_self_score
                            max_match_item_score = current_item_score
                            max_match_item_simi_score = current_item_simi_score
                            max_item_fname = file_name

                    # 将每一行代表的 layout 所对应的近似得分保存到 map 中
                    if file_type == 1 and len(cfile_nd) < 200:
                        # 用 package name + main layout + item layout 作为索引
                        key_id = layout_id + '/' + max_item_fname if contains_list and max_item_fname is not None else layout_id
                        current_layout_self_score = max_score(cfile_nd, cfile_pot, cfile_nd, cfile_pot)
                        current_layout_score = max_score(nd1, post_order_main, cfile_nd, cfile_pot)

                        # 放到 map 中的是计算后的 "近似度得分" 绝对值计算的是惩罚
                        # scores_map[key_id] = (current_layout_score + max_match_item_score) - \
                        #                      abs(current_layout_self_score - current_layout_score) - \
                        #                      abs(max_match_item_score - max_match_item_self_score)
                        scores_map[key_id] = 2 * (current_layout_score + max_match_item_score) / \
                                             (self_score + current_layout_self_score + max_match_item_self_score)
                        print(key_id, current_layout_score, current_layout_self_score, max_match_item_score,
                              max_match_item_self_score, self_score)

    sorted_map = sorted(scores_map.items(), key=operator.itemgetter(1), reverse=True)

    print('---------------------------------')
    print('Matching results:')
    rank = 1
    for key, value in sorted_map[:30]:
        print(rank, key, '| similarity: %.2f' % (value * 100) + '%, score:', int(value))
        rank += 1

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
