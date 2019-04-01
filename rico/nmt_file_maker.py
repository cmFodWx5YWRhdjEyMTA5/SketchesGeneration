import random
import time
from configparser import ConfigParser, ExtendedInterpolation

from utils.widget import Widget

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('../config.ini')

vocab_fp = cfg.get('files', 'vocab')
index_map_fp = cfg.get('files', 'index_map')
layout_sequences_fp = cfg.get('files', 'sequences')

max_tokens_num = cfg.getint('nmt', 'max_tokens_num')
min_tokens_num = cfg.getint('nmt', 'min_tokens_num')
dataset_size = cfg.getint('nmt', 'dataset_size')
test_prop = cfg.getfloat('nmt', 'test_prop')
val_prop = cfg.getfloat('nmt', 'val_prop')

train_fp = cfg.get('files', 'train')
val_fp = cfg.get('files', 'val')
test_fp = cfg.get('files', 'test')


def gen_vocab_file(vocab_file_path):
    """
    生成词汇表
    :param vocab_file_path: 词汇表路径
    :return:
    """
    with open(vocab_file_path, 'w') as f:
        f.write('{\n}\n')
        f.write('\n'.join([widget.name for widget in Widget]))
    print('>>> Generating Vocabulary file', vocab_file_path, '... OK')


def gen_training_lists(train_fp, val_fp, test_fp, dataset_size, test_prop, val_prop, i2l_dict, inv_lines):
    """
    生成训练/验证/测试集
    :param train_fp: 训练文件路径
    :param val_fp: 验证文件路径
    :param test_fp: 测试文件路径
    :param dataset_size: 数据集大小
    :param test_prop: 测试集所占比例
    :param val_prop: 验证集所占比例
    :param i2l_dict: {rico_index: line_number}
    :param inv_lines: 无效行列表
    :return:
    """
    print('>>> Random sampling test indexes ...', end=' ')
    valid_indexes = [x for x in range(dataset_size) if i2l_dict[x] not in inv_lines]

    # 根据预设比例计算三者大小
    size_valid_indexes = len(valid_indexes)
    size_test = int(size_valid_indexes * test_prop)
    size_val = int(size_valid_indexes * val_prop)
    size_train = size_valid_indexes - size_test - size_val

    # 随机选取 indexes 作为三者组成
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
    with open(test_fp, 'w') as f:
        for index in test_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', test_fp, '... OK')

    # 生成 train.lst 文件
    with open(train_fp, 'w') as f:
        for index in train_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', train_fp, '... OK')

    # 生成 validate.lst 文件
    with open(val_fp, 'w') as f:
        for index in val_indexes:
            f.write(str(index) + '.png ' + str(i2l_dict[index]) + '\n')
    print('>>> Generating', val_fp, '... OK')


def gen_i2l_dict(index_map_fp):
    """
    构造 index seq_line_no 字典用于构造训练集等时确定每张图所对应的行号
    :return: 字典 {rico_index: line_number}
    """
    #
    index_map = {}
    with open(index_map_fp, 'r') as f:
        for line in f:
            index, line_no = [int(x) for x in line.split()]
            index_map[index] = line_no
    print('>>> Reading Index Map from', index_map_fp, '... OK')
    return index_map


def get_invalid_lineno_list(seq_fp, max_num_tokens, min_num_tokens):
    """
    去除 sequence 中长度超出阈值的项、无效项，并调用优化、压缩算法后生成新 sequence
    :param seq_fp: 保存 sequences 的文件路径
    :param max_num_tokens: 最大认可 token 长度
    :param min_num_tokens: 最小认可 token 长度
    :return: 无效项的行号列表
    """
    print('>>> Reading and Cleaning', seq_fp, end=' ')
    with open(seq_fp, 'r') as f:
        lines = f.readlines()
        inv_lineno_list = []
        for i, line in enumerate(lines):
            len_tokens = len(line.split())
            if len_tokens > max_num_tokens or len_tokens < min_num_tokens and not (
                    len_tokens == 1 and line != 'Layout'):
                inv_lineno_list.append(i)
            if i % 3000 == 0:
                print('.', end='')
    print(' OK')
    print('### Cleaning ended.', len(inv_lineno_list), 'lines have more than', max_num_tokens,
          'or less than', min_num_tokens, 'tokens which are excluded from training samples set.')

    return inv_lineno_list


if __name__ == '__main__':
    start_time = time.time()
    print('---------------------------------')

    gen_vocab_file(vocab_fp)

    i2l_dict = gen_i2l_dict(index_map_fp)
    inv_lines = get_invalid_lineno_list(layout_sequences_fp, max_tokens_num, min_tokens_num)

    gen_training_lists(train_fp, val_fp, test_fp, dataset_size, test_prop, val_prop, i2l_dict, inv_lines)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
