import re
from typing import List, Dict, Any

from utils.noise_detection import clean_comment, if_comment_generated

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
# from function_parser.parsers.commentutils import get_docstring_summary


class RubyParser(LanguageParser):

    FILTER_PATHS = ('test', 'vendor')

    BLACKLISTED_FUNCTION_NAMES = {'initialize', 'to_text', 'display', 'dup', 'clone', 'equal?', '==', '<=>',
                                  '===', '<=', '<', '>', '>=', 'between?', 'eql?', 'hash'}

    @staticmethod
    def get_docstring(trait_node, blob: str, idx: int) -> str:
        raise NotImplementedError("Not used for Ruby.")
    
    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['comment'])
        return comment_node

    @staticmethod
    def _extract_method(node, blob, comment_buffer: List, module_name: str, module_or_class_name: str):
        definitions = []
        docstring = '\n'.join([match_from_span(comment, blob).strip().strip('#') for comment in comment_buffer])
        # docstring_summary = get_docstring_summary(docstring)
        
        metadata = RubyParser.get_function_metadata(node, blob)
        if docstring == '':
            return
        if metadata['identifier'] in RubyParser.BLACKLISTED_FUNCTION_NAMES:
            return
        if if_comment_generated(metadata['identifier'], docstring):  # Auto code generation
            return
        # print(docstring)
        # print('Function name', metadata['identifier'])
        # print(match_from_span(node, blob), '\n')
        
        _docs = docstring
        # docstring, param = 
        docstring = clean_comment(docstring, blob)
        comment_node = RubyParser.__get_comment_node(node)
        comment = [clean_comment(match_from_span(cmt, blob)) for cmt in comment_node]
        
        definitions.append({
            'type': 'class',
            'identifier': '{}.{}.{}'.format(module_name, module_or_class_name, metadata['identifier']),
            'parameters': metadata['parameters'],
            'function': match_from_span(node, blob),
            'function_tokens': tokenize_code(node, blob),
            'original_docstring': _docs,
            'docstring': docstring,
            'docstring_tokens': tokenize_docstring(docstring),
            'comment': comment,
            # 'docstring_summary': docstring_summary,
            'start_point': node.start_point,
            'end_point': node.end_point
        })
        return definitions

    @staticmethod
    def get_methods(nodes, blob: str, module_name: str, comment_buffer: List = None) -> List[Dict[str, Any]]:
        metadata = []
        comment_buffer = comment_buffer or []
        for module_or_class_node in nodes:
            module_or_class_name = match_from_span(module_or_class_node.children[1], blob)
            definitions = []
            for child in module_or_class_node.children:
                if child.type == 'comment':
                    comment_buffer.append(child)
                elif child.type == 'body_statement':
                    for sub_child in child.children:
                        if sub_child.type == 'comment':
                            comment_buffer.append(sub_child)
                        elif sub_child.type == 'method':
                            det = RubyParser._extract_method(sub_child, blob, comment_buffer, module_name, module_or_class_name)
                            comment_buffer = []
                            if det: definitions.append(det)
                        else:
                            comment_buffer = []
                            
                elif child.type == 'method':
                    # docstring = '\n'.join([match_from_span(comment, blob).strip().strip('#') for comment in comment_buffer])
                    # docstring_summary = get_docstring_summary(docstring)

                    # metadata = RubyParser.get_function_metadata(child, blob)
                    # if metadata['identifier'] in RubyParser.BLACKLISTED_FUNCTION_NAMES:
                    #     continue
                    # definitions.append({
                    #     'type': 'class',
                    #     'identifier': '{}.{}.{}'.format(module_name, module_or_class_name, metadata['identifier']),
                    #     'parameters': metadata['parameters'],
                    #     'function': match_from_span(child, blob),
                    #     'function_tokens': tokenize_code(child, blob),
                    #     'docstring': docstring,
                    #     # 'docstring_summary': docstring_summary,
                    #     'start_point': child.start_point,
                    #     'end_point': child.end_point
                    # })
                    det = RubyParser._extract_method(sub_child, blob, comment_buffer, module_name, module_or_class_name)
                    if det: definitions.append(det)
                    comment_buffer = []
                else:
                    comment_buffer = []
            metadata.extend(definitions)
        return metadata


    @staticmethod
    def get_definition(tree, blob: str) -> List[Dict[str, Any]]:
        definitions = []
        if 'ERROR' not in set([child.type for child in tree.root_node.children]):
            modules = [child for child in tree.root_node.children if child.type == 'module']
            
            for module in modules:
                if module.children:
                    module_name = ''
                    # comment_buffer = []
                    # module_name = match_from_span(module.children[1], blob)
                    for child in module.children:
                        if child.type == 'scope_resolution':
                            module_name = match_from_span(child, blob)
                        # elif child.type == 'comment':
                        #     comment_buffer.append(child)
                        elif child.type == 'body_statement':
                            sub_modules = [item for item in child.children if item.type == 'module' and child.children]
                            classes = [item for item in child.children if item.type == 'class']
                    
                    # for sub_module_node in sub_modules:
                    definitions.extend(RubyParser.get_methods(sub_modules, blob, module_name))
                    # for class_node in classes:
                    definitions.extend(RubyParser.get_methods(classes, blob, module_name))
        return definitions


    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        metadata['identifier'] = match_from_span(function_node.children[1], blob)
        params = []
        if function_node.children[2].type == 'method_parameters':
            parameter_list = match_from_span(function_node.children[2], blob).split(',')
            for param in parameter_list:
                item = re.sub(r'[^a-zA-Z0-9\_]', ' ', param).split()
                if len(item) > 0:
                    params.append(item[0].strip())
            # metadata['parameters'] = match_from_span(function_node.children[2], blob)
        metadata['parameters'] = params
        return metadata