import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Optional

DOCSTRING_REGEX = re.compile(r"(['\"])\1\1(.*?)\1{3}", flags=re.DOTALL)
DOCSTRING_REGEX_TOKENIZER = re.compile(r"[^\s,'\"`.():\[\]=*;>{\}+-/\\]+|\\+|\.+|\(\)|{\}|\[\]|\(+|\)+|:+|\[+|\]+|{+|\}+|=+|\*+|;+|>+|\++|-+|/+")


def remove_words_in_string(words, string):
    new_string = string
    for word in words:
        new_string = str(new_string).replace(word, '')
    return new_string


def tokenize_docstring(docstring: str) -> List[str]:
    return [t for t in DOCSTRING_REGEX_TOKENIZER.findall(str(docstring)) if t is not None and len(t) > 0]


def tokenize_code(node, blob: str, nodes_to_exclude: Optional[Set]=None) -> List:
    tokens = []
    traverse(node, tokens)
    # print(tokens)
    # for token in tokens:
    #     print(token.text)
    return [match_from_span(token, blob) for token in tokens if nodes_to_exclude is None or token not in nodes_to_exclude]

def nodes_are_equal(n1, n2):
    return n1.type == n2.type and n1.start_point == n2.start_point and n1.end_point == n2.end_point

def parent_and_previous_sibling(tree, node):
    """Merge `node_parent` and `previous_sibling` function
    """
    parent = node_parent(tree, node)
    for i, node_at_i in enumerate(parent.children):
        if nodes_are_equal(node, node_at_i):
            if i > 0:
                return parent, parent.children[i-1]
            return parent, None

    return ValueError("Could not find node in tree.")


def previous_sibling(tree, node):
    """
    Search for the previous sibling of the node.
    TODO: C TreeSitter should support this natively, but not its Python bindings yet. Replace later.
    """
    to_visit = [tree.root_node]
    while len(to_visit) > 0:
        next_node = to_visit.pop()
        for i, node_at_i in enumerate(next_node.children):
            if nodes_are_equal(node, node_at_i):
                if i > 0:
                    return next_node.children[i-1]
                return None
        else:
            to_visit.extend(next_node.children)
    return ValueError("Could not find node in tree.")


# if parent_node.type == 'variable_declarator':
#     # node
#     base_node = node_parent(tree, parent_node)  # Get the variable declaration
#     # parent
#     parent_node = node_parent(tree, base_node)
# elif parent_node.type == 'pair':
#     base_node = parent_node  # This is a common pattern where a function is assigned as a value to a dictionary.
#     parent_node = node_parent(tree, base_node)
# else:
#     base_node = node

def traverse_type_parent(node, kind:List) -> None:
    results = []
    to_visit = [node]
    while len(to_visit) > 0:
        next_node = to_visit.pop()
        for child in next_node.children:
            if child.type in kind:
                results.append([next_node, child])
        else:
            to_visit.extend(next_node.children)
    
    return results


def node_parent(tree, node):
    to_visit = [tree.root_node]
    while len(to_visit) > 0:
        next_node = to_visit.pop()
        for child in next_node.children:
            if nodes_are_equal(child, node):
                return next_node
        else:
            to_visit.extend(next_node.children)
    raise ValueError("Could not find node in tree.")


def traverse(node, results: List) -> None:
    if node.type == 'string':
        results.append(node)
        return
    for n in node.children:
        traverse(n, results)
    if not node.children:
        results.append(node)


def traverse_type(node, results, kind:List) -> None:
    if node.type in kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)
        

def match_from_span(node, blob: str) -> str:
    lines = blob.split('\n')
    line_start = node.start_point[0]
    line_end = node.end_point[0]
    char_start = node.start_point[1]
    char_end = node.end_point[1]
    if line_start != line_end:
        return '\n'.join([lines[line_start][char_start:]] + lines[line_start+1:line_end] + [lines[line_end][:char_end]])
    else:
        return lines[line_start][char_start:char_end]


class LanguageParser(ABC):
    # @staticmethod
    # @abstractmethod
    # def get_definition(tree, blob: str) -> List[Dict[str, Any]]:
    #     pass

    @staticmethod
    @abstractmethod
    def get_class_metadata(class_node, blob):
        pass

    @staticmethod
    @abstractmethod
    def get_function_metadata(function_node, blob) -> Dict[str, str]:
        pass
    
    @staticmethod
    @abstractmethod
    def get_function_definitions(tree, blob) -> List:
        pass

    @staticmethod
    @abstractmethod
    def get_class_definitions(tree, blob) -> List:
        pass

    @staticmethod
    @abstractmethod
    def get_line_definitions(tree, blob) -> List:
        pass
    
    # @staticmethod
    # @abstractmethod
    # def get_context(tree, blob):
    #     raise NotImplementedError

    # @staticmethod
    # @abstractmethod
    # def get_calls(tree, blob):
    #     raise NotImplementedError