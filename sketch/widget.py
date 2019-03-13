import os
from enum import Enum

from PIL import Image

from sketch import config


class Widget(Enum):
    Layout = 0
    TextView = 1
    TextLink = 2
    EditText = 3
    ImageView = 4
    ImageLink = 5
    Button = 6
    RadioButton = 7
    Switch = 8
    CheckBox = 9
    Unclassified = 10
    List = 11
    Toolbar = 12


class WidgetColor(object):
    BLACK_RGB = (0, 0, 0)
    GRAY_RGB = (128, 128, 128)
    RED_RGB = (255, 0, 0)  #
    LIME_RGB = (0, 255, 0)  #
    BLUE_RGB = (0, 0, 255)  #
    YELLOW_RGB = (255, 255, 0)  #
    MAGENTA_RGB = (255, 0, 255)  #
    CYAN_RGB = (0, 255, 255)  #
    MAROON_RGB = (128, 0, 0)  #
    GREEN_RGB = (0, 128, 0)  #
    NAVY_RGB = (0, 0, 128)  #


class WidgetSketch(object):
    widget_sketches_dir = config.DIRECTORY_CONFIG['widget_sketches_dir']

    IM_BUTTON = Image.open(os.path.join(widget_sketches_dir, 'button.png'))
    IM_EDIT_TEXT = Image.open(os.path.join(widget_sketches_dir, 'edit_text.png'))
    IM_IMAGE_VIEW = Image.open(os.path.join(widget_sketches_dir, 'image_view.png'))
    IM_TEXT_VIEW = Image.open(os.path.join(widget_sketches_dir, 'text_view.png'))
    IM_IMAGE_LINK = Image.open(os.path.join(widget_sketches_dir, 'image_link.png'))
    IM_TEXT_LINK = Image.open(os.path.join(widget_sketches_dir, 'text_link.png'))
    IM_CHECK_BOX = Image.open(os.path.join(widget_sketches_dir, 'checkbox.png'))


class WidgetNode(object):
    def __init__(self, w_type, w_json, w_id, w_class, w_bounds, w_ancestor_clickable):
        self.w_type = w_type
        self.w_json = w_json
        self.w_bounds = w_bounds
        self.w_id = w_id
        self.w_class = w_class
        self.w_ancestor_clickable = w_ancestor_clickable


class MatchTreeNode:
    def __init__(self, widget_type, tree_node):
        self.widget_type = widget_type
        self.tree_node = tree_node

    def __repr__(self):
        return "MatchTreeNode(type: {0} : children: {1})".format(self.widget_type, self.tree_node.children)
