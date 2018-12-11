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
        csv_rows = []
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if csv_reader.line_num == 1:
                continue  # 忽略页眉
            elif csv_reader.line_num % 3000 == 0:
                print('.', end='')
            feature = create_feature(row)
            csv_rows.append(row)
            matrix[csv_reader.line_num - 2] = np.array(feature)
    print(' OK')

    return matrix, csv_rows


def create_feature(csv_row):
    class_keywords = ['Text', 'Edit', 'Button', 'Image', 'CheckBox', 'Toggle', 'Switch', 'Radio', 'Menu', 'Layout',
                      'Container']
    feature = []

    col_index = 0
    for col_title in COLUMN_TITLES:
        if col_title == 'class':
            class_str = csv_row[col_index]
            for k in class_keywords:
                feature.append(int(k in class_str))
        elif col_title == 'clickable':
            feature.append(int(csv_row[col_index] == 'True' or csv_row[col_index + 1] == 'True'))
        elif col_title == 'focusable' or col_title == 'long-clickable':
            feature.append(int(csv_row[col_index] == 'True'))
        elif col_title == 'content-desc':
            feature.append(int(csv_row[col_index] != '[None]'))
        col_index += 1
    return feature


def create_cluster_dirs(rows, labels, widgets_dir, clusters_dir, cluster_csv_path):
    if os.path.exists(clusters_dir):
        shutil.rmtree(clusters_dir)
    os.makedirs(clusters_dir)
    print('### Checking directory to save clustered widget cuts:', clusters_dir, '... OK')

    clustered_csv_rows = [['cluster'] + COLUMN_TITLES]

    print('>>> Moving widget images to corresponding cluster directory ...', end='')
    for idx, row in enumerate(rows):
        file_name = row[0] + '.jpg'
        copy_file(os.path.join(widgets_dir, file_name),
                  os.path.join(clusters_dir, str(labels[idx]), file_name))
        clustered_csv_rows.append([labels[idx]] + rows[idx])
        if idx % 3000 == 0:
            print('.', end='')
    with open(cluster_csv_path, 'w', newline='') as f:
        csv.writer(f).writerows(clustered_csv_rows)
    print(' OK')


if __name__ == '__main__':
    print('---------------------------------')
    start_time = time.time()

    data, csv_rows = transform_csv_to_matrix(config.SKETCHES_CONFIG['csv_file_path'])

    print('>>> K-means working ...', end=' ')
    weights = np.ones(shape=num_features)
    weights[4:9] = 3
    kmeans = MiniBatchKMeans(n_clusters=num_clusters, random_state=0).fit(np.multiply(data, weights))
    print('OK')

    # joblib.dump(kmeans, os.path.join(config.DIRECTORY_CONFIG['models_dir'], 'kmeans.pkl'))

    np.set_printoptions(formatter={'float_kind': lambda x: "%.3f" % x})
    centers = kmeans.cluster_centers_
    centers = np.divide(centers, weights)
    centers_file_path = config.DIRECTORY_CONFIG['cluster_centers_file_path']
    with open(centers_file_path, 'w', newline='') as f:
        feature_titles.insert(0, 'cluster')
        csv.writer(f).writerow(feature_titles)
        for i, center in enumerate(centers):
            csv.writer(f).writerow(np.insert(center, 0, i))
    print('<<< K-Means cluster centers saved in', centers_file_path)

    create_cluster_dirs(csv_rows, kmeans.labels_, config.SKETCHES_CONFIG['widget_cut_dir'],
                        config.DIRECTORY_CONFIG['widget_clusters_dir'],
                        config.DIRECTORY_CONFIG['cluster_csv_file_path'])

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
