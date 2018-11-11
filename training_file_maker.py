import random
import os
import time
from datetime import datetime
from json_handler import Widget
from layout_compressor import get_optimized_seq

DATASET_SIZE = 72219
TEST_PROP = 0.05
VAL_PROP = 0.05

MAX_NUM_TOKENS = 150

DATA_DIR = 'data'
LAYOUT_SEQ_FILE_NAME = 'layout_sequence.lst'
NEW_LAYOUT_SEQ_FILE_NAME = 'new_layout_sequence.lst'
INDEX_LINE_MAP_FILE_NAME = 'index_map.lst'

VOCAB_FILE_NAME = 'xml_vocab.txt'
TRAIN_FILE_NAME = 'train.lst'
VAL_FILE_NAME = 'validate.lst'
TEST_SHUFFLE_FILE_NAME = 'test_shuffle.lst'


def gen_vocab_file(vocab_file_path):
    # 生成词汇表
    with open(vocab_file_path, 'w') as f:
        f.write('{\n')
        f.write('}\n')
        for widget in Widget:
            f.write(widget.name + '\n')
    print('>>> Generating Vocabulary file', vocab_file_path, '... OK')


def gen_training_lists(i2l_dict, long_tokens_lines, train_file_path, val_file_path, test_shuffle_file_path):
    # 构造训练/验证/测试集
    print('>>> Random sampling test indexes ...', end=' ')
    valid_indexes = [x for x in range(DATASET_SIZE) if i2l_dict[x] not in long_tokens_lines]

    size_valid_indexes = len(valid_indexes)
    size_test = int(size_valid_indexes * TEST_PROP)
    size_val = int(size_valid_indexes * VAL_PROP)
    size_train = size_valid_indexes - size_test - size_val

    test_indexes = random.sample(valid_indexes, size_test)
    train_val_indexes = [x for x in valid_indexes if x not in test_indexes]
    val_indexes = random.sample(train_val_indexes, size_val)
    val_indexes.sort()
    train_indexes = [x for x in train_val_indexes if x not in val_indexes]
    print('OK')
    print('>>>', size_valid_indexes, 'valid samples are divided into:')
    print('   Training set:', size_train, '(' + str(round(size_train / size_valid_indexes * 100, 2)) + '%)')
    print('   Validate set:', size_val, '(' + str(round(size_val / size_valid_indexes * 100, 2)) + '%)')
    print('   Test set:', size_test, '(' + str(round(size_test / size_valid_indexes * 100, 2)) + '%)')

    # 生成 test.lst 文件
    with open(test_shuffle_file_path, 'w') as f:
        for index in test_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', test_shuffle_file_path, '... OK')

    # 生成 train.lst 文件
    with open(train_file_path, 'w') as f:
        for index in train_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', train_file_path, '... OK')

    # 生成 validate.lst 文件
    with open(val_file_path, 'w') as f:
        for index in val_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', val_file_path, '... OK')


def gen_i2l_dict():
    # 构造 index seq_line_no 字典
    index_map = {}
    index_map_file_path = os.path.join(DATA_DIR, INDEX_LINE_MAP_FILE_NAME)
    with open(index_map_file_path, 'r') as f:
        for line in f:
            index, line_no = [int(x) for x in line.split()]
            index_map[index] = line_no
    print('>>> Reading Index Map from', index_map_file_path, '... OK')
    return index_map


def get_invalid_line_nos(seq_file_path, new_seq_file_path):
    # 去除 sequence 中长度超出阈值的项
    print('>>> Cleaning', seq_file_path, end=' ')
    with open(seq_file_path, 'r') as f:
        new_lines = []
        lines = f.readlines()
        inv_line_nos = []
        line_no = 0
        for line in lines:
            new_line = get_optimized_seq(line)
            new_lines.append(new_line + '\n')
            if len(new_line.split()) > MAX_NUM_TOKENS:
                inv_line_nos.append(line_no)
            line_no += 1
            if line_no % 3000 == 0:
                print('.', end='')
    print('OK')
    print(inv_line_nos[:20])
    print('### After cleaning,', len(inv_line_nos), 'lines have more than', MAX_NUM_TOKENS,
          'tokens. They will not be included in training samples set.')

    print('>>> Writing', new_seq_file_path, '...', end=' ')
    with open(new_seq_file_path, 'w') as f:
        for line in new_lines:
            f.writelines(line)
    print('OK')

    return inv_line_nos


if __name__ == '__main__':

    start_time = time.time()

    gen_vocab_file(os.path.join(DATA_DIR, VOCAB_FILE_NAME))

    i2l_dict = gen_i2l_dict()
    long_lines = get_invalid_line_nos(os.path.join(DATA_DIR, LAYOUT_SEQ_FILE_NAME),
                                      os.path.join(DATA_DIR, NEW_LAYOUT_SEQ_FILE_NAME))

    gen_training_lists(i2l_dict, long_lines,
                       os.path.join(DATA_DIR, TRAIN_FILE_NAME),
                       os.path.join(DATA_DIR, VAL_FILE_NAME),
                       os.path.join(DATA_DIR, TEST_SHUFFLE_FILE_NAME))

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
