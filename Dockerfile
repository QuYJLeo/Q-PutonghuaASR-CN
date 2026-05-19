FROM registry-crs-huadong1.ctyun.cn/hs/kylin-server-v10sp3-aarch64:20250530
WORKDIR /opt/hs-asr-funasr-large-server
COPY hs-asr-funasr-large-server/ /opt/hs-asr-funasr-large-server/
EXPOSE 6800 6060

# 指定容器启动时运行的命令
CMD ["./asr-server"]


