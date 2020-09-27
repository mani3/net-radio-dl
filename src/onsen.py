import os
import time
import json
import urllib
import urllib.parse
import urllib.request

from datetime import datetime
from urllib.request import build_opener

try:
  import unzip_requirements
except ImportError:
  pass

import boto3
import botocore

from src import logger
from src import radio


logger = logger.logger

session = boto3.Session(region_name='ap-northeast-1')
s3 = session.client('s3')
bucket_name = os.environ.get('NET_RADIO_S3_BUCKET', '')

os.environ['PATH'] = ':/var/task/bin'
SITE_NAME = 'onsen'
ONSEN_URL = os.environ.get('ONSEN_URL', '')

ONSEN_CONFIG = {
  0: ['miabyss', 'tate'],
  1: ['teibo'],
  2: ['matsui'],
  3: ['ippo', 'yurucamp'],
  4: ['bullet', 'railgun_t', 'koihime'],
  5: ['yujincho', 'gochiusabloom', 'dolls'],
  6: ['survey', 'watahana', 'hxeros', 'fujita', 'matsui'],
}


def get_program(program_name):
  body = None
  url = os.path.join(ONSEN_URL, program_name)
  req = urllib.request.Request(url)
  with urllib.request.urlopen(req) as res:
    body = json.load(res)
  return body


def upload_json(json_dict, s3, bucket, program_name):
  now = datetime.now()
  filename = now.strftime("%Y%m%d_%H%M%S.json")

  tmp_path = os.path.join(os.sep, 'tmp', filename)
  key = os.path.join('programs', SITE_NAME, program_name, filename)

  try:
    with open(tmp_path, 'w') as f:
      json.dump(json_dict, f, ensure_ascii=False)
    s3.upload_file(tmp_path, bucket, key)
    os.remove(tmp_path)
  except Exception as e:
    logger.error(str(e))


def is_exist(bucket, key):
  try:
    s3.head_object(Bucket=bucket, Key=key)
    return True
  except botocore.errorfactory.ClientError as e:
    return False


def upload_media(filepath, s3, bucket, key):
  try:
    start_time = time.time()
    s3.upload_file(filepath, bucket, key)
    stats = {'upload_time': time.time() - start_time, 'key': key}
    logger.info('Upload time', extra={'stats': stats})
    os.remove(filepath)
  except Exception as e:
    logger.error(str(e))


def main(event, context):
  logger.info(event)

  weekday = datetime.today().weekday()
  program_list = ONSEN_CONFIG[weekday]

  for program_name in program_list:
    try:
      json_dict = get_program(program_name)
      upload_json(json_dict, s3, bucket_name, program_name)

      for content_dict in json_dict['contents']:
        id = content_dict.get('id', 0)
        streaming_url = content_dict.get('streaming_url', None)
        is_movie = content_dict.get('movie', False)
        ext = 'mp4' if is_movie else 'm4a'
        filename = f'{id}.{ext}'

        if streaming_url is None:
          logger.info('streaming_url is nll', extra={'stats': content_dict})
          continue

        key = os.path.join('contents', SITE_NAME, program_name, filename)
        output_path = os.path.join(os.sep, 'tmp', filename)

        if not is_exist(bucket_name, key):
          radio.download(streaming_url, output_path)
          upload_media(output_path, s3, bucket_name, key)
        else:
          logger.info(f'File exist: {key}')
    except Exception as e:
      logger.error(str(e))


if __name__ == "__main__":
  main(None, None)
