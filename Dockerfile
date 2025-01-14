FROM ubuntu:jammy
RUN apt-get update -y && apt-get upgrade -y \
    && apt-get install -y git libxrender1 python3-pip \
    && apt-get install -y ffmpeg && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
COPY . /app/
WORKDIR /app/

RUN pip3 install -r requirements.txt --force-reinstall

CMD python3 -m RishuMusic
