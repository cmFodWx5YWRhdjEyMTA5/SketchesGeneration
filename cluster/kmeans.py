import csv
import os
import shutil

import numpy as np
from sklearn.cluster import KMeans

from sketch import config
from sketch.directory_manager import copy_file

COLUMN_TITLES = config.CSV_CONFIG['column_titles']

num_features = 12


def transform_csv_to_matrix(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        num_lines = sum(1 for _ in f) - 1
        matrix = np.zeros(shape=(num_lines, num_features))
        print('>>> data X shape:', matrix.shape)

    with open(csv_path, 'r', encoding='utf-8') as f:
        sha1_values = []
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if csv_reader.line_num == 1:
                continue
            feature = []
            col_index = 0
            for col_title in COLUMN_TITLES:
                if col_title == 'sha1':
                    sha1_values.append(row[col_index])
                if col_title == 'class':
                    class_str = row[col_index]
                    feature.append(int('Text' in class_str))
                    feature.append(int('Button' in class_str))
                    feature.append(int('Image' in class_str))
                    feature.append(int('CheckBox' in class_str))
                    feature.append(int('Toggle' in class_str))
                    feature.append(int('Switch' in class_str))
                    feature.append(int('Radio' in class_str))
                    feature.append(int('Menu' in class_str))
                    feature.append(int('Layout' in class_str))
                    feature.append(int('Container' in class_str))
                elif col_title == 'clickable' or col_title == 'parent-clickable':
                    feature.append(int(row[col_index] == 'True'))
                col_index += 1
            matrix[csv_reader.line_num - 2] = np.array(feature)

    return sha1_values, matrix


def create_cluster_dirs(sha1s, labels, widgets_dir, clusters_dir):
    if os.path.exists(clusters_dir):
        shutil.rmtree(clusters_dir)
    os.makedirs(clusters_dir)

    for idx, sha1 in enumerate(sha1s):
        file_name = sha1 + '.jpg'
        copy_file(os.path.join(widgets_dir, file_name),
                  os.path.join(clusters_dir, str(labels[idx]), file_name))


if __name__ == '__main__':
    sha1s, data = transform_csv_to_matrix('E:\\playground\\analysis_result.csv')
    kmeans = KMeans(n_clusters=10, random_state=0).fit(data)

    print('K-Means cluster centers:')
    print(kmeans.cluster_centers_)

    # create_cluster_dirs(sha1s, kmeans.labels_, config.SKETCHES_CONFIG['widget_cut_dir'],
    #                     config.DIRECTORY_CONFIG['widget_clusters_dir'])
