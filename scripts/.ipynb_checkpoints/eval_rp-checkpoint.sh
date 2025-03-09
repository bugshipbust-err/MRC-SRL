# evaluation using accuracy, used to select the best checkpoint
python /home/happyuser/Documents/ageion-dynamics/MRC-SRL/module/RolePrediction/predict.py \
--dataset_tag conll2012 \
--dataset_path /home/happyuser/Documents/ageion-dynamics/MRC-SRL/data/conll2012/dev.english.conll12.json \
--checkpoint_path ./checkpoints/conll2012/role_prediction/2025_02_25_23_10_37/checkpoint_7.cpt  \
--max_tokens 2048
# --amp

# detailed evaluation , used to determine the value of alpha (lambda in the paper)
# the values of alpha in CoNLL05, CoNLL09 and CoNLL12 are 5, 4.2 and 5.5 respectively.
# python ./module/RolePrediction/predict.py \
# --dataset_tag conll2005 \
# --dataset_path ./data/conll2005/dev.english.conll05.json \
# --checkpoint_path ./checkpoints/conll2005/role_prediction/2021_09_12_14_02_07/checkpoint_7.cpt \
# --max_tokens 2048 \
# --alpha 5 \
# --amp
