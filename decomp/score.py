import operator
import os
import time
from configparser import ConfigParser

import networkx as nx
import numpy as np

from decomp.layout_utils import create_layout_tree, post_order_traversal, split_list_item_subtree, \
    dfs_make_tokens

cfg = ConfigParser()
cfg.read('../config.ini')

seq_dir = cfg.get('decode', 'apk_tokens_dir')

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
           [0, 0, 0, 0, 0, 0, 0, 75, 0, 0, 0, 0, 0],  # 7
           [0, 0, 0, 0, 0, 0, 0, 0, 75, 0, 0, 0, 0],  # 8
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 75, 0, 0, 0],  # 9
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 10
           [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0],  # 11
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15]]  # 12

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

    return matrix[:, :, 0].max()


def create_tree(sequence):
    """
    输出该序列的根节点（用于遍历）、节点字典、后序遍历（用于依次比较）
    :param sequence: 布局序列
    :return:
    """
    root, nd = create_layout_tree(sequence)
    post_order = post_order_traversal(root)
    return root, nd, post_order


def cal_simi_score(tree_root, nd, post_order):
    """
    将 layout_dir 中的每个文件中每个布局与输入的布局树进行比较，返回一个按相似度排序的有序字典
    :param tree_root: 待匹配布局树根节点
    :param nd: 待匹配布局树节点字典
    :param post_order: 待匹配布局树后序遍历
    :return: 按相似度排序的字典（key: layout id, value: similarity score）
    """
    scores_map = {}

    item_roots = []
    split_list_item_subtree(tree_root, nd, item_roots)
    tks_main = []
    tks_item = []

    dfs_make_tokens(tree_root.children[0], nd, tks_main)
    len_tks_main = len(tks_main)
    len_tks_item = 0
    print('Input: ' + str(tks_main), len_tks_main)
    print('Searching ...')

    contains_list = len(item_roots) > 0

    # 新建变量代表待匹配 item 树根节点及其后序遍历，仅当 contains_list 为真时有效
    post_order_item = None

    total_self_score_i = max_score(nd, post_order, nd, post_order)  # 自身得分/最大可能得分
    item_self_score_i = 0

    if contains_list:
        # todo 目前只处理了所有表项的第一个
        item_root = item_roots[0]
        post_order_item = post_order_traversal(item_root)
        item_self_score_i = max_score(nd, post_order_item, nd, post_order_item)
        total_self_score_i += item_self_score_i * 1.5
        dfs_make_tokens(item_root, nd, tks_item)
        len_tks_item = len(tks_item)
        print(tks_item, len_tks_item)

    for file_name in os.listdir(seq_dir):
        if file_name.endswith('.lst'):
            with open(os.path.join(seq_dir, file_name), 'r') as f:

                # 新建变量代表当需要 item 匹配时记录当前最大近似的 item 文件名和分值
                max_match_item_self_score = 0
                max_match_item_lawecse_score = 0
                max_match_item_simi_score = 0
                max_match_item_fname = None

                for i, line in enumerate(f):
                    package = str(file_name.split('-')[0])
                    line_sp = line.split()
                    layout_type = int(line_sp[0])
                    len_tks_c = int(line_sp[2])

                    if layout_type == 1:
                        if abs(
                                len_tks_c - len_tks_main) > 10 + len_tks_main / 3 or contains_list and 'List' not in tks_main:
                            # print('layout skipped')
                            continue

                    file_name = line_sp[1]
                    layout_id = package + ':' + file_name
                    tokens = line_sp[3:]

                    cfile_tree_root, cfile_nd, cfile_pot = create_tree(' '.join(tokens))

                    # 文件中 2(item) 总是放在 1(layout) 前面
                    if contains_list and layout_type == 2:
                        if abs(len_tks_c - len_tks_item) > 10:
                            # print('item skipped')
                            continue
                        item_lawecse_score_c = max_score(nd, post_order_item, cfile_nd, cfile_pot)
                        item_self_score_c = max_score(cfile_nd, cfile_pot, cfile_nd, cfile_pot)

                        item_simi_score_c = item_lawecse_score_c * item_lawecse_score_c / \
                                            item_self_score_c / item_self_score_i if item_self_score_c > 0 else 0

                        if item_simi_score_c > max_match_item_simi_score:
                            max_match_item_self_score = item_self_score_c
                            max_match_item_lawecse_score = item_lawecse_score_c
                            max_match_item_simi_score = item_simi_score_c
                            max_match_item_fname = file_name

                    # 将每一行代表的 layout 所对应的近似得分保存到 map 中
                    if layout_type == 1 and len(cfile_nd) < 200:
                        # 用 package name + main layout + item layout 作为索引
                        key_id = layout_id + '/' + max_match_item_fname if contains_list and max_match_item_fname is not None else layout_id
                        layout_self_score_c = max_score(cfile_nd, cfile_pot, cfile_nd, cfile_pot)
                        layout_lawecse_score_c = max_score(nd, post_order, cfile_nd, cfile_pot)

                        # 放到 map 中的是计算后的 "近似度得分"
                        total_lawecse_score = layout_lawecse_score_c + max_match_item_lawecse_score * 1.5
                        scores_map[key_id] = total_lawecse_score * total_lawecse_score / total_self_score_i / \
                                             (layout_self_score_c + max_match_item_self_score * 1.5)

                        # print(key_id, layout_lawecse_score_c, layout_self_score_c, max_match_item_lawecse_score,
                        #       max_match_item_self_score, total_self_score_i)

    return sorted(scores_map.items(), key=operator.itemgetter(1), reverse=True)


def search_similar_seq(seq):
    start_time = time.time()
    print('---------------------------------')

    tree_root, nd, post_order_main = create_tree(seq)
    sorted_map = cal_simi_score(tree_root, nd, post_order_main)

    print('---------------------------------')
    print('Matched results:')

    for i, (key, value) in enumerate(sorted_map[:30]):
        print(i + 1, key, '| %.2f' % (value * 100) + '%')

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))


if __name__ == '__main__':
    seq = 'replace_here'
    search_similar_seq(seq)

    # seq1 = 'Layout { Layout { EditText EditText TextView } Layout { Button Button } }'
    # seq2 = 'Layout { Layout { EditText EditText } Layout { Layout { Button Button } Layout { TextView Button } } }'
    # tree_root1, nd1, post_order_main1 = create_tree(seq1)
    # tree_root2, nd2, post_order_main2 = create_tree(seq2)
    # lawecse = max_score(nd1, post_order_main1, nd2, post_order_main2)
    # w1 = max_score(nd1, post_order_main1, nd1, post_order_main1)
    # w2 = max_score(nd2, post_order_main2, nd2, post_order_main2)
