import re
from typing import List, Dict, Any

from docstring_parser import parse
from docstring_parser.common import *

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import clean_comment, if_comment_generated, strip_c_style_comment_delimiters
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
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node

    @staticmethod
    def extract_docstring(docstring:str, parameter_list:List) -> List:
        if docstring == '':
            return None, None
        
        param = {'other_param': {}}
        for each in parameter_list:
            param[each] = {'docstring': None}
            
        _docstring = parse(docstring, DocstringStyle.PHPDOC)
        
        for item in _docstring.meta:
            if len(item.args) > 0:
                tag = item.args[0]
                if tag in PARAM_KEYWORDS:
                    _param_name = item.arg_name
                    _param_type = item.type_name
                    _param_default = item.default
                    _param_docstring = item.description
                    _param_optional = item.is_optional
                
                    if _param_name in param.keys():
                        param[_param_name]['docstring'] = _param_docstring if _param_docstring != '' else None
                        
                        if _param_type != None:
                            param[_param_name]['type'] = _param_type
                    
                    else:
                        param['other_param'][_param_name] = {}
                        param['other_param'][_param_name]['docstring'] = _param_docstring if _param_docstring != '' else None
                        
                        if _param_type != None:
                            param['other_param'][_param_name]['type'] = _param_type
                
                elif tag in RETURNS_KEYWORDS | RAISES_KEYWORDS | YIELDS_KEYWORDS:  # other tag (@raise, @return, ...)
                    _param_docstring = item.description
                    
                    if _param_docstring != None and _param_docstring != "None":
                        _p = {'docstring': _param_docstring}
        
                        try:
                            _param_type = item.type_name                            
                            if _param_type != None:
                                _p = {'docstring': _param_docstring, 'type': _param_type}
                        except Exception:
                            pass
                            
                        if tag in param.keys():
                            if isinstance(param[tag], Dict):
                                param[tag] = [param[tag], _p]
                            
                            elif isinstance(param[tag], List):
                                param[tag].append(_p)
                        else:
                            param[tag] = _p
                            
        new_docstring = ''
        if _docstring.short_description != None:
            new_docstring += _docstring.short_description + '\n'
        if _docstring.long_description != None:
            new_docstring += _docstring.long_description
        
        return new_docstring, param
    
    @staticmethod
    def get_function_declarations(node, parent, blob, idx, node_type = None) -> Dict:
        docstring = PhpParser.get_docstring(parent, blob, idx)
        metadata = PhpParser.get_function_metadata(node, blob)
        for child in node.children:
            if child.type == 'compound_statement':
                
                if docstring == '':
                    return
                if metadata['identifier'] in PhpParser.BLACKLISTED_FUNCTION_NAMES:
                    return
                
                _docs = docstring
                comment_node = PhpParser.__get_comment_node(node)
                docstring, param = PhpParser.extract_docstring(docstring, metadata['parameters'])
                docstring = clean_comment(docstring, blob)
                _comment = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_node]
                comment = [clean_comment(cmt) for cmt in _comment]
                if if_comment_generated(metadata['identifier'], docstring):
                    return

                declarations = {
                    'type': node_type,
                    'identifier': '{}'.format(metadata['identifier']),
                    'parameters': metadata['parameters'],
                    'function': match_from_span(node, blob),
                    'function_tokens': tokenize_code(node, blob),
                    'original_docstring': _docs,
                    'docstring': docstring,
                    'docstring_tokens': tokenize_docstring(docstring),
                    'docstring_param': param,
                    'comment': comment,
                    'start_point': node.start_point,
                    'end_point': node.end_point
                }
        return declarations


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
                        # ret = PhpParser._get_declarations(child, _child, blob, declaration_name, node_type)
                        # if not ret:
                        #     continue
                        # # ret['type'] = node_type
                        # # ret['identifier'] = f'{}.{}'.format(declaration_name, metadata['identifier'])
                        # declarations.append(ret)
                        docstring = PhpParser.get_docstring(_child, blob, idx)
                        metadata = PhpParser.get_function_metadata(child, blob)
                        
                        if docstring == '':
                            continue
                        if metadata['identifier'] in PhpParser.BLACKLISTED_FUNCTION_NAMES:
                            continue
                        
                        _docs = docstring
                        comment_node = PhpParser.__get_comment_node(child)
                        docstring, param = PhpParser.extract_docstring(docstring, metadata['parameters'])
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
                            'docstring_param': param,
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
        function_nodes = {idx: child for idx, child in enumerate(tree.root_node.children) if child.type == 'function_definition'}
                
        for idx, function_node in function_nodes.items():
            ret = PhpParser.get_function_declarations(function_node, tree.root_node, blob, idx, node_type=function_node.type)
            if ret: definitions.extend(ret)
            
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
                        word = re.search(r"[\w\d_-]*$", word.strip()).group()
                        params.append(word)  # arg_name
        metadata['parameters'] = params
        return metadata