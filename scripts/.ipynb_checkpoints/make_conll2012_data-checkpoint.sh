#!/bin/bash

# ONTONOTES_PATH=$1
ONTONOTES_PATH="./conll-formatted-ontonotes-5.0"

SRL_PATH="./data/conll2012"
if [ ! -d $SRL_PATH ]; then
  mkdir -p $SRL_PATH
fi


# Preprocess CoNLL formatted files.

rm -f ${SRL_PATH}/train.english.v5_gold_conll
python3 ./concatenate_gold_skel.py ${ONTONOTES_PATH}/data/train/data/english/annotations/ ${SRL_PATH}/train.english.v5_gold_conll
# cat ${ONTONOTES_PATH}/data/train/data/english/annotations/*/*/*/*.gold_skel \
#   >> ${SRL_PATH}/train.english.v5_gold_conll

rm -f ${SRL_PATH}/dev.english.v5_gold_conll
python3 ./concatenate_gold_skel.py ${ONTONOTES_PATH}/data/development/data/english/annotations/ ${SRL_PATH}/dev.english.v5_gold_conll
# cat ${ONTONOTES_PATH}/data/development/data/english/annotations/*/*/*/*.gold_skel \
#   >> ${SRL_PATH}/dev.english.v5_gold_conll

rm -f ${SRL_PATH}/conll12test.english.v5_gold_conll
python3 ./concatenate_gold_skel.py ${ONTONOTES_PATH}/data/conll-2012-test/data/english/annotations/ ${SRL_PATH}/conll12test.english.v5_gold_conll
# cat ${ONTONOTES_PATH}/data/conll-2012-test/data/english/annotations/*/*/*/*.gold_skel \
#   >> ${SRL_PATH}/conll12test.english.v5_gold_conll

python3 ontonotes5_to_json.py ${SRL_PATH}/train.english.v5_gold_conll \
  ${SRL_PATH}/train.english.v5.jsonlines
python3 ontonotes5_to_json.py ${SRL_PATH}/dev.english.v5_gold_conll \
  ${SRL_PATH}/dev.english.v5.jsonlines
python3 ontonotes5_to_json.py ${SRL_PATH}/conll12test.english.v5_gold_conll \
  ${SRL_PATH}/conll12test.english.v5.jsonlines


# Filter data for e2e experiments. (wget is recognized as a robot and you have to download these files manually.)
#wget http://conll.cemantix.org/2012/download/ids/english/coref/train.id -O ${SRL_PATH}/conll12.train.id
#wget http://conll.cemantix.org/2012/download/ids/english/coref/development.id -O ${SRL_PATH}/conll12.dev.id
#wget http://conll.cemantix.org/2012/download/ids/english/coref/test.id -O ${SRL_PATH}/conll12.test.id

python3 filter_conll2012_data.py ${SRL_PATH}/train.english.v5.jsonlines \
  ${SRL_PATH}/conll12.train.id \
  ${SRL_PATH}/train.english.mtl.jsonlines

python3 filter_conll2012_data.py ${SRL_PATH}/dev.english.v5.jsonlines \
  ${SRL_PATH}/conll12.dev.id \
  ${SRL_PATH}/dev.english.mtl.jsonlines

python3 filter_conll2012_data.py ${SRL_PATH}/conll12test.english.v5.jsonlines \
  ${SRL_PATH}/conll12.test.id \
  ${SRL_PATH}/test.english.mtl.jsonlines


python3 ./preprocess.py ${SRL_PATH}/train.english.mtl.jsonlines   ${SRL_PATH}/train.english.conll12.json
python3 ./preprocess.py ${SRL_PATH}/dev.english.mtl.jsonlines   ${SRL_PATH}/dev.english.conll12.json
python3 ./preprocess.py ${SRL_PATH}/test.english.mtl.jsonlines   ${SRL_PATH}/test.english.conll12.json