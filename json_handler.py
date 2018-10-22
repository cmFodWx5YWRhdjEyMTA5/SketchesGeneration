import json
import os
from pprint import pprint
from PIL import Image

CLEAN_JSON = False
LEVEL = 1
CREATE_DRAWINGS = True


im_button = Image.open('./drawings/rectangle.png')
im_edit_text = Image.open('./drawings/rectangle.png')
im_image_view = Image.open('./drawings/rectangle.png')
im_text_view = Image.open('./drawings/rectangle.png')


def json_handler(read_json_file, write_json_file):
    with open(read_json_file, 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']
    root_children = root['children']

    # fixme: unchecked top layout placed at index 0
    top_layout = root_children[0]
    dfs_clean(top_layout)
    # pprint(top_layout)

    with open(write_json_file, 'w') as f:
        json.dump(top_layout, f, indent=2)


def img_processing(layout_json_file_path, output_img_file):
    with open(layout_json_file_path, 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']
    root_children = root['children']
    img_bounds = root['bounds']

    # fixme: unchecked top layout placed at index 0
    top_layout = root_children[0]

    im = Image.new('RGB', (img_bounds[2], img_bounds[3]), (255, 255, 255))
    dfs_im(top_layout, im)

    im.save(output_img_file, "JPEG")


# 深度优先遍历去除无关节点
def dfs_clean(json_obj):
    remove_unrelated_keys(json_obj)
    if 'children' not in json_obj:
        return

    # # print(len(json_obj['children']))
    # if 'class' in json_obj:
    #     print(json_obj['class'])

    for i in range(len(json_obj['children'])):
        dfs_clean(json_obj['children'][i])


def remove_unrelated_keys(json_dict):
    if LEVEL == 1:
        reserved_list = ['class', 'children', 'visibility']
    elif LEVEL == 2:
        reserved_list = ['class', 'children', 'visibility', 'bounds']
    else:
        reserved_list = ['class', 'children']

    key_list = [key for key in json_dict.keys() if key not in reserved_list]
    for k in key_list:
        del json_dict[k]


# 深度优先遍历按节点绘制草图
def dfs_im(json_obj, im):

    if not json_obj['visible-to-user']:
        return

    if not draw_component(im, json_obj['class'], json_obj['bounds']):
        for ancestor in json_obj['ancestors']:
            if draw_component(im, ancestor, json_obj['bounds']):
                break

    if 'children' not in json_obj:
        return

    for i in range(len(json_obj['children'])):
        dfs_im(json_obj['children'][i], im)


def draw_component(im, class_tag, bounds):
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    if w <= 0 or h <= 0:
        return

    # with priority
    if 'Button' in class_tag:
        im.paste(im_button.resize((w, h)), box=(bounds[0], bounds[1]))
        return True
    if 'Image' in class_tag:
        im.paste(im_image_view.resize((w, h)), box=(bounds[0], bounds[1]))
        return True
    if 'EditText' in class_tag:
        im.paste(im_edit_text.resize((w, h)), box=(bounds[0], bounds[1]))
        return True
    if 'TextView' in class_tag:
        im.paste(im_text_view.resize((w, h)), box=(bounds[0], bounds[1]))
        return True
    return False


if __name__ == '__main__':
    main_path = "./Top Apps"
    output_path = "./output"

    if CLEAN_JSON:
        print("Start cleaning json files ...")
        for case_dir in os.listdir(main_path):
            if not case_dir.startswith("."):    # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(main_path, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        json_handler(os.path.join(main_path, case_dir, file), os.path.join(output_path, case_dir, file_name + "." + str(LEVEL) + ".json"))
                print(os.path.join(output_path, case_dir))
        print("Output cleaned json files saved in " + output_path)

    output_path = "./Top Apps"
    # turn screenshots to sketches
    if CREATE_DRAWINGS:
        print("Start cleaning json files ...")
        for case_dir in os.listdir(main_path):
            if not case_dir.startswith("."):    # hidden files
                if not os.path.exists(os.path.join(output_path, case_dir)):
                    os.makedirs(os.path.join(output_path, case_dir))
                for file in os.listdir(os.path.join(main_path, case_dir)):
                    # print(file)
                    if file.endswith(".json"):
                        file_name = file.split('.')[0]
                        img_processing(os.path.join(main_path, case_dir, file),
                                       os.path.join(output_path, case_dir, file_name + '-sketch.jpg'))
                print(os.path.join(output_path, case_dir))
        print("Output drawings saved in " + output_path)
