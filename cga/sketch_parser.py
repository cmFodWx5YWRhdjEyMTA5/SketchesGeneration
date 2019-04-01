import os
from configparser import ConfigParser, ExtendedInterpolation
from enum import Enum

from PIL import Image

from rico.generator import draw_colored_image
from utils.files import check_make_dir, listdir_nohidden
from utils.widget import Widget

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('../config.ini')

# 画布长宽
SKETCH_WIDTH = cfg.getint('nmt', 'sketch_width')
SKETCH_HEIGHT = cfg.getint('nmt', 'sketch_height')

coord_dir = cfg.get('sketch', 'coord_dir')
colored_dir = cfg.get('sketch', 'colored_dir')
nmt_file_dir = cfg.get('sketch', 'nmt_files_dir')

check_make_dir(colored_dir)
check_make_dir(nmt_file_dir)

sketch_sequences_fp = cfg.get('sketch', 'sequences')
sketch_lst_fp = cfg.get('sketch', 'dummy_lst')


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
        self.bounds = None

    def set_widget_type(self):
        def judge_widget_type(flags):
            if flags[Shape.HLINE.value] == 3 and flags[Shape.CIRCLE.value] == 1:
                return Widget.Toolbar  # - - - O
            if flags[Shape.ARROW.value] == 1:
                return Widget.List  # ->
            if flags[Shape.CROSS.value] == 3:
                # return Widget.TextLink if flags[Shape.HLINE.value] == 1 else Widget.TextView  # X X X
                return Widget.TextView
            if flags[Shape.TRIANGLE.value] == 1:
                # return Widget.ImageLink if flags[Shape.HLINE.value] == 1 else Widget.ImageView  # △
                return Widget.ImageView
            if flags[Shape.VLINE.value] == 1:
                return Widget.EditText  # |
            if flags[Shape.CHECK.value] == 1:
                return Widget.CheckBox  # X X V
            if flags[Shape.CIRCLE.value] == 1:
                if flags[Shape.CROSS.value] > 0:
                    return Widget.RadioButton  # X X O
                if flags[Shape.HLINE.value] == 1:
                    return Widget.Switch  # O -
                return Widget.Button  # O
            return Widget.Unclassified

        self.widget = judge_widget_type(self.inside_shapes_cnt)


def create_colored_pic(sketch_data_fp, out_fp):
    with open(sketch_data_fp, 'r') as f:
        non_rectangles = []  # 保存非矩形形状的列表
        rectangles = []  # 保存矩形的列表

        # 先获取第一行（为最外围矩形）
        head_line = next(f)
        nums = head_line.split()
        if int(nums[4]) != Shape.RECTANGLE.value:
            raise Exception('First line in the sketch data file must be the valid contour rectangle.')

        move_x = int(nums[1])
        move_y = int(nums[0])
        contour_width = int(nums[3])
        contour_height = int(nums[2])

        contour_rect = Rectangle(Shape.RECTANGLE, 0, 0, contour_width, contour_height)

        # 处理草图数据文件中的每一行（坐标）
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

        # 非矩形形状
        for component in non_rectangles:
            mid_x = (component.x0 + component.x1) / 2
            mid_y = (component.y0 + component.y1) / 2
            direct_rect = contour_rect
            # 检查每个矩形，记录包围该形状的最小矩形
            for rect in rectangles:
                if rect.x0 < mid_x < rect.x1 and rect.y0 < mid_y < rect.y1 and rect.get_area() < direct_rect.get_area():
                    direct_rect = rect
            # 修改最小包围矩形的内部形状计数值矩阵
            direct_rect.inside_shapes_cnt[component.shape.value] += 1

        im_colored = Image.new('RGB', (SKETCH_WIDTH, SKETCH_HEIGHT), (255, 255, 255))

        # 矩形: 先画 List，再画其他控件
        for rect in rectangles:
            rect.set_widget_type()  # 根据计数值矩阵判断控件类型
            # Toolbar 特殊处理
            rect.bounds = (13, 10, 187, 31) if rect.widget == Widget.Toolbar else (
                int(rect.x0 / contour_width * SKETCH_WIDTH), int(rect.y0 / contour_height * SKETCH_HEIGHT),
                int(rect.x1 / contour_width * SKETCH_WIDTH), int(rect.y1 / contour_height * SKETCH_HEIGHT))
            if rect.widget == Widget.List:
                draw_colored_image(im_colored, rect.widget, rect.bounds)

        for rect in rectangles:
            if rect.widget != Widget.List:
                draw_colored_image(im_colored, rect.widget, rect.bounds)

        im_colored.rotate(90, expand=1).save(out_fp)
        print(out_fp, "saved.")


def create_nmt_files(sketch_lst_fp, sketch_lst_content, layout_seq_fp, num_lines):
    with open(sketch_lst_fp, 'w') as f:
        f.write(sketch_lst_content)
    with open(layout_seq_fp, 'w') as f:
        f.write((Widget.Unclassified.name + '\n') * num_lines)
    print('NMT Training files saved in', sketch_lst_fp)


if __name__ == '__main__':
    files = list(listdir_nohidden(coord_dir))
    files.sort()
    sketch_nmt = ''

    for i, coord_file in enumerate(files):
        if coord_file.endswith('.lst'):
            file_name = os.path.splitext(coord_file)[0]
            create_colored_pic(sketch_data_fp=os.path.join(coord_dir, coord_file),
                               out_fp=os.path.join(colored_dir, file_name + '.png'))
            sketch_nmt += file_name + '.png ' + str(i) + '\n'

    create_nmt_files(sketch_lst_fp, sketch_nmt, sketch_sequences_fp, len(files))
