from datasets import load_dataset
from codetext.parser import GoParser, JavascriptParser, JavaParser, PythonParser, CppParser
from codetext.parser.language_parser import tokenize_code
from codetext.utils import parse_code
import json
from tqdm import tqdm


# HumanEvallanguage = "java"
humaneval = load_dataset("THUDM/humaneval-x", "js")
for set_name in ['test']: #, 'train']:
    writer = open(f'./javascript.jsonl', 'w')
    dataset = humaneval[set_name]
    _fail = 0

    for data in tqdm(dataset, total=len(dataset)):
        # try:
        # code = json.loads(data['solutions'])[0]
        code = data['declaration'] + data['canonical_solution']
        node = parse_code(code, 'java').root_node

        fn = JavascriptParser.get_function_list(node)
        print(fn)
        if len(fn) > 0:
            docstring = JavascriptParser.get_comment_node(fn[0])
            data['code_tokens'] = tokenize_code(fn[0], code, docstring)
        else:
            docstring = JavascriptParser.get_comment_node(node)
            data['code_tokens'] = tokenize_code(node, code, docstring)

        json.dump(data, writer)
        writer.write('\n')
            
        # except Enue
    
    print('Fail', _fail)
    
# data_path = ""
# for set_name in ['test', 'train']:
    