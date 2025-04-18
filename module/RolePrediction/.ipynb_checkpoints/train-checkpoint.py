import time
import os
import random
import argparse
import pickle
import copy    ###

from transformers.optimization import get_linear_schedule_with_warmup
from torch.utils.tensorboard import SummaryWriter
from torch.cuda.amp import autocast, GradScaler
from tqdm import trange, tqdm
import numpy as np
import torch
from torch.nn.utils import clip_grad_norm_

from model import MyModel
from evaluate import *
from dataloader import *


def compare_state_dicts(prev_state_dict, current_state_dict):
    for key in prev_state_dict:
        if key not in current_state_dict:
            print(f"Key {key} not found in current state dict.")
            
        prev_tensor = prev_state_dict[key]
        current_tensor = current_state_dict[key]
        
        # Compare tensors for equality (within tolerance for floating point comparisons)
        if not torch.allclose(prev_tensor, current_tensor):
            print(f"Tensor mismatch for key: {key}")
        
    return True


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)


def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dataset_tag", choices=['conll2005', 'conll2009', 'conll2012'])
    #train_path and dev_path can also be cached data directories.
    parser.add_argument("--train_path")
    parser.add_argument("--dev_path")
    parser.add_argument("--pretrained_model_name_or_path")

    parser.add_argument("--max_tokens", type=int, default=2048)
    parser.add_argument("--max_epochs", default=5, type=int)
    parser.add_argument("--warmup_ratio", type=float, default=-1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--max_grad_norm", type=float, default=1)

    parser.add_argument("--amp", action="store_true",help="whether to enable mixed precision")
    parser.add_argument("--local_rank", type=int, default=-1) #DDP has been implemented but has not been tested.
    parser.add_argument("--eval", action="store_true",help="Whether to evaluate during training")
    parser.add_argument("--tensorboard", action='store_true',help="whether to use tensorboard to log training information")
    parser.add_argument("--save", action="store_true",help="whether to save the trained model")
    parser.add_argument("--tqdm_mininterval", default=1, type=float, help="tqdm minimum update interval")
    args = parser.parse_args()
    return args


def train(args, train_dataloader, dev_dataloader):
    model = MyModel(args)
    model.train()
    #prepare training
    if args.amp:
        scaler = GradScaler()
    device = args.local_rank if args.local_rank != -1 else (torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))
    if args.local_rank != -1:
        torch.cuda.set_device(args.local_rank)
    model.to(device)
    if args.local_rank != -1:
        model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[
                                                          args.local_rank], output_device=args.local_rank,   find_unused_parameters=True)
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {"params": [p for n, p in model.named_parameters() if (
            not any(nd in n for nd in no_decay))], "weight_decay":args.weight_decay},
        {"params": [p for n, p in model.named_parameters() if any(
            nd in n for nd in no_decay)], "weight_decay":0.0},
    ]
    optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=args.lr)
    if args.warmup_ratio > 0:
        num_training_steps = len(train_dataloader)*args.max_epochs
        warmup_steps = args.warmup_ratio*num_training_steps
        scheduler = get_linear_schedule_with_warmup(
            optimizer, warmup_steps, num_training_steps)
    if args.local_rank < 1:
        mid = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))
        if args.tensorboard:
            log_dir = "./logs/{}/role_prediction/{}".format(args.dataset_tag, mid)
            writer = SummaryWriter(log_dir)
    ltime = time.time()
    #start training  
    prev_state_dict = 0            ###
    print(evaluation(model, dev_dataloader, args.amp, device, args.dataset_tag))
    for epoch in range(args.max_epochs):
        if args.local_rank != -1:
            train_dataloader.sampler.set_epoch(epoch)
        tqdm_train_dataloader = tqdm(train_dataloader, desc="epoch:%d" % epoch, ncols=100, total=len(
            train_dataloader), mininterval=args.tqdm_mininterval)
        for i, batch in enumerate(tqdm_train_dataloader):
            torch.cuda.empty_cache()
            optimizer.zero_grad()
            input_ids, attention_mask, target = batch['input_ids'], batch['attention_mask'], batch['target']
            if int(input_ids.size()[-1]) > 512:
                print("zing zing...")
                continue
            input_ids, attention_mask, target = input_ids.to(
                device), attention_mask.to(device), target.to(device)
            # skip
            if args.amp:
                with autocast():
                    loss = model(input_ids, attention_mask, target)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                grad_norm = torch.norm(torch.stack(
                    [torch.norm(p.grad) for p in model.parameters() if p.grad is not None]))
                clip_grad_norm_(model.parameters(), args.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            # --------
            else:
                loss = model(input_ids, attention_mask, target)
                loss.backward()
                grad_norm = torch.norm(torch.stack(
                    [torch.norm(p.grad) for p in model.parameters() if p.grad is not None]))
                clip_grad_norm_(model.parameters(), args.max_grad_norm)
                optimizer.step()
            lr = optimizer.param_groups[0]['lr']
            if args.warmup_ratio > 0:
                scheduler.step()
            if args.local_rank < 1 and args.tensorboard:
                writer.add_scalar('loss', loss.item(), i +
                                  epoch*len(train_dataloader))
                writer.add_scalars(
                    "lr_grad", {"lr": lr, "grad_norm": grad_norm}, i+epoch*len(train_dataloader))
                writer.flush()
            if time.time()-ltime >= args.tqdm_mininterval:
                postfix_str = 'norm:{:.2f},lr:{:.1e},loss:{:.2e}'.format(
                    grad_norm, lr, loss.item())
                tqdm_train_dataloader.set_postfix_str(postfix_str)
        if args.local_rank < 1 and args.save:
            if hasattr(model, 'module'):
                model_state_dict = model.module.state_dict()
            else:
                model_state_dict = model.state_dict()
            optimizer_state_dict = optimizer.state_dict()

            # print(model.state_dict())
            
            # if prev_state_dict:         ###
                # print(compare_state_dicts(prev_state_dict, model_state_dict))
                
            # prev_state_dict = copy.deepcopy(model.state_dict())
            # checkpoint = {}           ###
            # checkpoint['model_state_dict'] = model_state_dict
            # checkpoint['optimizer_state_dict'] = optimizer_state_dict
            checkpoint = {"model_state_dict": model_state_dict,
                          "optimizer_state_dict": optimizer_state_dict}
            if args.warmup_ratio > 0:
                checkpoint['scheduler_state_dict'] = scheduler.state_dict()
            if args.amp:
                checkpoint["scaler_state_dict"] = scaler.state_dict()
            save_dir = './checkpoints/%s/role_prediction/%s/' % (args.dataset_tag, mid)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                pickle.dump(args, open(save_dir+'args', 'wb'))
            save_path = save_dir+"checkpoint_%d.cpt" % epoch
            torch.save(checkpoint, save_path)
            print("model saved at:", save_path)
        if args.eval and args.local_rank < 1:
            if args.local_rank != -1:
                for param in model.parameters():
                    torch.distributed.all_reduce(param.data, op=torch.distributed.ReduceOp.SUM)
                    param.data /= torch.distributed.get_world_size()

            score = evaluation(model, dev_dataloader, args.amp, device, args.dataset_tag)
            print(score)
            if args.tensorboard:
                hp = vars(args)
                hp['epoch']=epoch
                hp['mid']=mid
                writer.add_hparams(hp,score)
                writer.flush()
            model.train()     
    if args.local_rank < 1 and args.tensorboard:
        writer.close()


if __name__ == "__main__":
    args = args_parser()
    set_seed(args.seed)
    if args.local_rank != -1:
        torch.distributed.init_process_group(backend='nccl')
    if args.train_path.endswith('.json'):
        train_dataloader = load_data(args.train_path, args.pretrained_model_name_or_path,
                                     args.max_tokens, True, args.dataset_tag, args.local_rank)
        save_dir = args.train_path.replace(
            ".json", '')+'/role_prediction/'+args.pretrained_model_name_or_path.split('/')[-1]
        train_dataloader.dataset.save(save_dir)
        print('training data saved at:', save_dir)
    else:
        train_dataloader = reload_data(args.train_path, args.max_tokens, True, args.local_rank)
    if not args.eval:
        dev_dataloader = None
    elif args.dev_path.endswith('.json'):
        dev_dataloader = load_data(
            args.dev_path, args.pretrained_model_name_or_path, args.max_tokens, False, args.dataset_tag, -1)
        save_dir = args.dev_path.replace(
            ".json", '')+'/role_prediction/'+args.pretrained_model_name_or_path.split('/')[-1]
        dev_dataloader.dataset.save(save_dir)
        print('validation data saved at:', save_dir)
    else:
        dev_dataloader = reload_data(args.dev_path, args.max_tokens, False, -1)
    print(args)
    train(args, train_dataloader, dev_dataloader)
