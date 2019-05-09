import os
import platform
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from configparser import ConfigParser

from decomp.layout_utils import optimize_sequence
from utils.logging import Loggers

cfg = ConfigParser()
cfg.read('../config.ini')

apk_dir = cfg.get('decode', 'apk_dir')
temp_dir = cfg.get('decode', 'temp_dir')
apk_tokens_dir = cfg.get('decode', 'apk_tokens_dir')

android_jars = cfg.get('decode', 'android_jars')
soot_jar = cfg.get('decode', 'soot_jar')
soot_output = cfg.get('decode', 'soot_output')

log_dir = cfg.get('log', 'log_dir')

TIME_OUT = 300


def remove_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


if __name__ == '__main__':

    log = Loggers(level='debug', log_dir=log_dir)

    file_abps = []

    for f in os.listdir(apk_dir):
        category_dir = os.path.join(apk_dir, f)
        if os.path.isdir(category_dir):  # category
            for sub_dir in os.listdir(category_dir):
                sub_dp = os.path.join(category_dir, sub_dir)
                if os.path.isdir(sub_dp):  # apk_subdir
                    for package_name in os.listdir(os.path.join(sub_dp)):
                        fp = os.path.join(sub_dp, package_name)
                        if os.path.isfile(fp) and fp.endswith('.apk') and not fp.startswith('.'):
                            file_abps.append(fp)

    log.logger.info('Layout extraction on ' + str(len(file_abps)) + ' APK(s) started.')

    for i, apk_path in enumerate(file_abps):
        # file_name = os.path.splitext(file)[0]
        # apk_path = os.path.join(apk_dir, file)
        _, apk_name = os.path.split(apk_path)
        apktool_out_path = os.path.join(temp_dir, apk_name)

        start_time = time.time()
        log.logger.info('(' + str(i + 1) + '/' + str(len(file_abps)) + ') Analysis started on ' + apk_path)

        # 执行 apktool 命令
        if platform.system() == 'Windows':
            subprocess.call(['apktool', 'd', apk_path, '-f', '-o', apktool_out_path], shell=True)
        else:
            subprocess.call(['apktool', 'd', apk_path, '-f', '-o', apktool_out_path])

        # 检查 apktool 结果目录的状态
        if not os.path.isdir(apktool_out_path):
            log.logger.error('Apktool decoding failed.')
            continue

        # 获取包名作为标识符
        package = None
        manifest_fp = os.path.join(apktool_out_path, 'AndroidManifest.xml')
        if os.path.isfile(manifest_fp):
            try:
                e = ET.parse(manifest_fp).getroot()
                if e.tag == 'manifest':
                    package = e.attrib['package']
                    log.logger.info('APK package is parsed: ' + package)
            except ET.ParseError as e:
                # 解析错误跳过
                log.logger.error('AndroidManifest.xml parsed error.')
                continue
        if package is None:
            package = apk_name
            log.logger.info('APK package is not parsed, using ' + package + ' to substitute.')

        if not os.path.exists(soot_output):
            os.makedirs(soot_output)

        cmd = ['java', '-jar', soot_jar,
               '-d', soot_output,
               '-android-jars', android_jars,
               '-package', package,
               '-process-dir', apk_path,
               '-apktool-dir', apktool_out_path,
               '-token-dir', apk_tokens_dir,
               '-process-multiple-dex', '-allow-phantom-refs']

        log.logger.info('Soot analysis is running (time out = ' + str(TIME_OUT) +
                        's). The output will display after the subprocess ended.')

        # 执行 soot 程序并处理返回
        try:
            out_bytes = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=TIME_OUT)
        except subprocess.TimeoutExpired as e:
            # 处理超时异常
            log.logger.error(str(type(e)) + ' Soot analysis times out >>> Skip ' + apk_path)
            log.logger.error(e.output)
        except subprocess.CalledProcessError as e:
            # 处理调用失败异常
            log.logger.error(str(type(e)))
            utf_message = e.output.decode('utf-8', 'ignore')
            log.logger.error(e.output)
        else:
            print(out_bytes.decode('utf-8', 'ignore'))
            tmp_tokens_fp = os.path.join(apk_tokens_dir, package + '-layout.tmp.lst')
            tokens_fp = os.path.join(apk_tokens_dir, package + '-layout.lst')
            log.logger.info('Soot finished. Start optimizing soot outputted layout.')
            if os.path.isfile(tmp_tokens_fp):
                with open(tokens_fp, 'w') as wf:
                    line_cnt = 0
                    with open(tmp_tokens_fp, 'r') as rf:
                        for j, line in enumerate(rf):
                            line_sp = line.split()
                            layout_type = int(line_sp[0])
                            xml_name = line_sp[1]
                            tokens = line_sp[2:]
                            opt_tokens, opt_seq = optimize_sequence(' '.join(tokens))
                            wf.write(
                                str(layout_type) + ' ' + xml_name + ' ' + str(len(opt_tokens)) + ' ' + opt_seq + '\n')
                            line_cnt = j + 1
                if line_cnt == 0:
                    os.remove(tokens_fp)
                os.remove(tmp_tokens_fp)
        finally:
            remove_dir(apktool_out_path)  # 删除 apktool 生成目录，如果需要可以注释这一行
            remove_dir(soot_output)
            log.logger.info('Intermediate files produced by Soot and Apktool are removed.')
            log.logger.info(
                'Analysis on ' + apk_path + ' finished. It has run for {:.2f} s.'.format(time.time() - start_time))

    log.logger.info('Layout extraction on ' + str(len(file_abps)) + ' APK(s) finished.')
