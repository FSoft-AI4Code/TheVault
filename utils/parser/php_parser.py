import re
from typing import List, Dict, Any

from utils.noise_detection import clean_comment, if_comment_generated, strip_c_style_comment_delimiters
from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
# from function_parser.parsers.commentutils import strip_c_style_comment_delimiters, get_docstring_summary


class PhpParser(LanguageParser):

    FILTER_PATHS = ('test', 'tests')

    BLACKLISTED_FUNCTION_NAMES = {'__construct', '__destruct', '__call', '__callStatic',
                                  '__get', '__set', '__isset', '__unset',
                                  '__sleep', '__wakeup', '__toString', '__invoke',
                                  '__set_state', '__clone', '__debugInfo', '__serialize',
                                  '__unserialize'}

    @staticmethod
    def get_docstring(trait_node, blob: str, idx: int) -> str:
        docstring = ''
        if idx - 1 >= 0 and trait_node.children[idx-1].type == 'comment':
            docstring = match_from_span(trait_node.children[idx-1], blob)
            docstring = strip_c_style_comment_delimiters(docstring)
        return docstring
    
    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['line_comment'])
        return comment_node

    @staticmethod
    def get_declarations(declaration_node, blob: str, node_type: str) -> List[Dict[str, Any]]:
        declarations = []
        # for _child in (child for child in declaration_node.children if child.type == 'declaration_list'):
        for _child in declaration_node.children:
            if _child.type == 'name':
                declaration_name = match_from_span(_child, blob)
            elif _child.type == 'declaration_list':
                for idx, child in enumerate(_child.children):
                    # if child.type == 'name':
                    #     declaration_name = match_from_span(child, blob)
                    if child.type == 'method_declaration':
                        docstring = PhpParser.get_docstring(_child, blob, idx)
                        metadata = PhpParser.get_function_metadata(child, blob)
                        
                        if docstring == '':
                            continue
                        if metadata['identifier'] in PhpParser.BLACKLISTED_FUNCTION_NAMES:
                            continue
                        
                        _docs = docstring
                        comment_node = PhpParser.__get_comment_node(child)
                        # docstring, param = JavaParser.extract_docstring(docstring, metadata['parameters'])
                        docstring = clean_comment(docstring, blob)
                        _comment = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_node]
                        comment = [clean_comment(cmt) for cmt in _comment]
                        if if_comment_generated(metadata['identifier'], docstring):
                            continue

                        declarations.append({
                            'type': node_type,
                            'identifier': '{}.{}'.format(declaration_name, metadata['identifier']),
                            'parameters': metadata['parameters'],
                            'function': match_from_span(child, blob),
                            'function_tokens': tokenize_code(child, blob),
                            'original_docstring': _docs,
                            'docstring': docstring,
                            'docstring_tokens': tokenize_docstring(docstring),
                            # 'docstring_param': param,
                            'comment': comment,
                            # 'docstring_summary': docstring_summary,
                            'start_point': child.start_point,
                            'end_point': child.end_point
                        })
        return declarations


    @staticmethod
    def get_definition(tree, blob: str) -> List[Dict[str, Any]]:
        definitions = []
        trait_declarations = [child for child in tree.root_node.children if child.type == 'trait_declaration']
        class_declarations = [child for child in tree.root_node.children if child.type == 'class_declaration']
        # print(trait_declarations)
        # print(class_declarations)
        for trait_declaration in trait_declarations:
            definitions.extend(PhpParser.get_declarations(trait_declaration, blob, trait_declaration.type))
        for class_declaration in class_declarations:
            definitions.extend(PhpParser.get_declarations(class_declaration, blob, class_declaration.type))
        return definitions


    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        # metadata['identifier'] = match_from_span(function_node.children[1], blob)
        # metadata['parameters'] = match_from_span(function_node.children[2], blob)
        params = []
        for n in function_node.children:
            if n.type == 'name':
                metadata['identifier'] = match_from_span(n, blob)
            elif n.type == 'formal_parameters':
                parameter_list = match_from_span(n, blob).split(',')
                for param in parameter_list:
                    item = param.strip('(').strip(')').split()
                    for word in (word for word in item if re.search(r'\$', word)):
                        params.append(word.strip())  #arg
        metadata['parameters'] = params
        return metadata