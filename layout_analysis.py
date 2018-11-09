from anytree import Node, RenderTree
from anytree.exporter import DotExporter


def get_layout_tree(sequence):
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
            while cnt_children > 0:
                stack_parent.pop()
                cnt_children -= 1
            parent = stack_parent[-1 - stack_cnt_children[-1]]  # locate the parent node
        else:
            tree_node = Node(token, parent=parent)
            stack_parent.append(tree_node)
            stack_cnt_children[-1] += 1

    for pre, fill, node in RenderTree(root):
        print("%s%s" % (pre, node.name))
    # DotExporter(root).to_picture("layout.png")


if __name__ == '__main__':
    get_layout_tree("Layout Layout")