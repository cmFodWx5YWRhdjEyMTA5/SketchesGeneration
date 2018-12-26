import csv
import os
import shutil
import time

import numpy as np
from sklearn.cluster import KMeans
from sklearn.externals import joblib

from sketch import config
from sketch.directory_manager import copy_file

COLUMN_TITLES = config.CSV_CONFIG['column_titles']

feature_titles = ['Text', 'Edit', 'Button', 'Image', 'CheckBox', 'Toggle', 'Switch', 'Radio', 'Menu', 'clickable']
class_keywords = ['Text', 'Edit', 'Button', 'Image', 'CheckBox', 'Toggle', 'Switch', 'Radio', 'Menu']

num_features = len(feature_titles)

num_clusters = 26


def transform_csv_to_matrix(csv_path):
    print('### csv file', csv_path, 'loaded.')

    with open(csv_path, 'r', encoding='utf-8') as f:
        num_lines = sum(1 for _ in f) - 1
        matrix = np.zeros(shape=(num_lines, num_features))
        print('### data X shape:', matrix.shape)

    print('>>> Transforming csv file to feature matrix ...', end='')
    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = []
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if csv_reader.line_num == 1:
                continue  # 忽略页眉
            elif csv_reader.line_num % 3000 == 0:
                print('.', end='')
            feature = create_feature(row[3], row[5], row[7] == 'True', row[8] == 'True')
            rows.append(row)
            matrix[csv_reader.line_num - 2] = np.array(feature)
    print(' OK')

    return matrix, rows


def create_feature(claz, fstdclaz, clickable, anc_clickable):
    feature = []
    for k in class_keywords:
        feature.append(int((k in claz) or (k in fstdclaz)))
    feature.append(int(clickable or anc_clickable))
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
    with open(cluster_csv_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(clustered_csv_rows)
    print(' OK')


if __name__ == '__main__':
    print('---------------------------------')
    start_time = time.time()

    data, csv_rows = transform_csv_to_matrix(config.SKETCHES_CONFIG['csv_file_path'])

    print('>>> K-means working ...', end=' ')
    weights = np.ones(shape=num_features)
    weights[4:8] = 2
    kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(np.multiply(data, weights))
    print('OK')

    joblib.dump(kmeans, config.DIRECTORY_CONFIG['km_model_path'])

    np.set_printoptions(formatter={'float_kind': lambda x: "%.3f" % x})
    centers = kmeans.cluster_centers_
    centers = np.divide(centers, weights)
    centers_file_path = config.DIRECTORY_CONFIG['cluster_centers_file_path']
    with open(centers_file_path, 'w', newline='', encoding='utf-8') as f:
        feature_titles.insert(0, 'cluster')
        csv.writer(f).writerow(feature_titles)
        for i, center in enumerate(centers):
            csv.writer(f).writerow(np.insert(center, 0, i))
    print('<<< K-Means cluster centers saved in', centers_file_path)

    pred_labels = kmeans.predict(np.multiply(data, weights))
    create_cluster_dirs(csv_rows, pred_labels, config.SKETCHES_CONFIG['widget_cut_dir'],
                        config.DIRECTORY_CONFIG['widget_clusters_dir'],
                        config.DIRECTORY_CONFIG['cluster_csv_file_path'])

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
