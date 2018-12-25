try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from sketch.widget import Widget


def infer_widget_type(cn, ancestors):
    if 'LinearLayout' in cn or 'RelativeLayout' in cn or 'ScrollView' in cn or 'FrameLayout' in cn \
            or 'ListView' in cn or 'RecyclerView' in cn:
        return Widget.Layout
    if 'TextView' in cn:
        return Widget.TextView
    if 'Image' in cn:
        return Widget.ImageView
    if 'Edit' in cn:
        return Widget.EditText
    if 'Button' in cn or 'ImageButton' in cn:
        return Widget.Button
    return Widget.Unclassified


def xml_dfs(xml_node, tokens):
    tokens.append(infer_widget_type(xml_node.tag).name)
    if len(xml_node) > 0:
        tokens.append('{')
        for c in xml_node:
            xml_dfs(c, tokens)
        tokens.append('}')


def xml_process(xml_fp, out_fp):
    tree = ET.ElementTree(file=xml_fp)
    root = tree.getroot()

    tokens = []
    xml_dfs(root, tokens)

    print(' '.join(tokens))


if __name__ == '__main__':
    tokens = []
    xml_process('E:\\apk-analysis\\org.wikipedia\\res\layout\\activity_login.xml', None)
