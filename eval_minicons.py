from minicons import scorer
import torch
import logging
import argparse
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset

def get_scorer(model_name, cache_dir, tokenHF):
    model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=cache_dir, return_dict=True, token=tokenHF)
    model_tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir , use_fast=True, token=tokenHF)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_scorer = scorer.IncrementalLMScorer(model, tokenizer=model_tokenizer, device=device)
    return model_scorer

def get_surprisal(model_scorer, string_pair):
    return model_scorer.sequence_score(string_pair, reduction = lambda x: -x.sum(0).item())

def get_surprisal_last_word(model_scorer, string):
    words = string.split()
    last_word = words[-1]
    surprisals = model_scorer.token_score(string, surprisal=True)[0]
    last_surprisal_word = surprisals[-1][0]

    # Check if the last word is the same as the last surprisal word
    if last_word == last_surprisal_word:
        return surprisals[-1][1]
    # If not, concatenate previous elements until they match
    for i in range(2, len(words) + 1):
        last_surprisal_word = ''.join(word for word, _ in surprisals[-i:])
        #word, score = surprisals[-i]; print(f"    {word} {score}")
        if last_word == last_surprisal_word:
            return max([score for _, score in surprisals[-i:]])
    print(f"Last word not found in the surprisal list: {last_word}")
    return None
    
def obtain_score_calame(model_scorer, model_name, dataset):
    scores = []
    for examples in dataset:
        score = get_surprisal_last_word(model_scorer, examples)
        scores.append(score)

    scores_mean = round(np.mean([x for x in scores if x != None]),4)
    print(f"""Results for model: {model_name}
            Mean score last word: {scores_mean}
    {"#"*20}""")

def obtain_score_cola(model_scorer, model_name, dataset_good, dataset_bad):
    good_scores = []
    bad_scores = []
    for good in dataset_good:
        good_score = get_surprisal(model_scorer, good)
        good_scores.append(good_score)
    
    for bad in dataset_bad:
        bad_score = get_surprisal(model_scorer, bad)
        bad_scores.append(bad_score)

    good_mean = round(np.mean(good_scores),4)
    bad_mean = round(np.mean(bad_scores),4)
    difference_mean = round(bad_mean - good_mean,4)
    print(f"""Results for model: {model_name}
            Good mean: {good_mean}
            Bad mean: {bad_mean}
            Difference between means (bad-good): {difference_mean}
            {good_mean},{bad_mean},{difference_mean}
    {"#"*20}""")

def load_galcola(cache_dir):
    dataset = load_dataset("proxectonos/galcola", cache_dir = cache_dir)["test"]
    dataset_bad = [item['sentence'] for item in dataset if item['label'] == 0]
    dataset_good = [item['sentence'] for item in dataset if item['label'] == 1]
    return dataset_good, dataset_bad

def load_catcola(cache_dir):
    dataset = load_dataset("nbel/CatCoLA", cache_dir = cache_dir)["validation"]
    dataset_bad = [item['Sentence'] for item in dataset if item['Label'] == 0]
    dataset_good = [item['Sentence'] for item in dataset if item['Label'] == 1]
    return dataset_good, dataset_bad

def load_escola(cache_dir):
    dataset = load_dataset("nbel/EsCoLA", cache_dir = cache_dir)["validation"]
    dataset_bad = [item['Sentence'] for item in dataset if item['Label'] == 0]
    dataset_good = [item['Sentence'] for item in dataset if item['Label'] == 1]
    return dataset_good, dataset_bad

def load_cola_en(cache_dir):
    dataset = load_dataset("nyu-mll/glue", "cola", cache_dir = cache_dir)["validation"]
    dataset_bad = [item['sentence'] for item in dataset if item['label'] == 0]
    dataset_good = [item['sentence'] for item in dataset if item['label'] == 1]
    return dataset_good, dataset_bad

def load_cola_it(cache_dir):
    dataset = load_dataset("gsarti/itacola",  cache_dir = cache_dir)["test"]
    dataset_bad = [item['sentence'] for item in dataset if item['acceptability'] == 0]
    dataset_good = [item['sentence'] for item in dataset if item['acceptability'] == 1]
    return dataset_good, dataset_bad

def load_calame_pt(cache_dir):
    dataset = load_dataset("NOVA-vision-language/calame-pt", "all", cache_dir = cache_dir)["train"]
    dataset_concatenated = [item['sentence'] + ' ' + item['last_word'] for item in dataset]
    return dataset_concatenated

def avaliate_calame(lang, model_scorer, model_name, cache_dir):
    if lang == "pt":
        dataset = load_calame_pt(cache_dir)
    elif lang == "gl":
        print("Galician Calame not suported yet...")
        exit()
    else:
        print("Calame language not suported...")
        exit()
    obtain_score_calame(model_scorer, model_name, dataset)

def avaliate_cola(lang,model_scorer, model_name, cache_dir):   
    if lang == "gl":
        dataset_good, dataset_bad = load_galcola(cache_dir)
    elif lang == "en":
        dataset_good, dataset_bad = load_cola_en(cache_dir)
    elif lang == "cat":
        dataset_good, dataset_bad = load_catcola(cache_dir)
    elif lang == "es":
        dataset_good, dataset_bad = load_escola(cache_dir)
    elif lang == "it":
        dataset_good, dataset_bad = load_cola_it(cache_dir)
    else:
        print("CoLA language not suported...")
        exit()
    obtain_score_cola(model_scorer, model_name, dataset_good, dataset_bad)

def test():
    print("Test function")
    return

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Evaluation of Surprisal for linguistic datasets')
    parser.add_argument('--model', type=str, help='Model to use for obtaining text representations')
    parser.add_argument('--cache', type=str, help='Directory where cache data will be stored')
    parser.add_argument('--test', action='store_true', help='Test functionalities')
    parser.add_argument('--lang', type=str, help='Language of the dataset')
    parser.add_argument('--dataset', type=str, help='Dataset to evaluate (CoLA or Calame)')
    parser.add_argument('--token', type=str, help='Hugging Face authentication token')
    args = parser.parse_args()

    if args.test:
        test()
        exit()
    model_scorer = get_scorer(args.model, args.cache, args.token)
    if args.dataset == "calame":
        avaliate_calame(args.lang, model_scorer, args.model, args.cache)
    elif args.dataset == "cola":
        avaliate_cola(args.lang, model_scorer, args.model, args.cache)
    else:
        print("Dataset not suported...")
        exit()



    