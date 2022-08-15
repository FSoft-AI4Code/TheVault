# Preprocessing code description

To getting started with preprocessing step, install dependencies:
```bash
pip install -r requirements.txt
```

This dataset was collected by `codeparrot` from open-source project on Github.
(More detail: [codeparrot/github-code](https://huggingface.co/datasets/codeparrot/github-code))

Extract dataset by languages into `.jsonl` file (store in `./data/raw`)
```bash
python crawl_data --n_samples 100 --languages Python C++ C#
```

Extract source code to function-description, class-description, code_line-description:
```bash
python parser_processing
```