import random
import os
import time
from json_handler import Widget

DATASET_SIZE = 72219
TEST_SET_SIZE = 7222
VAL_SET_SIZE = 3611

DATA_DIR = 'E:\\sketches-test\\data'
LAYOUT_SEQ_FILE_NAME = 'layout_sequence.lst'
INDEX_LINE_MAP_FILE_NAME = 'index_map.lst'

VOCAB_FILE_NAME = 'xml_vocab.txt'
TEST_SHUFFLE_FILE_NAME = 'test_shuffle.lst'
TRAIN_SHUFFLE_FILE_NAME = 'train.lst'
VAL_SHUFFLE_FILE_NAME = 'validate.lst'

if __name__ == '__main__':

    start_time = time.time()

    print('## DATASET_SIZE = ' + str(DATASET_SIZE))
    print('## TRAIN_SET_SIZE = ' + str(DATASET_SIZE - VAL_SET_SIZE - TEST_SET_SIZE),
          str(round((DATASET_SIZE - VAL_SET_SIZE - TEST_SET_SIZE) / DATASET_SIZE * 100, 2)) + '%')
    print('## VAL_SET_SIZE = ' + str(VAL_SET_SIZE), str(round(VAL_SET_SIZE / DATASET_SIZE * 100, 2)) + '%')
    print('## TEST_SET_SIZE = ' + str(TEST_SET_SIZE), str(round(TEST_SET_SIZE / DATASET_SIZE * 100, 2)) + '%')

    # 生成词汇表
    vocab_file_path = os.path.join(DATA_DIR, VOCAB_FILE_NAME)
    with open(vocab_file_path, 'w') as f:
        f.write('{\n')
        f.write('}\n')
        for widget in Widget:
            f.write(widget.name + '\n')
    print('>>> Generating Vocabulary file', vocab_file_path, '... OK')

    print('>>> Random sampling test indexes ...', end=' ')
    total_indexes = range(DATASET_SIZE)
    test_indexes = random.sample(total_indexes, TEST_SET_SIZE)
    non_test_indexes = [x for x in total_indexes if x not in test_indexes]
    val_indexes = random.sample(non_test_indexes, VAL_SET_SIZE)
    val_indexes.sort()
    train_indexes = [x for x in non_test_indexes if x not in val_indexes]
    print('OK')

    # 构造 index seq_line_no 字典
    index_map = {}
    index_map_file_path = os.path.join(DATA_DIR, INDEX_LINE_MAP_FILE_NAME)
    with open(index_map_file_path, 'r') as f:
        for line in f:
            index, line_no = [int(x) for x in line.split()]
            index_map[index] = line_no
    print('>>> Reading Index Map from', index_map_file_path, '... OK')

    # 生成 test.lst 文件
    test_shuffle_file_path = os.path.join(DATA_DIR, TEST_SHUFFLE_FILE_NAME)
    with open(test_shuffle_file_path, 'w') as f:
        for index in test_indexes:
            f.write(str(index) + '.png ' + str(index_map[index]) + '\n')
    print('>>> Generating', test_shuffle_file_path, '... OK')

    # 生成 train.lst 文件
    train_shuffle_file_path = os.path.join(DATA_DIR, TRAIN_SHUFFLE_FILE_NAME)
    with open(train_shuffle_file_path, 'w') as f:
        for index in train_indexes:
            f.write(str(index) + '.png ' + str(index_map[index]) + '\n')
    print('>>> Generating', train_shuffle_file_path, '... OK')

    # 生成 validate.lst 文件
    val_shuffle_file_path = os.path.join(DATA_DIR, VAL_SHUFFLE_FILE_NAME)
    with open(val_shuffle_file_path, 'w') as f:
        for index in val_indexes:
            f.write(str(index) + '.png ' + str(index_map[index]) + '\n')
    print('>>> Generating', val_shuffle_file_path, '... OK')

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
