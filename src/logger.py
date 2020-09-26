import json
import logging
import traceback


class FormatterJSON(logging.Formatter):
  def format(self, record):
    record.message = record.getMessage()
    if self.usesTime():
      record.asctime = self.formatTime(record, self.datefmt)
    j = {
        'logLevel': record.levelname,
        'timestamp': '%(asctime)s.%(msecs)dZ' % dict(
            asctime=record.asctime, msecs=record.msecs),
        'timestamp_epoch': record.created,
        'aws_request_id': getattr(
            record, 'aws_request_id', '00000000-0000-0000-0000-000000000000'),
        'message': record.message,
        'module': record.module,
        'filename': record.filename,
        'funcName': record.funcName,
        'levelno': record.levelno,
        'lineno': record.lineno,
    }
    if record.exc_info:
      exception_data = traceback.format_exc().splitlines()
      j['traceback'] = exception_data

    stats = record.__dict__.get('stats', None)
    if stats:
      j['stats'] = stats
    return json.dumps(j, ensure_ascii=False)

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = FormatterJSON(
  '[%(levelname)s]\t%(asctime)s.%(msecs)dZ\t%(levelno)s\t%(message)s\n',
  '%Y-%m-%dT%H:%M:%S'
)
# Replace the LambdaLoggerHandler formatter
if len(logger.handlers) > 0:
  logger.handlers[0].setFormatter(formatter)
