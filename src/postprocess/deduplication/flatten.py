from datasets import load_dataset
from codetext.parser import *
from codetext.parser.language_parser import tokenize_code
from codetext.utils import parse_code
import json
from tqdm import tqdm


# HumanEval
language = 'javascript'
fail = 0
humaneval = load_dataset("THUDM/humaneval-x", 'js')
humaneval_test = humaneval['test']

dataset = []

if language == 'python':
    parser = PythonParser
elif language == 'go':
    parser = GoParser
elif language == 'js' or language == 'javascript':
    parser = JavascriptParser
elif language == 'java':
    parser = JavaParser
elif language == 'cpp':
    parser = CppParser

for data in tqdm(humaneval_test, total=len(humaneval_test)):
    idx = data['task_id']
    code = data['declaration'] + data['canonical_solution'] # only for java
    # docstring = data['prompt']
    
    node = parse_code(code, language).root_node
    fn = parser.get_function_list(node)
    
    if len(fn) > 0:
        node = fn[0]
    docstring_node = parser.get_docstring_node(node)
    # docstring = '\n'.join([get_node_text(_node) for _node in docstring_node])
    if docstring_node:
        docstring = get_node_text(docstring_node[0])
    else:
        docstring = data['prompt']
    code_token = tokenize_code(node, code, docstring_node)
    
    dataset.append({
        'id': idx, 
        'docstring': docstring, 
        'code': get_node_text(node),
        'code_tokens': code_token
    })
    
with open(f'./eval/{language}.jsonl', 'w') as writer:
    for item in dataset:
        json.dump(item, writer)
        writer.write('\n')
    
# data_path = ""
# for set_name in ['test', 'train']:
    