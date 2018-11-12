import shutil
import os
import time
from os import walk

RICO_DIR = 'E:\\rico-dataset\\combined'
DIVIDED_RICO_DIR = 'E:\\sketches-test\\rico-data'

SKETCHES_DIR = 'E:\\sketches-test\\sketches'
MERGE_DIR = 'E:\\sketches-test\\data\\processedImage'

NUM_PER_DIR = 1000

DIVIDE_OR_MERGE = False


def check_make_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def copy_file(src_path, dst_path):
    if not os.path.isfile(src_path):
        print(src_path, "not exist!")
    else:
        fpath, fname = os.path.split(dst_path)
        if not os.path.exists(fpath):
            os.makedirs(fpath)
        shutil.copyfile(src_path, dst_path)
        # print('copy', src_path, '>', dst_path)


def move_file(src_path, dst_path):
    if not os.path.isfile(src_path):
        print(src_path, "not exist!")
    else:
        fpath, fname = os.path.split(dst_path)
        if not os.path.exists(fpath):
            os.makedirs(fpath)
        shutil.move(src_path, dst_path)


def make_sub_dir(src_dir, output_dir):
    check_make_dir(output_dir)
    print('### Checking/Making root directory to save divided directories ... OK')

    num_files = int(len(os.listdir(src_dir)) / 2)

    i = 0
    while i < num_files:
        dir_path = os.path.join(output_dir, str(i) + '-' + str(i + NUM_PER_DIR - 1)) \
            if i + NUM_PER_DIR - 1 < num_files else os.path.join(output_dir, str(i) + '-' + str(num_files - 1))
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        i = i + NUM_PER_DIR
    print('### Sub directories created. Each directory contains', NUM_PER_DIR, 'files.')

    for dir_name in os.listdir(output_dir):
        dir_path = os.path.join(output_dir, dir_name)
        if os.path.isdir(dir_path):
            print('>>> Creating directory', dir_name, '...', end=' ')
            beg_index = int(dir_name.split('-')[0])
            end_index = int(dir_name.split('-')[1])
            for i in range(beg_index, end_index + 1):
                copy_file(os.path.join(src_dir, str(i) + '.json'),
                          os.path.join(dir_path, str(i) + '.json'))
                copy_file(os.path.join(src_dir, str(i) + '.jpg'),
                          os.path.join(dir_path, str(i) + '.jpg'))
            print('OK')
    print('<<< All rico files copied to sub directories in', DIVIDED_RICO_DIR)


def merge_dirs(src_dir, dst_dir):
    check_make_dir(dst_dir)
    print('### Checking/Making directory to save store images ... OK')

    file_cnt = 0
    for (_, subdir_names, _) in walk(src_dir):
        for subdir_name in subdir_names:
            subdir_path = os.path.join(src_dir, subdir_name)
            print('>>> Moving files from directory', subdir_path, '...', end=' ')
            for (_, _, file_names) in walk(subdir_path):
                for file_name in file_names:
                    ext = os.path.splitext(file_name)[-1].lower()
                    if ext == '.png':
                        file_path = os.path.join(subdir_path, file_name)
                        copy_file(file_path, os.path.join(MERGE_DIR, file_name))
                        file_cnt += 1
            print('OK')
    print('<<<', str(file_cnt), 'PNGs in sub directories copied to', MERGE_DIR)


if __name__ == '__main__':

    start_time = time.time()

    if DIVIDE_OR_MERGE:
        make_sub_dir(RICO_DIR, DIVIDED_RICO_DIR)
    else:
        merge_dirs(SKETCHES_DIR, MERGE_DIR)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
