#!/usr/bin/env python

import os
import re
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
  {'station_id': 'QRR', 'wd': 5, 'ft': '023000', 'to': '030000', 'name': 'anisondaysplus'},
  {'station_id': 'QRR', 'wd': 0, 'ft': '003000', 'to': '010000', 'name': 'yuiroom'},
  {'station_id': 'QRR', 'wd': 5, 'ft': '190000', 'to': '200000', 'name': 'requesthour1'},
  {'station_id': 'QRR', 'wd': 5, 'ft': '200000', 'to': '210000', 'name': 'requesthour2'},
  {'station_id': 'QRR', 'wd': 6, 'ft': '223000', 'to': '230000', 'name': 'funs_project_lab'},
  {'station_id': 'QRR', 'wd': 6, 'ft': '230000', 'to': '233000', 'name': 'tenipuri'},
  {'station_id': 'QRR', 'wd': 0, 'ft': '000000', 'to': '003000', 'name': 'dragalia_lost'},
  {'station_id': 'FMT', 'wd': 4, 'ft': '230000', 'to': '232700', 'name': 'lisa_locks'},
  {'station_id': 'TBS', 'wd': 3, 'ft': '213000', 'to': '220000', 'name': 'd4dj'},
  {'station_id': 'QRR', 'wd': 0, 'ft': '010000', 'to': '013000', 'name': 'radio-hamamatsucho'},
  {'station_id': 'BAYFM78', 'wd': 5, 'ft': '013000', 'to': '020000', 'name': 'vitamin_m'},
  {'station_id': 'FMT', 'wd': 1, 'ft': '050000', 'to': '053000', 'name': 'memories_discoveries'},
  {'station_id': 'FMT', 'wd': 2, 'ft': '050000', 'to': '053000', 'name': 'memories_discoveries'},
  {'station_id': 'FMT', 'wd': 3, 'ft': '050000', 'to': '053000', 'name': 'memories_discoveries'},
]


class Radiko(object):
  AUTH_KEY_PATH = os.path.join(os.sep, 'tmp', 'authkey.png')
  RADIKO_PLAYER_URL = os.environ.get('RADIKO_PLAYER_URL', '')
  AUTH1_URL = os.environ.get('RADIKO_AUTH1_URL', '')
  AUTH2_URL = os.environ.get('RADIKO_AUTH2_URL', '')
  STREAM_URL = os.environ.get('RADIKO_STREAM_URL', '')

  def __init__(self):
    self.auth_key = self.get_auth_key()
    authToken, partialKey = self.auth1()
    self.authToken = authToken
    res = self.auth2(authToken, partialKey)
    logger.info('End radiko auth', extra={'stats': {'auth2_res': res}})

  def get_auth_key(self):
    req = urllib.request.Request(self.RADIKO_PLAYER_URL)
    with urllib.request.urlopen(req) as body:
      text = body.read().decode('utf-8')
    pattern = r".*new RadikoJSPlayer\(.*'pc_html5',\s'(\w+)'.*"
    auth_key = re.match(pattern, text, re.S).group(1)
    logger.info(f'auth_key: {auth_key}', extra={'stats': {'auth_key': auth_key}})
    return auth_key

  def auth1(self):
    url = self.AUTH1_URL
    headers = self.auth1_headers()
    req = urllib.request.Request(url, None, headers)

    res = {}
    with urllib.request.urlopen(req) as body:
      text = body.read().decode('utf-8')
      for key, value in body.headers.items():
        res[key.lower()] = value

    logger.info(f'auth1: {str(res)}', extra={'stats': {'text': text, 'auth1': res}})

    authToken  = res['X-Radiko-AuthToken'.lower()]
    keyOffset = int(res['X-Radiko-KeyOffset'.lower()])
    keyLength = int(res['X-Radiko-KeyLength'.lower()])

    byte = self.auth_key[keyOffset:keyOffset + keyLength]
    partialKey = base64.b64encode(byte.encode())
    return authToken, partialKey

  def auth2(self, authToken, partialKey):
    url = self.AUTH2_URL
    headers = self.auth2_headers(authToken, partialKey)
    req = urllib.request.Request(url, None, headers)

    res = {}
    with urllib.request.urlopen(req) as body:
      text = body.read().decode('utf-8').rstrip()
      for key, value in body.headers.items():
        res[key.lower()] = value
    logger.info(f'auth2: {text}', extra={'stats': {'headers': res}})
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
      'X-Radiko-App': 'pc_html5',
      'X-Radiko-App-Version': '0.0.1',
      'X-Radiko-User': 'dummy_user',
      'X-Radiko-Device':'pc'
    }
    return headers

  def auth2_headers(self, authToken, partialKey):
    headers = {
      # 'X-Radiko-App': 'pc_html5',
      # 'X-Radiko-App-Version': '0.0.1',
      'X-Radiko-User': 'dummy_user',
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
  try:
    main(None, None)
  except urllib.error.HTTPError as e:
    print('HTTPError: {}, {}'.format(e.code, e.read()))
  except urllib.error.URLError as e:
    print('URLError: {}'.format(e.reason))
