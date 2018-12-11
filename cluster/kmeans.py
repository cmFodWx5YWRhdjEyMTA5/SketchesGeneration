import csv
import os
import shutil
import time

import numpy as np
from sklearn.cluster import MiniBatchKMeans

from sketch import config
from sketch.directory_manager import copy_file

COLUMN_TITLES = config.CSV_CONFIG['column_titles']

feature_titles = ['Text', 'Edit', 'Button', 'Image', 'CheckBox', 'Toggle', 'Switch', 'Radio', 'Menu', 'Layout',
                  'Container', 'clickable', 'focusable', 'long-clickable', 'content-desc']
num_features = len(feature_titles)

num_clusters = 16


def transform_csv_to_matrix(csv_path):
    print('### csv file', csv_path, 'loaded.')

    with open(csv_path, 'r', encoding='utf-8') as f:
        num_lines = sum(1 for _ in f) - 1
        matrix = np.zeros(shape=(num_lines, num_features))
        print('### data X shape:', matrix.shape)

    print('>>> Transforming csv file to feature matrix ...', end='')
    with open(csv_path, 'r', encoding='utf-8') as f:
        sha1_values = []
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if csv_reader.line_num == 1:
                continue  # 忽略页眉
            elif csv_reader.line_num % 3000 == 0:
                print('.', end='')
            feature = create_feature(row, sha1_values)
            matrix[csv_reader.line_num - 2] = np.array(feature)
    print(' OK')

    return sha1_values, matrix


def create_feature(csv_row, sha1_values):
    def attr_create(keyword, f):
        f.append(int(keyword in class_str))

    class_keywords = ['Text', 'Edit', 'Button', 'Image', 'CheckBox', 'Toggle', 'Switch', 'Radio', 'Menu', 'Layout',
                      'Container']
    feature = []

    col_index = 0
    for col_title in COLUMN_TITLES:
        if col_title == 'sha1':
            sha1_values.append(csv_row[col_index])
        if col_title == 'class':
            class_str = csv_row[col_index]
            for k in class_keywords:
                attr_create(k, feature)
        elif col_title == 'clickable':
            feature.append(int(csv_row[col_index] == 'True' or csv_row[col_index + 1] == 'True'))
        elif col_title == 'focusable' or col_title == 'long-clickable':
            feature.append(int(csv_row[col_index] == 'True'))
        elif col_title == 'content-desc':
            feature.append(int(csv_row[col_index] != '[None]'))
        col_index += 1
    return feature


def create_cluster_dirs(sha1s, labels, widgets_dir, clusters_dir):
    if os.path.exists(clusters_dir):
        shutil.rmtree(clusters_dir)
    os.makedirs(clusters_dir)
    print('### Checking directory to save clustered widget cuts:', clusters_dir, '... OK')

    print('>>> Moving widget images to corresponding cluster directory ...', end='')
    for idx, sha1 in enumerate(sha1s):
        file_name = sha1 + '.jpg'
        copy_file(os.path.join(widgets_dir, file_name),
                  os.path.join(clusters_dir, str(labels[idx]), file_name))
        if idx % 3000 == 0:
            print('.', end='')
    print(' OK')


if __name__ == '__main__':
    print('---------------------------------')
    start_time = time.time()

    sha1s, data = transform_csv_to_matrix(config.SKETCHES_CONFIG['csv_file_path'])

    print('>>> K-means working ...', end=' ')
    weights = np.ones(shape=num_features)
    weights[4:9] = 3
    kmeans = MiniBatchKMeans(n_clusters=num_clusters, random_state=0).fit(np.multiply(data, weights))
    print('OK')

    # joblib.dump(kmeans, os.path.join(config.DIRECTORY_CONFIG['models_dir'], 'kmeans.pkl'))

    np.set_printoptions(formatter={'float_kind': lambda x: "%.3f" % x})
    centers = kmeans.cluster_centers_
    centers = np.divide(centers, weights)
    centers_file_path = 'E:\\playground\\centers.csv'
    with open(centers_file_path, 'w', newline='') as f:
        feature_titles.insert(0, 'cluster')
        csv.writer(f).writerow(feature_titles)
        for i, center in enumerate(centers):
            csv.writer(f).writerow(np.insert(center, 0, i))
    print('<<< K-Means cluster centers saved in', centers_file_path)

    create_cluster_dirs(sha1s, kmeans.labels_, config.SKETCHES_CONFIG['widget_cut_dir'],
                        config.DIRECTORY_CONFIG['widget_clusters_dir'])

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
