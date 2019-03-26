import os
import platform
import shutil
import subprocess
import time
from configparser import ConfigParser

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

TIME_OUT = 240


def remove_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)


if __name__ == '__main__':

    log = Loggers(level='debug', log_dir=log_dir)

    files = [f for f in os.listdir(apk_dir)
             if os.path.isfile(os.path.join(apk_dir, f)) and f.endswith('.apk') and not f.startswith('.')]

    log.logger.info('Layout extraction on ' + str(len(files)) + ' APK(s) started.')

    for i, file in enumerate(files):
        file_name = os.path.splitext(file)[0]
        apk_path = os.path.join(apk_dir, file)
        apktool_out_path = os.path.join(temp_dir, file_name)

        start_time = time.time()
        log.logger.info('(' + str(i + 1) + '/' + str(len(files)) + ') Analysis on ' + file + ' started.')

        # 执行 apktool 命令
        if platform.system() == 'Windows':
            subprocess.call(['apktool', 'd', apk_path, '-f', '-o', apktool_out_path], shell=True)
        else:
            subprocess.call(['apktool', 'd', apk_path, '-f', '-o', apktool_out_path])

        # 检查 apktool 结果目录的状态
        if not os.path.isdir(apktool_out_path):
            log.logger.error('Apktool decoding failed.')
            continue

        if not os.path.exists(soot_output):
            os.makedirs(soot_output)

        cmd = ['java', '-jar', soot_jar,
               '-d', soot_output,
               '-android-jars', android_jars,
               '-package', file_name,
               '-process-dir', apk_path,
               '-apktool-dir', apktool_out_path,
               '-token-dir', apk_tokens_dir,
               '-process-multiple-dex', '-allow-phantom-refs']

        log.logger.info('Soot analysis is running (time out = ' + str(TIME_OUT) +
                        's). The execution output will be shown in the console after the subprocess ended.')

        # 执行 soot 程序并处理返回
        try:
            out_bytes = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=TIME_OUT)
        except subprocess.TimeoutExpired as e:
            # 处理超时异常
            log.logger.error(e.output.decode('utf-8', 'replace'))
            log.logger.error(str(type(e)) + ' Soot analysis times out >>> Skip ' + file)
        except subprocess.CalledProcessError as e:
            # 处理调用失败异常
            log.logger.error(e.output.decode('utf-8', 'replace'))
            log.logger.error(str(type(e)))
        else:
            print(out_bytes.decode('utf-8', 'replace'))
            log.logger.info('Soot finished. The layout sequences are saved in ' + apk_tokens_dir)
        finally:
            log.logger.info('Removing intermediate files (Apktool files).')
            # remove_dir(apktool_out_path)  # 删除 apktool 生成目录，如果需要可以注释这一行
            remove_dir(soot_output)
            log.logger.info(
                'Analysis on ' + file + ' finished. It has run for {:.2f} s'.format(time.time() - start_time))

    log.logger.info('Layout extraction on ' + str(len(files)) + ' APK(s) finished.')
