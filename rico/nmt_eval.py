from configparser import ConfigParser, ExtendedInterpolation

import numpy as np
from nltk.translate.bleu_score import sentence_bleu

from decomp.layout_utils import optimize_sequence, create_layout_tree, get_tree_details
from utils.widget import Widget

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('../config.ini')

rico_combined_dir = cfg.get('dirs', 'rico_combined')
rico_divided_dir = cfg.get('dirs', 'rico_divided')
colored_pics_combined_dir = cfg.get('dirs', 'colored_pics_combined')

result_fp = 'C:\\Users\\Xiaofei\\Desktop\\results0418.txt'
correct_dp = 'C:\\Users\\Xiaofei\\Desktop\\correct'
incorrect_dp = 'C:\\Users\\Xiaofei\\Desktop\\incorrect'

if __name__ == '__main__':

    # num_depth = 10
    num_lines = len(list(open(result_fp)))
    scores = np.zeros((num_lines, 4))
    exact_matches = np.zeros((num_lines, 1))
    depths = np.zeros((num_lines, 1))
    widget_counts = np.zeros((num_lines, len(Widget.__members__.items())))
    total_counts = np.zeros((num_lines, 1))
    file_indices = {}

    with open(result_fp, 'r') as f:
        for i, line in enumerate(f):
            line_sp = line.split('\t')
            sketch_name = line_sp[0]
            # file_indices[sketch_name] = i
            true_tokens = line_sp[1].split()
            gen_tokens = line_sp[2].split()
            if true_tokens == gen_tokens:
                exact_matches[i] = 1

            # 处理两个 tokens 序列
            _, opt_seq = optimize_sequence(line_sp[1])
            true_root, tree_nd = create_layout_tree(opt_seq)
            depth, wc = get_tree_details(true_root, tree_nd)
            depths[i] = depth
            widget_counts[i] = np.asarray(wc)
            total_counts[i] = np.sum(widget_counts[i])

            score1 = sentence_bleu([gen_tokens], true_tokens, weights=(1, 0, 0, 0))
            score2 = sentence_bleu([gen_tokens], true_tokens, weights=(0.5, 0.5, 0, 0))
            score3 = sentence_bleu([gen_tokens], true_tokens, weights=(0.33, 0.33, 0.33, 0))
            score4 = sentence_bleu([gen_tokens], true_tokens)

            scores[i] = [score1, score2, score3, score4]

            print(sketch_name, 'n-gram score:', scores[i])

    print()
    print('### depth analysis ###')
    for i in range(15):
        indices = np.where(depths == i)[0]
        if len(indices) != 0:
            print('indices number:', len(indices))
            print('depth = ' + str(i) + ', multi-gram score:', np.mean(scores[indices], axis=0))
            print('depth = ' + str(i) + ', exact match rate:', np.mean(exact_matches[indices]))

    print()
    print('### containers analysis ###')
    for i in range(20):
        indices = np.where(widget_counts[:, 0] == i)[0]
        if len(indices) != 0:
            print('indices number:', len(indices))
            print('containers num = ' + str(i) + ', multi-gram score:', np.mean(scores[indices], axis=0))
            print('containers num = ' + str(i) + ', exact match rate:', np.mean(exact_matches[indices]))

    print()
    print('### num of components analysis ###')
    for i in range(40):
        indices = np.where(total_counts == i)[0]
        if len(indices) != 0:
            print('indices number:', len(indices))
            print('num of components = ' + str(i) + ', multi-gram score:', np.mean(scores[indices], axis=0))
            print('num of components = ' + str(i) + ', exact match rate:', np.mean(exact_matches[indices]))

    for i in range(2, 30, 3):
        indices_1 = np.where(total_counts == i - 1)[0]
        indices_2 = np.where(total_counts == i)[0]
        indices_3 = np.where(total_counts == i + 1)[0]
        print('num of components = ' + str(i - 1) + '-' + str(i + 1) + ', multi-gram score:', (
                    np.mean(scores[indices_1], axis=0) + np.mean(scores[indices_2], axis=0) + np.mean(scores[indices_3],
                                                                                                      axis=0)) / 3)
        print('num of components = ' + str(i - 1) + '-' + str(i + 1) + ', exact match rate:', (
                    np.mean(exact_matches[indices_1], axis=0) + np.mean(exact_matches[indices_2], axis=0) + np.mean(
                exact_matches[indices_3], axis=0)) / 3)

# print('Splitting true/false labeled images and files ...')
# with open(result_fp, 'r') as f:
#     for i, line in enumerate(f):
#         rico_index = line.split('\t')[0].split('.')[0]
#         if exact_matches[i] == 1:
#             copy_file(os.path.join(colored_pics_combined_dir, rico_index + '.png'),
#                       os.path.join(correct_dp, rico_index + '.png'))
#             copy_file(os.path.join(rico_combined_dir, rico_index + '.jpg'),
#                       os.path.join(correct_dp, rico_index + '.jpg'))
#         else:
#             copy_file(os.path.join(colored_pics_combined_dir, rico_index + '.png'),
#                       os.path.join(incorrect_dp, rico_index + '.png'))
#             copy_file(os.path.join(rico_combined_dir, rico_index + '.jpg'),
#                       os.path.join(incorrect_dp, rico_index + '.jpg'))
