from anytree import Node, RenderTree
from anytree.exporter import DotExporter

from sketch.widget import Widget, MatchTreeNode


def render_tree(tree_node, nodes_dict, pic_name=None):
    for pre, fill, node in RenderTree(tree_node):
        print("%s%s" % (pre, nodes_dict[node.name].widget_type.name))

    if pic_name is not None:
        DotExporter(tree_node).to_picture(pic_name)


def post_order_sweep(node, order):
    for child in node.children:
        post_order_sweep(child, order)
    order.append(node.name)


def post_order_traversal(root):
    post_order = []
    post_order_sweep(root, post_order)
    return post_order


def create_layout_tree(seq):
    """
    解析 DFS 序列 sequence 为树，返回根节点和字典 { idx(str): MatchTreeNode(WidgetType, TreeNode) }
    :param seq: tokens 序列
    :return:
    """
    tokens = seq.split()

    # '0' 代表 Dummy Root Node，类型为 Unclassified（得分记为0）。其他节点从 '1' 开始编号
    parent = root = Node('0')
    nodes_dict = {'0': MatchTreeNode(Widget.Unclassified, root)}

    stack_parent = [root]
    stack_cnt_children = [0]

    idx = 1
    for _, token in enumerate(tokens):
        if token == '{':
            parent = stack_parent[-1]
            stack_cnt_children.append(0)
        elif token == '}':
            cnt_children = stack_cnt_children.pop()
            if cnt_children > 0:
                del stack_parent[-cnt_children:]
            parent = stack_parent[-1 - stack_cnt_children[-1]]  # locate the parent node
        else:
            tree_node = Node(str(idx), parent=parent)
            nodes_dict[str(idx)] = MatchTreeNode(Widget[token], tree_node)
            stack_parent.append(tree_node)
            stack_cnt_children[-1] += 1
            idx += 1

    return root, nodes_dict


def split_list_item_subtree(tree_node, nd, item_roots):
    """
    解除待匹配的输入布局树 tree_node 中类型为 List 的节点的子项。目前处理是默认选择 List 的第一个子项作为所有子项的结构
    :param tree_node: 输入布局树节点（开始递归遍历）
    :param nd: node dict
    :param item_roots: 输入布局树中的所有表项根节点（可能有多个）
    :return:
    """
    node_id = tree_node.name

    if tree_node.parent is not None and nd[tree_node.parent.name].widget_type == Widget.List:
        tree_node.parent = None

    # 解除所有 List 节点的子节点，并保留其中一个加入到 item_roots 列表中
    if nd[node_id].widget_type == Widget.List:
        if len(tree_node.children) > 0:
            item_roots.append(tree_node.children[0])

    for child in tree_node.children:
        split_list_item_subtree(child, nd, item_roots)


def dfs_compress_tree(tree_node, idx, nd):
    node_parent = tree_node.parent
    if nd[tree_node.name].widget_type == Widget.Layout and len(tree_node.children) == 1:
        alt_node = tree_node.children[0]
        while nd[alt_node.name].widget_type == Widget.Layout and len(alt_node.children) == 1:
            alt_node = alt_node.children[0]
        # replace the tree node to the alt node
        node_parent.children = node_parent.children[:idx] + (alt_node,) + node_parent.children[idx + 1:]
        # remove leaf layout node
        child_idx = 0
        for child in alt_node.children:
            dfs_compress_tree(child, child_idx, nd)
            child_idx += 1
    else:
        child_idx = 0
        for child in tree_node.children:
            dfs_compress_tree(child, child_idx, nd)
            child_idx += 1


def dfs_remove_invalid_leaf(tree_node, nodes_dict):
    """
    清理孤立 Layout/Unclassified 节点（与清理 Rico 数据集不同）
    :param tree_node:
    :param nodes_dict:
    :return:
    """
    widget_node = nodes_dict[tree_node.name]
    widget_type = widget_node.widget_type

    if widget_type == Widget.Layout and len(tree_node.children) == 0 or \
            widget_type == Widget.Unclassified:
        tree_node.parent = None
    for child in tree_node.children:
        dfs_remove_invalid_leaf(child, nodes_dict)


def dfs_make_tokens(tree_node, nodes_dict, new_tokens):
    new_tokens.append(nodes_dict[tree_node.name].widget_type.name)
    if len(tree_node.children) > 0:
        new_tokens.append('{')
        for child in tree_node.children:
            dfs_make_tokens(child, nodes_dict, new_tokens)
        new_tokens.append('}')


def optimize_sequence(seq):
    root, nodes_dict = create_layout_tree(seq)

    for i in range(3):
        if len(root.children) > 0:
            dfs_compress_tree(root.children[0], 0, nodes_dict)
        if len(root.children) > 0:
            dfs_remove_invalid_leaf(root.children[0], nodes_dict)

    # 为压缩后的 layout-tree 生成序列
    new_tokens = []
    for child in root.children:
        dfs_make_tokens(child, nodes_dict, new_tokens)

    return " ".join(new_tokens)


def analyze(seq, file1, file2, print_mode):
    root, nodes_dict = create_layout_tree(seq)

    if print_mode:
        render_tree(root, nodes_dict, file1)

    for i in range(3):
        if len(root.children) > 0:
            dfs_compress_tree(root.children[0], 0, nodes_dict)
        if len(root.children) > 0:
            dfs_remove_invalid_leaf(root.children[0], nodes_dict)

    if print_mode:
        render_tree(root, nodes_dict, file2)