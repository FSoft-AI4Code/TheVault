import json
import os
import argparse
from datasets import load_dataset, Dataset, concatenate_datasets
from transformers import default_data_collator, set_seed
from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification, DataCollatorWithPadding
from torch.utils.data import DataLoader
from tqdm import tqdm
import torch
import numpy as np
import jsonlines
import multiprocessing
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import pandas as pd


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', type=str, default=None)
    parser.add_argument('--model_name_or_path', type=str, default= 'Fsoft-AIC/Codebert-comment-inconsistence')
    parser.add_argument('--data_folder', type=str, default= './rule-based-cleaned/')
    parser.add_argument('--save_folder', type=str, default= './deep-learning-cleaned/')
    parser.add_argument('--sentence1_key', type=str, default='docstring')
    parser.add_argument('--sentence2_key', type=str, default='code')
    parser.add_argument('--batch_size', type=int, default= 256)
    parser.add_argument('--max_seq_length', type=int, default= 512)
    parser.add_argument('--device', type=str, default= 'cuda')
    args = parser.parse_args()
    return args


def load_model_tokenizer(args):
    config = AutoConfig.from_pretrained(
    args.model_name_or_path,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name_or_path,
    )
    try:
        model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name_or_path,
        config=config,
    )
    except:
        model = AutoModelForSequenceClassification.from_pretrained(
            args.model_name_or_path,
            config=config,
            from_flax=True
        )
    model.to(args.device)

    return model, tokenizer


def read_data_multiprocess(datafile):
    df = pd.read_json(datafile, lines=True)
    return df

def load_data(args, data_file, tokenizer):

    def preprocess_function(examples):
        # Tokenize the texts
        texts = (
            (examples[args.sentence1_key],) if args.sentence2_key is None else (examples[args.sentence1_key], examples[args.sentence2_key])
        )
        result = tokenizer(*texts, padding="max_length", max_length=args.max_seq_length, truncation=True)

        if "label" in examples:
            result["labels"] = np.array(examples["label"] == 0).astype(int)
        return result
    
    df = pd.read_json(data_file, lines=True)
    if len(df) == 0:
        return None, None
    dataset = Dataset.from_pandas(df[[args.sentence1_key, args.sentence2_key]])

    processed_dataset = dataset.map(preprocess_function, remove_columns = dataset.column_names, batched= True, num_proc= 20)
    dataloader = DataLoader(processed_dataset, collate_fn=DataCollatorWithPadding(tokenizer), batch_size=args.batch_size, shuffle= False)
    return df.to_dict('records'), dataloader

def prediction(args, model, dataloader):
    all_predictions = []

    model.eval()
    for batch in tqdm(dataloader, total= len(dataloader), desc="Prediction"):
        for k in batch:
            batch[k] = batch[k].to(args.device)

        with torch.no_grad():
            outputs = model(**batch)
        prediction = outputs.logits.argmax(dim=-1).tolist()
        all_predictions.extend(prediction)
    return all_predictions


def file_filtering(args, datafile, model, tokenizer, language):
    filename = datafile.split("/")[-1]
    if os.path.exists(os.path.join(args.save_folder, language, filename)):
        return 0


    dataset, dataloader = load_data(args, datafile, tokenizer)
    if dataset is None:
        return 0
    predictions = prediction(args, model, dataloader)

    assert len(dataset) == len(predictions)

    keep_cnt = 0
    keep_data = []
    for i, pred in enumerate(predictions):
        if pred != 0:
            keep_data.append(dataset[i])
            keep_cnt += 1
    
    with jsonlines.open(os.path.join(args.save_folder, language, filename), mode='w') as writer:
        writer.write_all(keep_data)

    return keep_cnt



if __name__ == "__main__":
    args = get_args()
    print(args)

    set_seed(0)

    model, tokenizer = load_model_tokenizer(args)

    keep_cnt = 0
    if args.language:
        if not os.path.exists(os.path.join(args.save_folder, args.language)):
            os.mkdir(os.path.join(args.save_folder, args.language))
        print(args.language)
        all_files = [os.path.join(args.data_folder, args.language, filename) for filename in os.listdir(os.path.join(args.data_folder, args.language)) if os.path.isfile(os.path.join(args.data_folder, args.language, filename))]
    else:
        for language in os.listdir(args.data_folder):
            all_files = []
            if not os.path.exists(os.path.join(args.save_folder, language)):
                os.mkdir(os.path.join(args.save_folder, language))

            for filename in os.listdir(os.path.join(args.data_folder, language)):
                if os.path.isfile(os.path.join(args.data_folder, language, filename)):
                    all_files.append(os.path.join(args.data_folder, language, filename))
    
        
    for file in all_files:
        language = file.split("/")[-2]
        print(language, file)
        keep_cnt += file_filtering(args, file, model, tokenizer, language)
    print(keep_cnt)