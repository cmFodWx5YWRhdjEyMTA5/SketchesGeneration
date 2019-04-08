import os

import demjson

app_list_dir = '/Users/gexiaofei/Working/list'

for dir_name in os.listdir(app_list_dir):
    dir_path = os.path.join(app_list_dir, dir_name)
    if os.path.isdir(dir_path):
        # category
        package_list_fp = os.path.join(app_list_dir, dir_name + '.lst')
        open(package_list_fp, 'w')
        for file in os.listdir(dir_path):
            if not file.startswith('.'):
                print('processing', os.path.join(dir_path, file), '...')
                with open(os.path.join(dir_path, file), 'rb') as f:
                    json_data = demjson.decode(f.read())
                for item in json_data:
                    try:
                        if item['free'] and float(item['score']) > 4.0:
                            open(package_list_fp, 'a').write(item['appId'] + '\n')
                    except TypeError:
                        print('Not a float')
                print(os.path.join(dir_path, file), 'processed.')
