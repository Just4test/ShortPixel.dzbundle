# Dropzone Action Info
# Name: ShortPixel
# Description: Use shortpixel to compress images
# Handles: Files
# Creator: Just4test
# URL: https://github.com/Just4test/shortpixel.dzbundle
# Events: Dragged
# KeyModifiers: Command, Option, Control, Shift
# OptionsNIB: APIKey
# SkipConfig: No
# RunsSandboxed: No
# Version: 1.0
# MinDropzoneVersion: 3.5
# PythonPath: /usr/local/bin/python3

import sys
if not ('packages' in sys.path):
    sys.path.insert(0, 'packages')

import os
import json
import base64
import requests
from requests_toolbelt import (MultipartEncoder, MultipartEncoderMonitor)

APIKEY = os.environ['api_key']

ACCEPT_EXTENSION_NAME = ['.jpg','.jpeg','.png','.gif','.bmp','.tiff','.pdf']
UPLOAD_BATCH_NUMBER = 10
UPLOAD_BATCH_SIZE = 100*1024*1024

def readable_size(size):
    K = 1024
    M = K * K
    G = M * K
    if size > 10 * G:
        return '{:.0f} GB'.format(size / G)
    if size > G:
        return '{:.1f} GB'.format(size / G)
    if size > 10 * M:
        return '{:.0f} MB'.format(size / M)
    if size > 1024 * 1024:
        return '{:.1f} MB'.format(size / M)
    if size > 1024 * 10:
        return '{:.0f} KB'.format(size / K)
    if size > 1024:
        return '{:.1f} KB'.format(size / K)
    return '{} B'.format(size)

images = {}
total_filesnum = 0
total_filesize = 0
def add(path):
    def add_file(filepath):
        name, ext = os.path.splitext(filepath)
        if ext.lower() in ACCEPT_EXTENSION_NAME and os.path.isfile(filepath):
            filesize = os.path.getsize(filepath)
            images[filepath] = {'size':filesize, 'save_as':f'{name}_compressed{ext}'}
            global total_filesnum, total_filesize
            total_filesnum += 1
            total_filesize += filesize
    def add_dir(dirpath):
        for root, dirs, files in os.walk(dirpath):
            for name in files:
                add_file(os.path.join(root, name))
            for name in dirs:
                add_dir(os.path.join(root, name))
            
    if os.path.isdir(path):
        add_dir(path)
    else:
        add_file(path)
        
upload_count = 0
upload_size = 0

download_count = 0
faild_count = 0
successd_source_size = 0
successd_compressed_size = 0

progress_size = 0
old_percent = 0
def set_progress(n):
    n = int(n)
    global old_percent
    if n != old_percent:
        dz.percent(n)
        old_percent = n


def compress(images, batch_size):
    print(images, batch_size)
    global upload_count, upload_size, download_count
    
    # upload
    url = 'http://api.shortpixel.com/v2/post-reducer.php'
    for path, imgdata in images.items():
        upload_count += 1
        dz.begin(f'Uploading {upload_count}/{total_filesnum} {path.split("/")[-1]}')
        def progress_callback(monitor):
            set_progress((upload_size + imgdata['size'] * (monitor.bytes_read / monitor.len)) / (total_filesize * 2) * 100)
        
        fields = [
            ('key', APIKEY),
            ('lossy', '1'),
            ('wait', '0'),
            ('file_paths', '{"1": "xxxxxx"}'),
            ('file', ('1', open(path, 'rb')))
        ]
        
        
        m = MultipartEncoder(fields=fields)
        m = MultipartEncoderMonitor(m, progress_callback)
        print(dir(m))
        r = requests.post(url, data=m, headers={'Content-Type': m.content_type})
        
        
        try:
            temp = r.json()[0]
            if int(temp['Status']['Code']) != 1:
                print('Faild!', path, imgdata['r']['Status'])
            else:
                imgdata['r'] = temp
        except Exception as e:
            print('Faild when Upload!', path, e)
        
        upload_size += imgdata['size']
        
    # download
    
    url = 'http://api.shortpixel.com/v2/reducer.php'
    for path, imgdata in images.items():
        download_count += 1
        dz.begin(f'Waiting for compression {download_count}/{total_filesnum} {path.split("/")[-1]}')
        if 'r' not in imgdata or 'Status' not in imgdata['r']:
#            print('Faild Upload!', path)
            continue
            
        data = json.dumps({
            'key': APIKEY,
            'lossy': 1,
            'wait':30,
            'urllist': [imgdata['r']['OriginalURL']]
        })
        while True:
            r = requests.post(url=url, data=data)
            temp = r.json()[0]
            print(temp)
            if int(temp['Status']['Code']) == 1:
                continue
            if int(temp['Status']['Code']) != 2:
                #TODO
                print('Error!', path, temp)
                sys.exit(1)
            break;
            
        dz.begin(f'Downloading {download_count}/{total_filesnum} {path.split("/")[-1]}')
        r = requests.get(temp['LossyURL'], stream=True)
        size = int(r.headers.get('content-length', 0))
        write_size = 0
        with open(imgdata['save_as'], 'wb') as f:
            for i in r.iter_content(chunk_size=1024*256):
                f.write(i)
                write_size += len(i)
                set_progress((upload_size + imgdata['size'] * (write_size / size)) / (total_filesize * 2) * 100)
        if write_size != size:
            print('Faild download!', path)
            os.remove(imgdata['save_as'])
        upload_size += imgdata['size']
        
def work():
    count = 0
    size = 0
    temp = {}
    
    def work_batch():
        nonlocal count, size, temp
        if count == 0:
            return
        compress(temp, size)
        count = 0
        size = 0
        temp = {}
        
    for path, data in list(images.items()):
        if count >= UPLOAD_BATCH_NUMBER or size >= UPLOAD_BATCH_SIZE:
            work_batch()
        count += 1
        size += data['size']
        temp[path] = data
    work_batch()
    
    
        
        
        


def dragged():
    print(items)
    dz.begin(f'Checking images...')
    for path in items:
        print('!!!!!!!!', path)
        add(path)
#    upload(images)
    dz.begin(f'Start compress {readable_size(total_filesize)} of {total_filesnum} files...')
    dz.determinate(True)
    work()
    dz.finish('OK')
    dz.url(False)