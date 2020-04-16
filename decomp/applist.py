#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 读取 google play store 爬取的应用元数据列表，列表路径为 app_list_dir。
    筛选出其中符合要求的 app 包名并输出到 result_dir 中，作为后续的安装文件下载依据。
"""

import os

import demjson

app_list_dir = '../files/applist'
result_dir = '../files/packagelist'

for json_name in os.listdir(app_list_dir):
    json_path = os.path.join(app_list_dir, json_name)
    category, _ = os.path.splitext(json_name)
    if not json_name.startswith('.'):
        package_list_fp = os.path.join(result_dir, category + '.lst')
        open(package_list_fp, 'w')
        print('processing', json_path, '...')
        with open(json_path, 'rb') as f:
            json_data = demjson.decode(f.read())
        for item in json_data['results']:
            try:
                if item['free']:
                    open(package_list_fp, 'a').write(item['appId'] + '\n')
            except TypeError:
                print('Not a float')
        print(json_path, 'processed.')
