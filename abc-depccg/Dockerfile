FROM nvidia/cuda:10.1-cudnn7-runtime
LABEL maintainer="T. N. Hayashi <net@hayashi-lin.net>"
LABEL version="20190814"
LABEL description="VM for ABC Treebank Machine Learning"

RUN apt update \
    && apt install -y --no-install-recommends \
        make \
        gcc \
        g++ \
        libgomp1 \
        python3-dev \
        python3-wheel \
        python3-setuptools \
        python3-pip \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

ARG USE_OPENMP=1
RUN pip3 install --no-cache-dir \
        cython numpy cupy-cuda101 janome allennlp \
    && pip3 install --no-cache-dir depccg

ADD ./lex-model-depccg-ja.tar.gz /root/lex-model-depccg-ja
ADD ./keyaki-treebank.tar.gz /root/treebank
ADD ./vector-wikija.tar.bz2 /root/vector-wikija
ADD ./supertagger.jsonnet /root/
ADD ./script.py /usr/local/bin/train
RUN chmod 755 /usr/local/bin/train
ADD ./parser.py /usr/local/bin/parse
RUN chmod 755 /usr/local/bin/parse

ENV LC_ALL C.UTF-8