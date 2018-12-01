from enum import Enum


class Widget(Enum):
    Layout = 0
    Unclassified = 1
    Button = 2
    TextView = 3
    TextLink = 4
    ImageView = 5
    ImageLink = 6
    EditText = 7
    CheckBox = 8
    # Toolbar = 9


class WidgetNode(object):

    def __init__(self, w_type, w_json, w_id, w_class, w_bounds, w_ancestor_clickable):
        self.w_type = w_type
        self.w_json = w_json
        self.w_bounds = w_bounds
        self.w_id = w_id
        self.w_class = w_class
        self.w_ancestor_clickable = w_ancestor_clickable
