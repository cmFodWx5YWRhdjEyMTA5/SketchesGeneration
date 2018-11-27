import json
import os
import time
from datetime import datetime

import config


def json_handler(subdir_path, cleaned_subdir_path, rico_index):
    """
    将 rico_dirs_dir/dir_name 文件夹中的 json 文件清理后输出全包含可见控件的 json 文件保存到 cleaned_json_dir/dir_name 中
    :param subdir_path: 子文件夹路径
    :param rico_index: Rico 序号
    :param cleaned_subdir_path: 处理后子文件夹文件夹
    :return:
    """
    with open(os.path.join(subdir_path, rico_index + '.json'), 'r') as f:
        json_obj = json.load(f)

    root = json_obj['activity']['root']

    new_root = {k: root[k] for k, v in root.items() if k != 'children'}

    dfs_clean_json(root, new_root)

    with open(os.path.join(cleaned_subdir_path, rico_index + '.json'), 'w') as f:
        json.dump(new_root, f, indent=2)


def dfs_clean_json(json_obj, new_root):
    """
    通过深度优先搜索的方式清理 visible-to-user 值为 false 的控件
    :param json_obj: 原始 json 节点
    :param new_root: 已清理的 json_obj 副本
    :return:
    """
    # delete_unrelated_attrs(json_obj)
    if 'children' in json_obj:
        new_root['children'] = []
        for child in json_obj['children']:
            if child is not None and child['visible-to-user']:
                child_copy = {k: child[k] for k, v in child.items() if k != 'children'}
                new_root['children'].append(child_copy)
                dfs_clean_json(child, child_copy)


def delete_unrelated_attrs(json_node):
    """
    确定节点 json_node 保留的 json 属性
    :param json_node: 待处理的字典格式的 json 节点
    :return:
    """
    reserved_list = ['class', 'children', 'visibility']
    key_list = [key for key in json_node.keys() if key not in reserved_list]
    for k in key_list:
        del json_node[k]


if __name__ == '__main__':
    start_time = time.time()

    dir_config = config.DIRECTORY_CONFIG
    rico_dirs_dir = dir_config['rico_dirs_dir']
    cleaned_json_dir = dir_config['cleaned_json_dir']

    print('---------------------------------')
    print('>>> Start cleaning json files in', rico_dirs_dir, '...')

    # 检查输出文件夹状态
    if not os.path.exists(cleaned_json_dir):
        print('### Making directories to save cleaned json files ... OK')
        os.makedirs(cleaned_json_dir)
    print('### Checking directories to save cleaned json files:', cleaned_json_dir, '... OK')

    for case_name in os.listdir(rico_dirs_dir):
        if not case_name.startswith('.'):  # hidden files
            input_case_dir = os.path.join(rico_dirs_dir, case_name)
            output_case_dir = os.path.join(cleaned_json_dir, case_name)
            print('[' + datetime.now().strftime('%m-%d %H:%M:%S') + '] >>> Processing', output_case_dir, '...', end=' ')

            if not os.path.exists(output_case_dir):
                os.makedirs(output_case_dir)
            for file in os.listdir(input_case_dir):
                if file.endswith('.json'):
                    json_handler(os.path.join(rico_dirs_dir, case_name),
                                 os.path.join(cleaned_json_dir, case_name),
                                 file.split('.')[0])
            print('OK')

    print('<<< Cleaned json files saved in ' + cleaned_json_dir)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
