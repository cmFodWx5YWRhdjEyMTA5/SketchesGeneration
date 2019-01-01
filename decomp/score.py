import operator

import networkx as nx
import numpy as np
from numpy import unravel_index

from decomp.layout_compressor import optimize_sequence, create_layout_tree, post_order_traversal
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


weights = [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
           [0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 10, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0, 10, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 0],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

dist_penalty = 5
num_children_penalty = 5


def max_score(seq1, seq2):
    opt_seq1 = optimize_sequence(seq1)
    print(opt_seq1)
    tree1, nd1 = create_layout_tree(opt_seq1)
    post_order1 = post_order_traversal(tree1)

    opt_seq2 = optimize_sequence(seq2)
    print(opt_seq2)
    tree2, nd2 = create_layout_tree(opt_seq2)
    post_order2 = post_order_traversal(tree2)

    num_nodes1 = len(nd1)
    num_nodes2 = len(nd2)
    print('seq 1 len: ' + str(num_nodes1) + ', seq 2 len: ' + str(num_nodes2))
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
                children_mismatch_penalty = abs(len(u_children) - len(v_children)) * num_children_penalty

            matrix[int(u)][int(v)][0] = weights[nd1[u].widget_type.value][
                                            nd2[v].widget_type.value] + max_weighted_match - children_mismatch_penalty

    # print(matrix[:, :, 0].max())
    node1_idx, node2_idx = unravel_index(matrix[:, :, 0].argmax(), matrix[:, :, 0].shape)
    print(str(node1_idx) + ':', nd1[str(node1_idx)])
    print(str(node2_idx) + ':', nd2[str(node2_idx)])

    # for r in matrix:
    #     for c in r:
    #         print(c[0], end=' ')
    #     print()

    return matrix[:, :, 0].max()


if __name__ == '__main__':
    seq_fp = config.DIRECTORY_CONFIG['apk_sequences_file_path']
    scores_map = {}

    seq_to_match = 'Layout { Layout { Layout { Layout { Button Button Button } Layout { Layout { Button Button Button } Layout { Button Button Button } Layout { Button Button Button } } } Layout { Button Button Button Button Button } Layout { Button Button Button Button Button } } }'

    with open(seq_fp, 'r') as f:
        for line in f:
            line_sp = line.split()
            app = line_sp[0]
            activ_name = line_sp[1]
            tokens = line_sp[2:]
            print(activ_name)
            scores_map[activ_name] = max_score(seq_to_match, ' '.join(tokens))
    sorted_map = sorted(scores_map.items(), key=operator.itemgetter(1), reverse=True)
    print(sorted_map)
