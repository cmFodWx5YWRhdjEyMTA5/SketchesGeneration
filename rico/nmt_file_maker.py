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
    random.seed(1)
    # 去除不适合作为测试集和验证集的图像
    unsuitable_indexes = [336, 4333, 4519, 4352, 4948, 5796, 9999, 10076, 10357, 10330, 11527, 11508, 12034, 12350,
                          13722, 13809, 13810, 13820, 13821, 14483, 14397, 14655, 14868, 15078, 15116, 15272, 15404,
                          16816, 17542, 17704, 17852, 17866, 18524, 18584, 18585, 19871, 20181, 20413, 20624, 21508,
                          22155, 23129, 23131, 23234, 23662, 23713, 23912, 23967, 24163, 24594, 25249, 25768, 26129,
                          26266, 27006, 27083, 27252, 27946, 27954, 28098, 28073, 28388, 29034, 29555, 29752, 30885,
                          31932, 32927, 33060, 33260, 58661, 58763, 60640, 61127, 61230, 63554, 69384, 69518, 57487,
                          34581, 34600, 34698, 36504, 37025, 37146, 37961, 39665, 40040, 41656, 41569, 41552, 41745,
                          41878, 43053, 44246, 48473, 50958, 51310, 52371, 52627, 52637, 52942, 54562, 59037, 59703,
                          59644, 59640, 60429, 60807, 61285, 61934, 62124, 63843, 63902, 64917, 65001, 65130, 65233,
                          65289, 66558, 66595, 67065, 67850, 68172, 68666, 68953, 69443, 69790, 69841, 69857, 70443,
                          71153, 72169, 71958, 1191, 1800, 1396, 1829, 2351, 3072, 5236, 6079, 6905, 8245, 8683, 9364,
                          9461, 9543, 11045, 11107, 11169, 12545, 12614, 12658, 12670, 12776, 13010, 13796, 14287,
                          15014, 15095, 15766, 15978, 16247, 16250, 16412, 16545, 16896, 18280, 19093, 21281, 21510,
                          22123, 23760, 23761, 24248, 27594, 27549, 30618, 31070, 31006, 33630, 33979, 34562, 34846,
                          35920, 35196, 36616, 37482, 37718, 38308, 39526, 41707, 42221, 42286, 42859, 43353, 43448,
                          43475, 43524, 44294, 46106, 46460, 47312, 48248, 50280, 50896, 53346, 54548, 56257]
    test_indexes_random = random.sample(valid_indexes, size_test)
    test_indexes = [x for x in test_indexes_random if x not in unsuitable_indexes]
    test_indexes.sort()

    train_val_indexes = [x for x in valid_indexes if x not in test_indexes_random]

    val_indexes_random = random.sample(train_val_indexes, size_val)
    val_indexes = [x for x in val_indexes_random if x not in unsuitable_indexes]
    val_indexes.sort()

    train_indexes = [x for x in train_val_indexes if x not in val_indexes_random and x not in unsuitable_indexes]

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
            tokens = line.split()
            len_tokens = len(tokens)
            if len_tokens > max_num_tokens or len_tokens == 0 or \
                    (Widget.TextView.name not in tokens and Widget.ImageView.name not in tokens and
                     Widget.EditText.name not in tokens and Widget.Button.name not in tokens and
                     Widget.CheckBox.name not in tokens and Widget.Switch.name not in tokens and
                     Widget.RadioButton.name not in tokens and Widget.Toolbar.name not in tokens):
                inv_lineno_list.append(i)
            if i % 3000 == 0:
                print('.', end='')
    print(' OK')
    print('### Cleaning ended.', len(inv_lineno_list), 'lines have more than', max_num_tokens,
          'or tokens only contain only container are excluded from training samples set.')

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
