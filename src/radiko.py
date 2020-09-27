#!/usr/bin/env python

import os
import base64
import subprocess
import datetime

import urllib
import urllib.parse
import urllib.request

try:
  import unzip_requirements
except ImportError:
  pass

import requests

from src import logger
from src import radio
from src import s3

logger = logger.logger
os.environ['PATH'] = os.environ['PATH'] + ':/var/task/bin'

SITE_NAME = 'radiko'
RADIKO_CONFIG = [
  {'station_id': 'QRR', 'wd': 5, 'ft': '010000', 'to': '013000', 'name': 'tenshinotamago'},
  {'station_id': 'QRR', 'wd': 6, 'ft': '000000', 'to': '003000', 'name': 'kawaikaro'},
  {'station_id': 'QRR', 'wd': 0, 'ft': '210000', 'to': '213000', 'name': 'toretore'},
  {'station_id': 'QRR', 'wd': 6, 'ft': '233000', 'to': '240000', 'name': 'smilegang'},
  {'station_id': 'TBS', 'wd': 0, 'ft': '000000', 'to': '003000', 'name': 'tokyoboogienight'},
  {'station_id': 'FMT', 'wd': 0, 'ft': '210000', 'to': '213000', 'name': 'mnosekai'},
  {'station_id': 'QRR', 'wd': 6, 'ft': '220000', 'to': '223000', 'name': 'melodyflag'},
  {'station_id': 'QRR', 'wd': 3, 'ft': '213000', 'to': '220000', 'name': 'otomegokoro'},
]


def download_authkey():
  url = os.environ.get('RADIKO_SWF_URL', '')
  filepath = os.path.join(os.sep, 'tmp', 'player-release.swf')
  authkey_path = os.path.join(os.sep, 'tmp', 'authkey.png')

  with open(filepath, "wb") as f:
    res = requests.get(url)
    f.write(res.content)
  # subprocess.Popen(['swfextract', filepath, '-b', '12', '-o', authkey_path], stdout=subprocess.PIPE)
  subprocess.call(['swfextract', filepath, '-b', '12', '-o', authkey_path])

# Download authkey.png
download_authkey()


class Radiko(object):
  AUTH_KEY_PATH = os.path.join(os.sep, 'tmp', 'authkey.png')
  AUTH1_URL = os.environ.get('RADIKO_AUTH1_URL', '')
  AUTH2_URL = os.environ.get('RADIKO_AUTH2_URL', '')
  STREAM_URL = os.environ.get('RADIKO_STREAM_URL', '')

  def __init__(self):
    authToken, partialKey = self.auth1()
    self.authToken = authToken
    res = self.auth2(authToken, partialKey)
    logger.info('End radiko auth', extra={'stats': {'auth2_res': res}})

  def auth1(self):
    url = self.AUTH1_URL
    data = '\r\n'
    headers = self.auth1_headers()
    req = urllib.request.Request(url, data.encode(), headers)

    res = {}
    with urllib.request.urlopen(req) as body:
      text = body.read().decode('utf-8')
      for line in text.split('\n'):
        line = line.rstrip()
        if line.find('=') != -1:
          key, value = line.split('=')
          res[key] = value

    logger.info(f'auth1: {str(res)}')

    authToken  = res['X-RADIKO-AUTHTOKEN']
    keyOffset = int(res['X-Radiko-KeyOffset'])
    keyLength = int(res['X-Radiko-KeyLength'])
    with open(self.AUTH_KEY_PATH, 'rb') as f:
      f.seek(keyOffset)
      partialKey = base64.b64encode(f.read(keyLength))
    return authToken, partialKey

  def auth2(self, authToken, partialKey):
    url = self.AUTH2_URL
    data = '\r\n'
    headers = self.auth2_headers(authToken, partialKey)
    req = urllib.request.Request(url, data.encode(), headers)

    with urllib.request.urlopen(req) as body:
      text = body.read().decode('utf-8').rstrip()
    logger.info(f'auth2: {text}')
    return text

  def stream_url(self, station_id, ft, to):
    params = {
      'station_id': station_id,
      'l': '15',
      'ft': ft,
      'to': to
    }
    q = '&'.join([f'{k}={v}' for k, v in params.items()])
    return f'{self.STREAM_URL}?{q}'

  def auth1_headers(self):
    headers = {
      'X-Radiko-App': 'pc_ts',
      'X-Radiko-App-Version': '4.0.0',
      'X-Radiko-User': 'test-stream',
      'X-Radiko-Device':'pc'
    }
    return headers

  def auth2_headers(self, authToken, partialKey):
    headers = {
      'X-Radiko-App': 'pc_ts',
      'X-Radiko-App-Version': '4.0.0',
      'X-Radiko-User': 'test-stream',
      'X-Radiko-Device': 'pc',
      'X-Radiko-Authtoken': authToken,
      'X-Radiko-Partialkey': partialKey
    }
    return headers  


def main(event, context):
  logger.info(event)
  radiko = Radiko()

  for param in RADIKO_CONFIG:
    try:
      name = param['name']
      now = datetime.datetime.now()
      days = (now.weekday() - param['wd']) % 7
      days = 7 if days == 0 else days
      date = now - datetime.timedelta(days=days)

      id = param['station_id']
      ft = date.strftime('%Y%m%d') + param['ft']
      to = date.strftime('%Y%m%d') + param['to']
    
      filename = f'{ft}_{to}.m4a'
      key = os.path.join('contents', SITE_NAME, name, filename)
      output_path = os.path.join(os.sep, 'tmp', filename)

      if not s3.is_exist(s3.bucket_name, key):
        streaming_url = radiko.stream_url(id, ft, to)
        headers = f'X-Radiko-AuthToken: {radiko.authToken}'
        logger.info('Download start', extra={'stats': {'streaming_url': streaming_url, 'headers': headers}})
        radio.download(streaming_url, output_path, headers)
        s3.upload_media(output_path, s3.bucket_name, key)
      else:
        logger.info(f'File exist: {key}')
    except Exception as e:
      logger.error(str(e))


if __name__ == "__main__":
  main(None, None)
