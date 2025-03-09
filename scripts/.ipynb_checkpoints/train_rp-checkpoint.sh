python /home/happyuser/Documents/ageion-dynamics/MRC-SRL/module/RolePrediction/train.py \
--seed 69 \
--dataset_tag conll2012 \
--pretrained_model_name_or_path roberta-large \
--train_path /home/happyuser/Documents/ageion-dynamics/MRC-SRL/data/conll2012/test.english.conll12.json  \
--dev_path /home/happyuser/Documents/ageion-dynamics/MRC-SRL/data/conll2012/dev.english.conll12.json  \
--max_tokens 1024 \
--max_epochs 8 \
--lr 2e-5 \
--max_grad_norm 2 \
--warmup_ratio -1 \
--eval \
--save \
--tqdm_mininterval 1 \
# --amp \
