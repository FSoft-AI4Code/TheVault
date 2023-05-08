from datasets import load_dataset
from codetext.parser import GoParser, JavascriptParser, JavaParser, PythonParser, CppParser
from codetext.parser.language_parser import tokenize_code
from codetext.utils import parse_code
import json
from tqdm import tqdm


# HumanEvallanguage = "java"
humaneval = load_dataset("codeparrot/apps")
for set_name in ['test', 'train']:
    writer = open(f'./apps_{set_name}.jsonl', 'w')
    dataset = humaneval[set_name]
    _fail = 0

    for data in tqdm(dataset, total=len(dataset)):
        try:
            code = json.loads(data['solutions'])[0]
            # code = data['declaration'] + data['canonical_solution']
            node = parse_code(code, 'python').root_node

            fn = PythonParser.get_function_list(node)
            if len(fn) > 0:
                docstring = PythonParser.get_comment_node(fn[0])
                data['code_tokens'] = tokenize_code(fn[0], code, docstring)
                continue
            else:
                docstring = PythonParser.get_comment_node(node)
                data['code_tokens'] = tokenize_code(node, code, docstring)

            json.dump(data, writer)
            writer.write('\n')
            
        except Exception:
            _fail += 1
            continue
    
    print('Fail', _fail)
    
# data_path = ""
# for set_name in ['test', 'train']:
    