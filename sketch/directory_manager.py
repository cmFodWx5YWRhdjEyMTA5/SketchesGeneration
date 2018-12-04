import os
import random
import shutil
import time
from os import walk

from sketch import config

MODE = 'test_analysis'

NUM_PER_DIR = 1000


def check_make_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    # print('###', dir_path, 'created.')


def copy_file(src_path, dst_path):
    if not os.path.isfile(src_path):
        print('###', src_path, "not exist!")
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
    print('<<< All rico files copied to sub directories in', output_dir)


def merge_dirs(src_dir, dst_dir):
    check_make_dir(dst_dir)
    print('### Checking/Making directory to save store images ... OK')

    file_cnt = 0
    for (_, subdir_names, _) in walk(src_dir):
        for subdir_name in subdir_names:
            subdir_path = os.path.join(src_dir, subdir_name)
            print('>>> Copying files from directory', subdir_path, '...', end=' ')
            for (_, _, file_names) in walk(subdir_path):
                for file_name in file_names:
                    ext = os.path.splitext(file_name)[-1].lower()
                    if ext == '.png':
                        file_path = os.path.join(subdir_path, file_name)
                        copy_file(file_path, os.path.join(dst_dir, file_name))
                        file_cnt += 1
            print('OK')
    print('<<<', str(file_cnt), 'PNGs in sub directories copied to', dst_dir)


def make_test_sketches_dir(test_lst_path, rico_dir, sketches_dir, output_dir, num_samples):
    check_make_dir(output_dir)
    print('### Checking/Making directory to save all test sketches ... OK')

    with open(test_lst_path, 'w') as f:
        lines = f.readlines()
        print('>>> Copying files to directory', output_dir, '...', end=' ')
        files = []
        for line in lines:
            file_name = line.split()[0]
            files.append(file_name)
            copy_file(os.path.join(sketches_dir, file_name), os.path.join(output_dir, file_name))
        if num_samples > 0:
            check_make_dir(os.path.join(output_dir, 'samples'))
            random.seed(0)
            sample_files = random.sample(files, num_samples)
            for file in sample_files:
                copy_file(os.path.join(sketches_dir, file), os.path.join(output_dir, 'samples', file))
                jpg = file.split('.')[0] + '.jpg'
                copy_file(os.path.join(rico_dir, jpg), os.path.join(output_dir, 'samples', jpg))
                json = file.split('.')[0] + '.json'
                copy_file(os.path.join(rico_dir, json), os.path.join(output_dir, 'samples', json))
        print('OK')


if __name__ == '__main__':

    start_time = time.time()

    dirs_config = config.DIRECTORY_CONFIG
    training_config = config.TRAINING_CONFIG

    print('---------------------------------')

    if MODE == 'divide_rico':
        make_sub_dir(dirs_config['rico_combined_dir'], dirs_config['rico_dirs_dir'])
    if MODE == 'merge_sketches':
        merge_dirs(dirs_config['sketches_dirs_dir'], dirs_config['sketches_combined_dir'])
    if MODE == 'test_analysis':
        make_test_sketches_dir(test_lst_path='E:\\sketches-test\\data\\test_shuffle.lst',
                               rico_dir=dirs_config['rico_combined_dir'],
                               sketches_dir=dirs_config['sketches_combined_dir'],
                               output_dir='C:\\Users\\Xiaofei\\Desktop\\test-sketches',
                               num_samples=30)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
