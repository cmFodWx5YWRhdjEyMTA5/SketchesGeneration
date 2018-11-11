from anytree import Node, RenderTree
from anytree.exporter import DotExporter


def print_tree(tree_node, pic_name):
    for pre, fill, node in RenderTree(tree_node):
        print("%s%s" % (pre, node.name))
    if pic_name is not None:
        DotExporter(tree_node).to_picture(pic_name)


def get_layout_tree(sequence, analyze_mode):
    tokens = sequence.split()

    root = Node("Root")
    stack_parent = [root]
    parent = root
    stack_cnt_children = [0]

    for index, token in enumerate(tokens):
        if token == '{':
            parent = stack_parent[-1]
            stack_cnt_children.append(0)
        elif token == '}':
            cnt_children = stack_cnt_children.pop()
            if cnt_children > 0:
                del stack_parent[-cnt_children:]
            parent = stack_parent[-1 - stack_cnt_children[-1]]  # locate the parent node
        else:
            tree_node = Node(token + '_' + str(index) if analyze_mode else token, parent=parent)
            stack_parent.append(tree_node)
            stack_cnt_children[-1] += 1

    return root


def dfs_compress_tree(tree_node, idx):
    node_parent = tree_node.parent
    if tree_node.name.startswith('Layout') and len(tree_node.children) == 1:
        alt_node = tree_node.children[0]
        while alt_node.name.startswith('Layout') and len(alt_node.children) == 1:
            alt_node = alt_node.children[0]
        # replace the tree node to the alt node
        node_parent.children = node_parent.children[:idx] + (alt_node,) + node_parent.children[idx + 1:]
        # remove leaf layout node
        child_idx = 0
        for child in alt_node.children:
            dfs_compress_tree(child, child_idx)
            child_idx += 1
    else:
        child_idx = 0
        for child in tree_node.children:
            dfs_compress_tree(child, child_idx)
            child_idx += 1


def dfs_make_tokens(tree_node, new_tokens):
    new_tokens.append(tree_node.name)
    if len(tree_node.children) > 0:
        new_tokens.append('{')
        for child in tree_node.children:
            dfs_make_tokens(child, new_tokens)
        new_tokens.append('}')


def get_optimized_seq(seq):
    root = get_layout_tree(seq, False)
    dfs_compress_tree(root, None)

    new_tokens = []
    for child in root.children:
        dfs_make_tokens(child, new_tokens)

    return " ".join(new_tokens)


def analyze(seq, file1, file2):
    root = get_layout_tree(seq, True)

    print_tree(root, file1)
    dfs_compress_tree(root, None)
    print_tree(root, file2)


if __name__ == '__main__':
    seq = \
'Layout { Layout { Layout { Layout { Layout { Layout { Layout { Layout { Layout { TextView TextView Button Layout { Button Button Button } } Layout { Layout { Layout { TextLink } Layout { TextLink } } } } Layout { Layout { Layout { Layout { Layout { Button ImageView } Layout { TextView Layout { Layout { TextView TextView } Layout { TextView TextView } Layout { TextView TextView } } } } Layout { Layout { ImageView ImageView } Layout { TextView Layout { Layout { TextView TextView } Layout { TextView TextView } Layout { TextView TextView } } } } Layout { Layout { ImageView ImageView } Layout { TextView Layout { Layout { TextView TextView } Layout { TextView TextView } Layout { TextView } } } } Layout { Layout { ImageView ImageView } Layout { TextView Layout { Layout { TextView TextView } Layout { TextView TextView } Layout { TextView } } } } Layout { Layout { ImageView ImageView } Layout { TextView Layout { Layout { TextView TextView } Layout { TextView TextView } } } } } Button } } Layout { } } Layout { Layout { Layout { Layout { ImageLink Layout { TextView TextView } } } Layout { TextLink } Layout { TextLink } Layout { TextLink } Layout { Unclassified } Layout { TextLink } Layout { TextLink } Layout { TextLink } Layout { TextLink } Layout { Unclassified } Layout { TextLink } } } } } } } } Unclassified Unclassified }'
    analyze(seq, './data/layout1.png', './data/layout2.png')

