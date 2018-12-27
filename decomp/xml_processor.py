try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import numpy as np
from sklearn.externals import joblib

from cluster.kmeans import create_feature
from sketch import config
from sketch.sketches_generator import get_std_class_name
from sketch.widget import Widget

kmeans = joblib.load(config.DIRECTORY_CONFIG['km_model_path'])
widget_type = {0: Widget.Button.name,
               1: Widget.TextLink.name,
               2: Widget.ImageLink.name,
               3: Widget.TextView.name,
               4: Widget.Button.name,
               5: Widget.ImageView.name,
               6: Widget.CheckBox.name,
               7: Widget.RadioButton.name,
               8: Widget.Button.name,
               9: Widget.Switch.name,
               10: Widget.EditText.name,
               11: Widget.Switch.name,
               12: Widget.Button.name,
               13: Widget.Switch.name,
               14: Widget.Button.name,
               15: Widget.Unclassified.name,
               16: Widget.Unclassified.name,
               17: Widget.Button.name,
               18: Widget.RadioButton.name,
               19: Widget.TextLink.name,
               20: Widget.Button.name,
               21: Widget.EditText.name,
               22: Widget.Switch.name,
               23: Widget.Button.name,
               24: Widget.Button.name,
               25: Widget.ImageView.name}


def is_valid_view(view):
    return view.tag == 'View' \
           and view.attrib['type'] != 'android.view.ContextMenu' \
           and view.attrib['type'] != 'android.view.Menu'


def view_xml_dfs(view, anc_clickable, tks):
    num_children = 0
    clickable = False
    for sub in view:
        if sub.tag == 'Child':
            for c in sub:
                if is_valid_view(c):
                    num_children += 1
        if sub.tag == 'EventAndHandler' and sub.attrib['event'] == 'click':
            clickable = anc_clickable = True

    std_clz_name, lvl = get_std_class_name(view.attrib['type'], view.attrib['ancestors'].strip('][').split(', '))
    feature = create_feature(view.attrib['type'], std_clz_name, clickable, anc_clickable)
    label = kmeans.predict(np.array(feature).reshape(1, -1))[0]

    if num_children > 0:
        tks.append('Layout')
    else:
        tks.append(widget_type[int(label)])
        if widget_type[int(label)] == 'Unclassified':
            print(widget_type[int(label)])
            print(view.attrib['type'], std_clz_name, clickable, anc_clickable)
            print(feature)

    if num_children > 0:
        for sub in view:
            if sub.tag == 'Child':
                tks.append('{')
                for c in sub:
                    if is_valid_view(c):
                        view_xml_dfs(c, anc_clickable, tks)
                tks.append('}')


def xml_process(xml_fp, out_fp):
    tree = ET.parse(xml_fp)
    root = tree.getroot()

    if root.tag == 'GUIHierarchy':
        app_name = root.attrib['app']
        for activ in root:
            if activ.tag == 'Activity':
                activ_name = activ.attrib['name']
                print('------------------------------')
                print(activ_name)
                for view in activ:
                    if is_valid_view(view):
                        tks = []
                        view_xml_dfs(view, anc_clickable=False, tks=tks)
                        print(' '.join(tks))


if __name__ == '__main__':
    tokens = []
    xml_process('C:\\Users\\Xiaofei\\Desktop\\org.wikipedia.apk-7988004980825930672.xml', None)
