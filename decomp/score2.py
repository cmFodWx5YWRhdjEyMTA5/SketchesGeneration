import networkx as nx
import numpy as np
from numpy import unravel_index

from sketch.layout_compressor import optimize_sequence, create_layout_tree, post_order_traversal

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


weights = [[10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
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


class MatchTreeNode(object):
    def __init__(self, idx, widget_type, children_idxes):
        self.idx = idx,
        self.widget_type = widget_type,
        self.children_idxes = children_idxes


if __name__ == '__main__':
    penalty = 1

    sequence1 = 'Layout { Layout { Button TextView Button } Layout { Layout { EditText EditText } Layout { Button Button } } }'
    tree1, nd1 = create_layout_tree(optimize_sequence(sequence1))
    post_order1 = post_order_traversal(tree1)

    sequence2 = 'Layout { Layout { Button TextView Button } Layout { Layout { EditText Button EditText Button } Layout { Button Button } } }'
    tree2, nd2 = create_layout_tree(optimize_sequence(sequence2))
    post_order2 = post_order_traversal(tree2)

    h = len(nd1)
    w = len(nd2)
    print(h, w)
    matrix = np.zeros((h, w, 2))

    for u in post_order1:
        u_children = nd1[u].tree_node.children
        for v in post_order2:
            v_children = nd2[v].tree_node.children

            m1a = max([matrix[int(c.name)][int(v)][0] for c in u_children]) if len(u_children) > 0 else 0
            m1b = max([matrix[int(c.name)][int(v)][1] for c in u_children]) if len(u_children) > 0 else 0
            m2a = max([matrix[int(u)][int(c.name)][0] for c in v_children]) if len(v_children) > 0 else 0
            m2b = max([matrix[int(u)][int(c.name)][1] for c in v_children]) if len(v_children) > 0 else 0

            matrix[int(u)][int(v)][1] = max(m1a, m1b, m2a, m2b) - penalty

            G = nx.Graph()
            G.add_nodes_from([int(c.name) for c in u_children])
            G.add_nodes_from([int(c.name) + 1000 for c in v_children])

            MWM = 0
            if len(u_children) > 0 and len(v_children) > 0:
                for uc in u_children:
                    for vc in v_children:
                        weight = max(matrix[int(uc.name)][int(vc.name)][1],
                                     matrix[int(uc.name)][int(vc.name)][0] + 0)
                        G.add_edge(int(uc.name), int(vc.name) + 1000, weight=weight)
                pairs = nx.max_weight_matching(G)
                MWM = sum([G[pair[0]][pair[1]]['weight'] for pair in pairs])

            matrix[int(u)][int(v)][0] = weights[nd1[u].widget_type.value][nd2[v].widget_type.value] + MWM

    print(unravel_index(matrix[:, :, 0].argmax(), matrix[:, :, 0].shape))

    for r in matrix:
        for c in r:
            print(c[0], end=' ')
        print()
