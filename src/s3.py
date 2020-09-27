import os
import time

try:
  import unzip_requirements
except ImportError:
  pass

import boto3
import botocore

from src import logger


logger = logger.logger

session = boto3.Session(region_name='ap-northeast-1')
s3 = session.client('s3')
bucket_name = os.environ.get('NET_RADIO_S3_BUCKET', '')

def is_exist(bucket, key):
  try:
    s3.head_object(Bucket=bucket, Key=key)
    return True
  except botocore.errorfactory.ClientError as e:
    return False

def upload_media(filepath, bucket, key):
  try:
    start_time = time.time()
    s3.upload_file(filepath, bucket, key)
    stats = {'upload_time': time.time() - start_time, 'key': key}
    logger.info('Upload time', extra={'stats': stats})
    os.remove(filepath)
  except Exception as e:
    logger.error(str(e))
