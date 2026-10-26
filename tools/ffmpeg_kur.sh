#!/usr/bin/env bash
# FFmpeg + fontları kurar. Ubuntu paket sunucuları takılırsa GitHub'daki hazır FFmpeg sürümünü indirir.
PKGS="ffmpeg fonts-liberation fonts-dejavu-core"
OPTS="-o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 -o Acquire::Retries=2 -o DPkg::Lock::Timeout=60"
if timeout 150 sudo apt-get install -y -qq $OPTS $PKGS > /dev/null 2>&1; then
  echo "FFmpeg kuruldu (apt)"
elif timeout 300 bash -c "sudo apt-get update -qq $OPTS && sudo apt-get install -y -qq $OPTS $PKGS" > /dev/null 2>&1; then
  echo "FFmpeg kuruldu (apt, güncelleme sonrası)"
else
  echo "Paket sunucusu yanıt vermedi: hazır FFmpeg indiriliyor"
  sudo pkill -f apt-get || true
  curl -fsSL --retry 3 https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz \
    | tar xJ -C /tmp
  sudo cp /tmp/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg /tmp/ffmpeg-master-latest-linux64-gpl/bin/ffprobe /usr/local/bin/
fi
ffmpeg -version | head -1
