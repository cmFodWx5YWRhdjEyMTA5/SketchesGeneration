import csv
import json
import os
import shutil
import time
from configparser import ConfigParser, ExtendedInterpolation

import numpy as np
from sklearn.cluster import KMeans
from sklearn.externals import joblib

from utils.files import copy_file

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('../config.ini')

COLUMN_TITLES = json.loads(cfg.get('debug', 'columns'))

KM_MODEL_PATH = cfg.get('debug', 'km_model')
CSV_ANALYSIS_FP = cfg.get('debug', 'csv_analysis')
CSV_CLUSTER_CENTERS_FP = cfg.get('debug', 'csv_cluster_centers')
CSV_CLUSTERS = cfg.get('debug', 'csv_clusters')
WIDGET_FLAKES_DIR = cfg.get('debug', 'widget_flakes')
WIDGET_CLUSTERS_DIR = cfg.get('debug', 'widget_clusters')

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

    data, csv_rows = transform_csv_to_matrix(CSV_ANALYSIS_FP)

    print('>>> K-means working ...', end=' ')
    weights = np.ones(shape=num_features)
    weights[4:8] = 2
    kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(np.multiply(data, weights))
    print('OK')

    joblib.dump(kmeans, KM_MODEL_PATH)

    np.set_printoptions(formatter={'float_kind': lambda x: "%.3f" % x})
    centers = kmeans.cluster_centers_
    centers = np.divide(centers, weights)
    with open(CSV_CLUSTER_CENTERS_FP, 'w', newline='', encoding='utf-8') as f:
        feature_titles.insert(0, 'cluster')
        csv.writer(f).writerow(feature_titles)
        for i, center in enumerate(centers):
            csv.writer(f).writerow(np.insert(center, 0, i))
    print('<<< K-Means cluster centers saved in', CSV_CLUSTER_CENTERS_FP)

    pred_labels = kmeans.predict(np.multiply(data, weights))
    create_cluster_dirs(csv_rows, pred_labels, WIDGET_FLAKES_DIR, WIDGET_CLUSTERS_DIR, CSV_CLUSTERS)

    print('---------------------------------')
    print('Duration: {:.2f} s'.format(time.time() - start_time))
