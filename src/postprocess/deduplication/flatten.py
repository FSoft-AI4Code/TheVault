from datasets import load_dataset
from codetext.parser import PythonParser
from codetext.parser.language_parser import tokenize_code
from codetext.utils import parse_code
import json
from tqdm import tqdm

humaneval = load_dataset("openai_humaneval")
dataset = humaneval['test']

writer = open('./humaneval.jsonl', 'a')
for data in tqdm(dataset):
    code = data['prompt'] + data['canonical_solution']
    node = parse_code(code, 'python').root_node
    fn = PythonParser.get_function_list(node)[0]
    docstring = PythonParser.get_docstring_node(fn)
    data['code_tokens'] = tokenize_code(fn, code, docstring)
    
    json.dump(data, writer)
    writer.write('\n')
    