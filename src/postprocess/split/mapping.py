import os
import jsonlines
import csv
import glob
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor


def process_sample(sample, sets):
    for set_name, ids in sets.items():
        if sample["id"] in ids:
            return (set_name, sample)
    return None


def process_jsonl_file(filename, sets):
    with jsonlines.open(filename) as reader:
        samples = []
        name = os.path.basename(os.path.normpath(filename))
        for sample in tqdm(reader, desc=f"Processing {name}"):
            result = process_sample(sample, sets)
            if result:
                samples.append(result)
    return samples


def write_samples_to_jsonl(samples, language):
    for set_name, sample_list in samples.items():
        with jsonlines.open(f"{language}/{set_name}.jsonl", mode='w') as writer:
            for sample in sample_list:
                writer.write(sample)


def load_ids(language, csv_files):
    sets = {}
    for file in csv_files:
        # set_name = file.split('_')[1].split('.')[0]
        set_name = str(file).replace(".csv", "")
        name = os.path.basename(os.path.normpath(language))
        with open(f"{language}/{name}_{file}") as f:
            reader = csv.reader(f)
            ids = [row[0] for row in reader]
        sets[set_name] = ids
    return sets


def processing(language):
    csv_files = ["eval.csv", "large_train.csv", "medium_train.csv", "small_train.csv", "test.csv"]
    sets = load_ids(language, csv_files)
    name = os.path.basename(os.path.normpath(language))
    jsonl_file = f"{language}/{name}_merged.jsonl"
    samples = process_jsonl_file(jsonl_file, sets)

    # Group samples by set
    grouped_samples = {}
    for set_name, sample in samples:
        if set_name not in grouped_samples:
            grouped_samples[set_name] = []
        grouped_samples[set_name].append(sample)

    write_samples_to_jsonl(grouped_samples, language)
    # print(f"Finished processing {language} files.")


def main():
    data_path = "/datadrive/dungnm31/data/thestack"
    languages = glob.glob(os.path.join(data_path, '*'))
    csv_files = ["eval.csv", "large_train.csv", "medium_train.csv", "small_train.csv", "test.csv"]

    with ProcessPoolExecutor(max_workers=len(languages)) as executor:
        executor.submit(processing, languages)
        
        executor.map(processing, languages)


if __name__ == "__main__":
    main()
