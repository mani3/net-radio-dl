## ffmpeg

ここから `ffmpeg-git-amd64-static.tar.xz` をダウンロードして `ffmpeg` を bin の下に置く

- https://johnvansickle.com/ffmpeg/


## swfextract

AWS Lambda 上で実行できる `swftools` をビルドする

```
❯ /path/to/net-radio-dl
❯ docker run -v "$PWD":/var/task  -it lambci/lambda:build-python3.8 bash
$ yum install -y zlib-devel libjpeg-devel giflib-devel freetype-devel gcc gcc-c++
$ curl -O http://www.swftools.org/swftools-0.9.2.tar.gz
$ tar -zxvf swftools-0.9.2.tar.gz
$ cd swftools-0.9.2
$ ./configure
$ make
$ cp ..
$ cp /usr/local/bin/swfextract bin/
$ cp /lib64/libgif.so* lib/
$ cp /lib64/libjpeg.so* lib/
$ cp /lib64/libpng.so* lib/
$ cp /lib64/libfreetype.so* lib/
$ cp /lib64/libSM.so* lib/
$ cp /lib64/libICE.so* lib/
$ cp /lib64/libpng15.so* lib/
$ cp /lib64/libxcb.so* lib/
$ cp /lib64/libX11.so* lib/
$ cp /lib64/libXau.so* lib/
$ cp /lib64/libuuid.so* lib/
```
