import os

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

TRAINING_CONFIG = {
    'layout_seq_file_name': 'layout_sequence.lst',
    'index_map_file_name': 'index_map.lst',

    'vocab_file_name': 'vocab.txt',
    'train_lst_name': 'train.lst',
    'val_lst_name': 'validate.lst',
    'test_lst_name': 'test_shuffle.lst',

    'dataset_size': 72219,
    'test_prop': 0.05,
    'val_prop': 0.05,
    'max_tokens_num': 150,
    'min_tokens_num': 5
}

working_dir = 'E:\\sketches-test\\'
playground_dir = 'E:\\playground\\'

DIRECTORY_CONFIG = {
    'rico_combined_dir': 'E:\\rico-dataset\\combined',
    'sketches_combined_dir': working_dir + 'data\\processedImage',
    'widget_sketches_dir': os.path.join(PROJECT_ROOT, 'pictures', 'frameless'),

    'rico_dirs_dir': working_dir + 'rico-data',
    'sketches_dirs_dir': working_dir + 'sketches',
    'cleaned_json_dir': working_dir + 'cleaned-json',
    'training_file_dir': working_dir + 'data',

    'widget_clusters_dir': playground_dir + 'clusters',
    'models_dir': playground_dir + 'models',
}

SKETCHES_CONFIG = {
    'widget_cut_dir': playground_dir + 'widget-cut',
    'csv_file_path': playground_dir + 'analysis_result.csv',

    'sketch-width': 200,
    'sketch-height': 300,
}

CSV_CONFIG = {
    'column_titles': ['sha1', 'rico-index', 'resource-id', 'class', 'ancestors', 'first-official-class', 'level',
                      'clickable', 'parent-clickable', 'visibility', 'visible-to-user', 'focusable', 'focused',
                      'enabled', 'draw', 'scrollable-horizontal', 'scrollable-vertical', 'pointer', 'long-clickable',
                      'selected', 'pressed', 'abs-pos', 'bounds', 'package', 'content-desc']
}
