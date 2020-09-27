
import time
import ffmpeg

from src import logger

logger = logger.logger

def download(input_url: str, output_path: str, headers=''):
  start_time = time.time()
  (
    ffmpeg
    .input(input_url, headers=headers)
    .output(output_path)
    .run(capture_stdout=False, capture_stderr=True)
  )
  stats = {'ffmpeg_download_time': time.time() - start_time}
  logger.info('ffmpeg download time', extra={'stats': stats})
