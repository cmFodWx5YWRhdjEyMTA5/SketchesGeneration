import random
import os
import time
from widget import Widget
from layout_compressor import get_optimized_seq
import yaml


def gen_vocab_file(vocab_file_path):
    # 生成词汇表
    with open(vocab_file_path, 'w') as f:
        f.write('{\n')
        f.write('}\n')
        for widget in Widget:
            f.write(widget.name + '\n')
    print('>>> Generating Vocabulary file', vocab_file_path, '... OK')


def gen_training_lists(i2l_dict, long_tokens_lines, train_file_path, val_file_path, test_shuffle_file_path,
                       dataset_size, test_prop, val_prop):
    # 构造训练/验证/测试集
    print('>>> Random sampling test indexes ...', end=' ')
    valid_indexes = [x for x in range(dataset_size) if i2l_dict[x] not in long_tokens_lines]

    size_valid_indexes = len(valid_indexes)
    size_test = int(size_valid_indexes * test_prop)
    size_val = int(size_valid_indexes * val_prop)
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


def gen_i2l_dict(index_map_file_path):
    """
    构造 index seq_line_no 字典
    :return: 字典 {rico_index: line_number}
    """
    #
    index_map = {}
    with open(index_map_file_path, 'r') as f:
        for line in f:
            index, line_no = [int(x) for x in line.split()]
            index_map[index] = line_no
    print('>>> Reading Index Map from', index_map_file_path, '... OK')
    return index_map


def get_invalid_line_nos(seq_file_path, new_seq_file_path, max_num_tokens, min_num_tokens):
    """
    去除 sequence 中长度超出阈值的项、无效项，并调用优化、压缩算法后生成新 sequence
    :param seq_file_path: 保存 sequences 的文件路径
    :param new_seq_file_path: 生成有效 sequences 的文件路径
    :return: 无效项的行号
    """
    print('>>> Cleaning', seq_file_path, end=' ')
    with open(seq_file_path, 'r') as f:
        new_lines = []
        lines = f.readlines()
        inv_line_nos = []
        line_no = 0
        for line in lines:
            new_line = get_optimized_seq(line)
            new_lines.append(new_line + '\n')
            len_tokens = len(new_line.split())
            if len_tokens > max_num_tokens or len_tokens < min_num_tokens:
                inv_line_nos.append(line_no)
            line_no += 1
            if line_no % 3000 == 0:
                print('.', end='')
    print('OK')
    print(inv_line_nos[:20])
    print('### After cleaning,', len(inv_line_nos), 'lines have more than', max_num_tokens,
          'tokens. They will not be included in training samples set.')

    print('>>> Writing', new_seq_file_path, '...', end=' ')
    with open(new_seq_file_path, 'w') as f:
        for line in new_lines:
            f.writelines(line)
    print('OK')

    return inv_line_nos


if __name__ == '__main__':
    start_time = time.time()

    training_config = yaml.safe_load(open('config.yaml'))['training']
    data_dir = training_config['data_dir']

    gen_vocab_file(os.path.join(data_dir, training_config['vocab_file_name']))

    i2l_dict = gen_i2l_dict(os.path.join(data_dir, training_config['index_map_file_name']))
    invalid_lines = get_invalid_line_nos(os.path.join(data_dir, training_config['layout_seq_file_name']),
                                         os.path.join(data_dir, training_config['new_layout_seq_file_name']),
                                         training_config['max_tokens_num'], training_config['min_tokens_num'])

    gen_training_lists(i2l_dict, invalid_lines,
                       os.path.join(data_dir, training_config['train_lst_name']),
                       os.path.join(data_dir, training_config['val_lst_name']),
                       os.path.join(data_dir, training_config['test_lst_name']),
                       training_config['dataset_size'], training_config['test_prop'], training_config['val_prop'])

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
