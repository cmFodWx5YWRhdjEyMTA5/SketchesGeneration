import os

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

TRAINING_CONFIG = {
    'data_dir': 'E:\\rico-dataset\\data',

    'layout_seq_file_name': 'layout_sequence.lst',
    'new_layout_seq_file_name': 'new_layout_sequence.lst',
    'index_map_file_name': 'index_map.lst',

    'vocab_file_name': 'xml_vocab.txt',
    'train_lst_name': 'train.lst',
    'val_lst_name': 'validate.lst',
    'test_lst_name': 'test_shuffle.lst',

    'dataset_size': 72219,
    'test_prop': 0.05,
    'val_prop': 0.05,
    'max_tokens_num': 150,
    'min_tokens_num': 5
}

DIRECTORY_CONFIG = {
    'rico_combined_dir': 'E:\\rico-dataset\\combined',
    'sketches_combined_dir': 'E:\\sketches-test\\data\\processedImage',

    'rico_dirs_dir': 'E:\\sketches-test\\rico-data',
    'sketches_dirs_dir': 'E:\\sketches-test\\sketches',
    'cleaned_json_dir': 'E:\\sketches-test\\cleaned-json',
}

SKETCHES_CONFIG = {
    'widget_cut_dir': '/Users/gexiaofei/PycharmProjects/json_handler/widget-cut',
    'csv_file_path': 'analysis_result.csv'
}