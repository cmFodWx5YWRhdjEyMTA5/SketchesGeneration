from enum import Enum

from PIL import Image

from sketch import config
from sketch.sketches_generator import draw_colored_image
from sketch.widget import Widget

# 画布长宽
SKETCH_WIDTH = config.SKETCHES_CONFIG['sketch-width']
SKETCH_HEIGHT = config.SKETCHES_CONFIG['sketch-height']


class Shape(Enum):
    VLINE = 1
    CIRCLE = 2
    TRIANGLE = 3
    CROSS = 4
    HLINE = 5
    RECTANGLE = 6
    CHECK = 7
    ARROW = 8


class Component(object):
    def __init__(self, shape, x0, y0, x1, y1):
        self.shape = shape
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def get_area(self):
        return (self.x1 - self.x0) * (self.y1 - self.y0)


class Rectangle(Component):
    def __init__(self, shape, x0, y0, x1, y1):
        super().__init__(shape, x0, y0, x1, y1)
        self.inside_shapes_cnt = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.widget = Widget.Unclassified

    def set_widget_type(self):

        def judge_widget_type(flags):
            if flags[Shape.HLINE.value] == 3 and flags[Shape.CIRCLE.value] == 1:
                return Widget.Toolbar
            if flags[Shape.ARROW.value] == 1:
                return Widget.List
            if flags[Shape.CROSS.value] == 3:
                return Widget.TextLink if flags[Shape.HLINE.value] == 1 else Widget.TextView
            if flags[Shape.TRIANGLE.value] == 1:
                return Widget.ImageLink if flags[Shape.HLINE.value] == 1 else Widget.ImageView
            if flags[Shape.VLINE.value] == 1:
                return Widget.EditText
            if flags[Shape.CROSS.value] == 2:
                if flags[Shape.CIRCLE.value] == 1:
                    return Widget.RadioButton
                if flags[Shape.CHECK.value] == 1:
                    return Widget.CheckBox
            if flags[Shape.CIRCLE.value] == 1:
                return Widget.Switch if flags[Shape.HLINE.value] == 1 else Widget.Button
            return Widget.Unclassified

        self.widget = judge_widget_type(self.inside_shapes_cnt)


if __name__ == '__main__':
    with open('/Users/gexiaofei/Desktop/PaperExample3-out.txt', 'r') as f:
        non_rectangles = []
        rectangles = []

        head_line = next(f)
        nums = head_line.split()
        if int(nums[4]) != Shape.RECTANGLE.value:
            print('Error: The first line must be the contour rectangle!')
            exit(-1)

        move_x = int(nums[1])
        move_y = int(nums[0])
        contour_width = int(nums[3])
        contour_height = int(nums[2])

        contour_rect = Rectangle(Shape.RECTANGLE, 0, 0, contour_width, contour_height)

        for line in f:
            nums = line.split()
            # 计算平移后的新坐标值
            x0 = int(nums[1]) - move_x
            y0 = int(nums[0]) - move_y
            x1 = x0 + int(nums[3])
            y1 = y0 + int(nums[2])
            if int(nums[4]) == Shape.RECTANGLE.value:
                rectangles.append(Rectangle(Shape.RECTANGLE, x0, y0, x1, y1))
            else:
                non_rectangles.append(Component(Shape(int(nums[4])), x0, y0, x1, y1))

        for component in non_rectangles:
            mid_x = (component.x0 + component.x1) / 2
            mid_y = (component.y0 + component.y1) / 2
            direct_rect = contour_rect
            for rect in rectangles:
                if rect.x0 < mid_x < rect.x1 and rect.y0 < mid_y < rect.y1 and rect.get_area() < direct_rect.get_area():
                    direct_rect = rect
            direct_rect.inside_shapes_cnt[component.shape.value] += 1

        im_colored = Image.new('RGB', (SKETCH_WIDTH, SKETCH_HEIGHT), (255, 255, 255))

        for rect in rectangles:
            rect.set_widget_type()
            print(rect.inside_shapes_cnt, rect.x0, rect.y0, rect.widget.name)

            bounds = (int(rect.x0 / contour_width * SKETCH_WIDTH), int(rect.y0 / contour_height * SKETCH_HEIGHT),
                      int(rect.x1 / contour_width * SKETCH_WIDTH), int(rect.y1 / contour_height * SKETCH_HEIGHT))
            print(bounds)
            draw_colored_image(im_colored, rect.widget, bounds)

            im_colored.save('/Users/gexiaofei/Desktop/PaperExample3-out.png')
