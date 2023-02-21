import re
import sys
import warnings
from collections import Counter
from itertools import permutations
from typing import Any, Dict, List, Union

from langdetect import detect, detect_langs
from bs4 import BeautifulSoup
import Levenshtein as lev

from tree_sitter import Node
from codetext.parser.language_parser import tokenize_docstring, traverse_type
from codetext.clean import remove_comment_delimiters
warnings.filterwarnings("ignore", module='BeautifulSoup')


REGEX_TEXT = ("(?<=[a-z0-9])(?=[A-Z])|"
              "(?<=[A-Z0-9])(?=[A-Z][a-z])|"
              "(?<=[0-9])(?=[a-zA-Z])|"
              "(?<=[A-Za-z])(?=[0-9])|"
              "(?<=[@$.'\"])(?=[a-zA-Z0-9])|"
              "(?<=[a-zA-Z0-9])(?=[@$.'\"])|"
              "_|\\s+")

if sys.version_info >= (3, 7):
    import re
    SPLIT_REGEX = re.compile(REGEX_TEXT)
else:
    import regex
    SPLIT_REGEX = regex.compile("(?V1)"+REGEX_TEXT)


def split_sentences(docstring):
    # sentences = re.split("(?<![\.])\.(?![\.\w])", docstring)

    sentences = re.split("(?<=.)[\.\!\?](?=\s+)", docstring)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip() != ""]

    return sentences


def split_identifier_into_parts(identifier: str) -> List[str]:
    """
    Split a single identifier into parts on snake_case and camelCase
    """
    identifier_parts = list(s.lower() for s in SPLIT_REGEX.split(identifier) if len(s)>0)

    if len(identifier_parts) == 0:
        return [identifier]
    return identifier_parts


def check_node_error(node: Node) -> bool:
    """
    Check if node contains "ERROR" node
    Args:
        node (tree_sitter.Node): node
    
    Return:
        bool
    """
    if not isinstance(node, Node):
        raise ValueError("Expect type tree_sitter.Node, get %i", type(node))

    error_node = []        
    traverse_type(node, error_node, ['ERROR'])
    if len(error_node) > 0:
        return True
    else:
        return False


def get_node_length(node: Node) -> int:
    """
    Get node length
    Args:
        node (tree_sitter.Node): node
        
    Return:
        int
    """
    if not isinstance(node, Node):
        raise ValueError("Expect type tree_sitter.Node, get %i", type(node))

    line_start = node.start_point[0]
    line_end = node.end_point[0]
    return int(line_end - line_start)


def remove_special_tag(docstring: str) -> str:
    """
    Remove all special tag (html tag, e.g. <p>docstring</p>)
    """
    return BeautifulSoup(docstring, "html.parser").get_text()


def remove_special_character(docstring: str) -> str:
    return re.sub(r'[^a-zA-Z0-9\\\_\.\,]', ' ', docstring)


def remove_function_name_at_the_beginning(docstring):
    """
    This function is applied at docstring/paragraph-level.
    """
    ending_symbols = [":", "\s-"]
    for symbol in ending_symbols:
        pattern = "^[a-zA-Z0-9_\(\)]+" + symbol
        docstring = re.sub(pattern, "", docstring)

    docstring = docstring.strip()

    return docstring


def remove_link_in_brackets(docstring):
    """
    Removing patterns, for examples:
        - (https://www.a.ai)
        - <see https://www.b.ai>
        - <eg. a b c>

    This function is applied to each line of the docstring/paragraph.
    """
    pattern = "\%s(?:http|see|e\.g|eg.).*?\%s"
    bracket_pairs = [("(", ")"), ("<", ">")]
    for pair in bracket_pairs:
        docstring = re.sub(pattern % pair, "", docstring.strip())
    
    return docstring.strip()


# def remove_curly_brackets(docstring):
#     """
#     This function applies at docstring-level
#     For exampple:
#         {@link a.b} -> a.b
#     """
#     patterns = ["code", "link", "linkplain"]
#     for pattern in patterns:
#         # re.findall("(?<=\{\@link\s)[\w\.\#]+(?=\})")
#         matches = re.findall("\{\@%s\s[\w\.\#\-\_\'\"\(\)\/\\\~\|\s]+\}" % pattern, docstring)
#         for match in matches:
#             docstring = docstring.replace(match, match[len(pattern) + 2:-1])

#     docstring = docstring.strip()

#     return docstring


def remove_everything_after_a_pattern(docstring):
    """
    Only keep the part appears before the patterns.
    Ignore everything after the patterns.
                
    This function is applied at docstring-level
    """
    patterns = [
                "E.g", "e.g", "eg.", "Eg.", # "See", "Sees", ">>>", # "Example",
                # "<!doctype html>", 
                "Example usage:", "Created by", "Example:", # "Example output", "For example"
                # "TODO", "todo", "TO-DO", "to-do", "\\todo",

                # COMMENT THIS OUT WHEN PROCESSING THE PARAMETER DOCSTRINGS
                # "@param", "@return", 

                # javascript
                # "@constructor", "@extends", "@method", "@static", "@api", "@author", 
                # "@since", "@private", "@throws", "@example", "@export", "@see", "@author",
                # "@lisence", "@source", "@hidden", "@listens", "@deprecated", "@exception",

                # # ??
                # "@Route",

                # C
                "Note:", ". Note", "note::", "note:", ". note"
                ]

    for pattern in patterns:
        docstring = docstring.strip().split(pattern)[0]

    docstring = docstring.strip()
    return docstring


def remove_everything_after_an_url(docstring):
    """
    This function applies at sentence-level
    TO-DO: Should apply on docstring-level by regular expression
    """
    patterns = ["https:", "http:"]
    sentences = split_sentences(docstring)
    sentences_ = []
    for sentence in sentences:
        has_pattern = False
        for pattern in patterns:
            if pattern in sentence:
                has_pattern = True
                break
        if has_pattern:
            break
        sentences_.append(sentence)
    docstring = ". ".join(sentences_)

    docstring = docstring.strip()

    return docstring


def remove_lines_start_and_end_with_the_same_char(docstring):
    """
    Remove noisy lines.
    This function applies at line-level
    """
    lines = docstring.strip().split("\n")
    patterns = ["*", "-", "_", "=", "/", "+"]
    lines_ = []
    for line in lines:
        line = line.strip()
        if line == "":
            lines_.append(line)
            continue
        flag = False
        for pattern in patterns:
            p = "^\%s.*\%s$" % (pattern, pattern)
            if re.search(p, line) is not None:
                flag = True
                break
        if flag:
            continue

        lines_.append(line)
    docstring = "\n".join(lines_).strip()

    return docstring


def remove_lines_contain_only_a_single_char(docstring):
    """
    This function applies at line-level
    """
    patterns = ["*", "/", "=", "-", "+"]
    lines = docstring.strip().split("\n")
    for i, line in enumerate(lines):
        if line.strip() in patterns:
            lines[i] = ""
            continue
    
    docstring = "\n".join(lines).strip()

    return docstring


def remove_patterns_at_any_positions(docstring):
    """
    This function applies at docstring-level
    """
    patterns = ["/**", "/*", "<code>", "</code>", "*-*"]
    for pattern in patterns:
        if pattern in docstring:
            docstring = docstring.replace(pattern, "").strip()

    return docstring


def remove_patterns_at_the_start_and_end_of_a_line(docstring):
    """
    This function applies at line-level
    """ 
    patterns = ["* "]
    lines = docstring.strip().split("\n")
    for i, line in enumerate(lines):
        flag = True
        while flag:
            flag = False
            # at the beginning
            for pattern in patterns:
                if line.startswith(pattern):
                    line = line[len(pattern):]
            for symbol in [".", "*", "-", "_", "@", "#", "$", "!", "\\", "/", "+"]:
                pattern = r"^\%s{2,}" % (symbol) 
                line_ = re.sub(pattern, "", line)
                if line_ != line:
                    flag = True
                line = line_

            # at the end
            for symbol in [".", "*", "-", "_", "@", "#", "$", "!", "\\", "/", "+"]:
                pattern = r"\%s{2,}$" % (symbol) 
                line_ = re.sub(pattern, "", line)
                if line_ != line:
                    flag = True
                line = line_
        lines[i] = line

    docstring = "\n".join(lines).strip()

    return docstring


def remove_patterns_at_the_end_of_a_docstring(docstring):
    """
    Remove ending character(s)
    This function applies at docstring-level
    """
    patterns = [":", ";", ",", "...", "@@", "@"]
    if docstring != "":
        if docstring[-1] in patterns:
            docstring = docstring[:-1] + '.'

    docstring = docstring.strip()

    return docstring


def remove_specific_pattern(docstring: str) -> str:
    """
    pattern 1 will match "(e.g something)"
    pattern 2 will match "e.g something\n" or "e.g something. "
    pattern 3 will match "{@tag content}" and change to "content"
    pattern 4 will match trailing special chars "==============" or "************"
    """
    pattern1 = re.compile(r'(\(((i\.e)|(e\.g)|(\beg)|(\bie))[\s\S]+?)(\))', flags=re.IGNORECASE|re.MULTILINE)
    pattern3 = re.compile(r'{@.*?}')
    pattern4 = re.compile(r'(-|=|#|\*){5,}')

    docstring = re.sub(pattern1, '', docstring)
    # docstring = re.sub(pattern2, '', docstring)
    docstring = re.sub(pattern4, '', docstring)
    all_matches = re.findall(pattern3, docstring)
    for match in all_matches:
        new_match = str(match)[1:-1]  # remove { }
        new_match = re.sub(r'@\w*', '', new_match)
        docstring = docstring.replace(match, new_match)
    
    return docstring


def remove_unrelevant(docstring: str) -> str:
    flag = True
    while flag:
        flag = False
        docstring_ = docstring
        
        removing_functions = [
            remove_specific_pattern,
            remove_link_in_brackets,
            # remove_everything_after_an_url,  # Overlap
            # remove_everything_after_a_pattern,  # Noticeable wrong catch
            remove_patterns_at_any_positions,
            remove_lines_contain_only_a_single_char,
            remove_lines_start_and_end_with_the_same_char,
            remove_patterns_at_the_start_and_end_of_a_line,
            remove_function_name_at_the_beginning,
        ]
        for removing_function in removing_functions:
            docstring = removing_function(docstring)
            # print(removing_function.__name__)
            # print(docstring)
            # print('\n\n')

        if docstring != docstring_:
            flag = True
    
    docstring = remove_patterns_at_the_end_of_a_docstring(docstring)
    return docstring


# =================== Check code ======================

def check_black_node(node_name: str, exclude_list: List = None):
    """
    Check if node belongs to black list. E.g:
        - Built-in function
        - Test function, test class
        - Constructor
    """
    black_keywords = ['test_', 'Test_', '_test', 'toString', 'constructor', 'Constructor']
    black_keywords.extend(exclude_list)
    
    if not isinstance(node_name, str):
        raise ValueError(f'Expect str, get {type(node_name)}')
    if node_name.startswith('__') and node_name.endswith('__'):
        return True
    if node_name.startswith('set') or node_name.startswith('get'):
        return True
    if any(keyword in node_name for keyword in black_keywords):
        return True
    
    return False


def check_function_empty(node):
    #TODO: iterate all children of the code and check if != comment
    if get_node_length(node) <= 3:
        return True
    return False


def check_missing_function_metadata(metadata: Dict):
    assert 'identifier' in metadata.keys()
    identifier = metadata['identifier']
    if not identifier or identifier == '':
        return True
    return False


def check_autogenerated_by_code(raw_code: str, identifier: str):
    threshold = 0.4
    fn_name_splited = split_identifier_into_parts(identifier)
    fn_name_splited = ' '.join(fn_name_splited).lower()
    
    comment = str(re.sub(r'[^a-zA-Z0-9]', ' ', comment)).lower()

    d0 = lev.distance(fn_name_splited, comment)
    d1 = max(len(fn_name_splited), len(comment))
    
    if d0 <= d1*threshold:
        # print('Auto-code')
        return True
    
    return False

# =================== Check docstring ======================

def check_docstring_length(docstring: str):
    doc_tokens = docstring.strip().split()
    doc_line = docstring.splitlines()
    
    # Low cap
    if len(doc_tokens) < 3: # or len(doc_tokens) > 256:
    # if len(doc_tokens) >= 256:
        return True
    
    # High cap
    if len(doc_line) > 200:
        return True
    return False


def check_docstring_literal(docstring: str):
    """
    Check if docstring is EN
    TODO: "Ce n'est pas en anglais" -> Fr
    """
    p = re.compile('[a-zA-Z0-9]')
    if not docstring.isascii():
        return True
    if not p.search(docstring):
        return True
    # TODO: uncomment this
    # try:
    #     _docstring = re.sub(r'[^a-zA-Z0-9]', ' ', docstring)
    #     _docstring = ' '.join(split_all_sepcial_case(_docstring))
            
    #     print(_docstring)
    #     if detect(_docstring) != 'en':
    #         print(detect_langs(_docstring))
    #         return True
    # except:
    #     pass
    return False


def check_docstring_contain_question(docstring: str):
    pattern = re.compile(r'(?i)^(why\b|how\b|what\'?s?\b|where\b|is\b|are\b)')

    if docstring[-1] == '?' or pattern.search(docstring):
        return True
    else:
        return False


def check_docstring_underdevelopment(docstring: str):
    p1 = re.compile('(?i)^((Description of the Method)|(NOT YET DOCUMENTED)|(Missing[\s\S]+Description)|(not in use)|'
                    '(Insert the method\'s description here)|(No implementation provided)|(\(non\-Javadoc\)))')
    p2 = re.compile('(?i)^(todo|to-do|deprecate|copyright|fixme)', flags=re.IGNORECASE)
    # p3 = re.compile('^[A-Za-z]+(\([A-Za-z_]+\))?:')

    if p1.search(docstring) or p2.search(docstring):
        return True
    else:
        return False


def check_docstring_autogenerated(docstring: str):
    p1 = re.compile(r'(?i)@[a-zA-Z]*generated\b')
    p2 = re.compile('(?i)^([aA]uto[-\s]generated)')
    p3 = re.compile('(?i)^(This method initializes)')
    p4 = re.compile('(?i)^(This method was generated by)')

    if docstring is not None:
        if p1.search(docstring):
            return True

    if p2.search(docstring) or p3.search(docstring) or p4.search(docstring):
        return True
    
    else:
        return False
    

def check_docstring_contain_specific_pattern(docstring: str):
    condition1 = re.compile(r'((i\.e)|(e\.g)|(\beg)|(\bie))(\s|\.)', flags=re.IGNORECASE)
    condition2 = re.compile(r'(^(Sees*)|(example usage)|(example)|(note:*))', flags=re.IGNORECASE)
    condition_follow = re.compile(r'[^a-zA-Z0-9\s\.\,\:\;\'\"]')
    
    # if pattern 1 and 2 match -> check if the line contain any special characters
    if condition1.match(docstring) or condition2.match(docstring):
        if condition_follow.match(docstring):
            return True
        
    return False
    

# =================== Check characters ======================

def does_str_containt_math(str):
    math_indicators = ["equation", "\exp(", "\log(", "\sqrt(", "mathbf", "mathrm"]
    # TODO: page [number]
    containt_math = False
    for math_indicator in math_indicators:
        if math_indicator in str:
            containt_math = True
            break

    return containt_math


def check_contain_little_alphabet_char(docstring: str):
    thresholds = [5, 0.65, 15, 0.4]
    docstring = docstring.strip()
    contain_math = does_str_containt_math(docstring)
    docstring = "".join(docstring.strip().split())
    if len(docstring) < 1:
        return True
    num_alphabet_chars = len(re.findall("[a-zA-Z]", docstring))

    return len(docstring) > thresholds[0 + 2*int(contain_math)] and num_alphabet_chars / len(docstring) < thresholds[1 + 2*int(contain_math)]


def convert_special_pattern(docstring):
    patterns = [
                (["HH", "MM", "SS"], (":", "-")),
                (["MM", "DD", "YY"], (":", "-")),
                (["MM", "DD", "YYYY"], (":", "-")),

                (["hh", "mm", "ss"], (":", "-")),
                (["mm", "dd", "yy"], (":", "-")),
                (["mm", "dd", "yyyy"], (":", "-")),

                (["R", "G", "B"], (",", "-")),

                (["r", "g", "b"], (",", "-"))
                ]
    for pattern, signs in patterns:
        for sign in signs:
            pms = permutations(pattern)
            for pm in pms:
                string = sign.join(pm)
                if string in docstring:
                    docstring = docstring.replace(string, "".join(pm).lower())
    return docstring


def check_contain_many_special_char(docstring: str):
    threshold_dict = [[4, 6, 10, 6],  # max #bracket schar, max #normal schar, max #math schar
                      [10, 0.3, 17, 0,5],   # acceptable #total schar or acceptable ratio
                      [15, 20]] #, 0.3]  # max #schar
    docstring = docstring.strip()
    containt_math = does_str_containt_math(docstring)
    docstring = convert_special_pattern(docstring)
    num_tokens = len(tokenize_docstring(docstring))
    counter = Counter(docstring)

    count = 0
    math_symbols = ["+", "-", "*", "/", ":", "^", "=", "<", ">", "|", "(",]

    symbols = ["$", "!", "@", "#", "%", "^", "&", "*", "<", ">",
               "~", "|", "\\", "'", '"',"?", "-", "+", "=", "`",
               ":", "/", "(", "[", "{"]
    
    for symb in symbols:
        threshold = threshold_dict[0][0]
        if symb in ["(", "[", "{"]:
            threshold = threshold_dict[0][1]
            if containt_math:
                threshold = threshold_dict[0][3]
        else:
            if containt_math:
                if symb in math_symbols:
                    threshold = threshold_dict[0][2]
            
        if counter[symb] > threshold:
            return True
        
        # brackets
        if symb not in ["(", "[", "{"]:
            count += counter[symb]

    return count > max(threshold_dict[1][0 + 2*int(containt_math)], threshold_dict[1][1 + 2*int(containt_math)]*num_tokens) \
            and count > threshold_dict[2][int(containt_math)]


def check_contain_little_unique_chars(docstring):
    """
    This function applies on docstring line
    """
    threshold_dict = [5, 3] 
    docstring = "".join(docstring.strip().split()) 
    return len(docstring) > threshold_dict[0] and len(set(docstring)) <= threshold_dict[1]

# =================== Check words ======================

def check_contain_little_unique_words(docstring):
    threshold_dict = [3, 0.3]
    ignored_words = ["the", "of", "a", "an", "it", "for", "or", "in", "but",]
                     # ".", ",", "(", ")", "{", "}", "<", ">", "[", "]", "-", "|"]
    docs = ' '.join(re.findall(r'\b[a-zA-Z0-9]+\b', docstring))
    docstring_tokens = tokenize_docstring(docs)
    counter = Counter(docstring_tokens)
    try:
        most_repeated_word = counter.most_common()[0][0]
    except IndexError:
        return True
    max_count = counter.most_common()[0][1]

    index = 1
    while most_repeated_word in ignored_words:
        try:
            most_repeated_word = counter.most_common()[index][0]
            max_count = counter.most_common()[index][1]
            index += 1
        except IndexError:
            return False
    
    return max_count >= threshold_dict[0] and max_count / len(docstring_tokens) > threshold_dict[1]


# def check_contain_many_special_case(docstring: str):
#     """
#     Check if the string contains too much sneak_case or camelCase
#     """
#     threshold = 0.3
#     total_words = docstring.strip().split()
#     if len(total_words) == 0:
#         return True
#     sneak_cases = re.findall("\w+_\w+", docstring)
#     camelCases = re.findall("[A-Z]([A-Z0-9]*[a-z][a-z0-9]*[A-Z]|[a-z0-9]*[A-Z][A-Z0-9]*[a-z])[A-Za-z0-9]*", docstring)
#     return (len(sneak_cases) + len(camelCases))/len(total_words) > threshold


# def check_contain_many_repeated_word(docstring: str):
#     """
#     Check if the string (longer than 30 words) have too many repeated word
#     """
#     threshold_dict = [30, 0.5]  # max number, ratio
#     docstring = "".join(docstring.strip().split())
#     counter = Counter(docstring)
#     return len(docstring) > threshold_dict[0] and counter.most_common()[0][1] / len(docstring) > threshold_dict[1]


def check_contain_many_uppercase_word(docstring: str):
    threshold_dict = [10, 0.3]
    patterns = ["DD", "MM", "YY", "YYYY", "R,G,B", "R-G-B", "SS", "HH", "API"]
    for pattern in patterns:
        docstring = docstring.replace(pattern, pattern.lower())

    docstring = docstring.strip()
    snake_case_identifiers = re.findall("\w+_\w+", docstring)

    for identifier in snake_case_identifiers:
        docstring = docstring.replace(identifier, identifier.lower())

    uppercase_words = re.findall(r"(?<=\s)[A-Z][A-Z0-9_]+", docstring)
    docstring_tokens = docstring.strip().split()
    return len(docstring_tokens) > threshold_dict[0] and len(uppercase_words) / len(docstring_tokens) > threshold_dict[1]


def check_contain_too_many_variables(docstring):
    """
    Check if the string contains too much sneak_case or camelCase
    """
    threshold_dict = 0.3
    total_words = docstring.strip().split()
    if not total_words:
        return False
    
    # snake_case variable name
    snake_case_identifiers = re.findall("\w+_\w+", docstring)
    for identifier in snake_case_identifiers:
        docstring = docstring.replace(identifier, "").strip()
    # CamelCaes variable name
    camel_case_identifiers = re.finditer(r"[A-Z]([A-Z0-9]*[a-z][a-z0-9]*[A-Z]|[a-z0-9]*[A-Z][A-Z0-9]*[a-z])[A-Za-z0-9]*", docstring)
    camel_case_identifiers = [x.group() for x in camel_case_identifiers]
    # Method call
    variable_names = snake_case_identifiers + camel_case_identifiers

    return len(variable_names)/len(total_words) > threshold_dict


def check_contain_too_many_method_call(docstring):
    threshold_dict = 0.2
    total_words = docstring.strip().split()
    if not total_words:
        return False

    method_call_identifiers = re.finditer(r"[a-zA-Z0-9]+((\.|\()[a-zA-Z0-9]+)+", docstring)
    method_call_identifiers = [x.group() for x in method_call_identifiers]

    return len(method_call_identifiers)/len(total_words) > threshold_dict


def camel_case_split(identifier):
    matches = re.finditer(r'.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]


def snake_case_split(identifier):
    return identifier.strip().split("_")


def split_all_sepcial_case(docstring: str):
    docstring_tokens = []
    for token in tokenize_docstring(docstring.strip()):
        sub_tokens = snake_case_split(token)
        for sub_token in sub_tokens:
            sub_sub_tokens = camel_case_split(sub_token)
            docstring_tokens.extend(sub_sub_tokens)
    
    return docstring_tokens

def check_contain_many_long_word(docstring: str):
    threshold = 30
    docstring_tokens = split_all_sepcial_case(docstring)

    if len(docstring_tokens) == 0:
        return True

    return max([len(docstring_token) for docstring_token in docstring_tokens]) > threshold


def check_contain_url(docstring: str):
    pattern = re.compile(r'(?:(?:https?|ftp|file):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])', flags=re.I)
    
    if pattern.search(docstring):
        return True
    return False

# =================== End checking ======================

def check_function(node, node_metadata: Dict[str, Any], exclude_list: List = None, is_class=False):
    """
    Check function if
        - is built-in function (python)
        - is constructor
        - is empty 
        - is error node
        - have length < 3 lines
    
    Args:
        node (tree_sitter.Node): function node
        exclude_list (List): exclude name of function
    Return:
        bool: pass the check or not
    """
    node_identifier = node_metadata['identifier']
    
    # Check node/code
    if check_node_error(node):
        return False
    if check_black_node(node_identifier, exclude_list):
        return False
    if check_function_empty(node):
        return False
    if check_missing_function_metadata(node_metadata):
        return False
    
    # If pass all the check, return True == passed!
    return True


def check_docstring(docstring: str, loosen_filter: bool = False):
    """
    Check docstring is valid or not
    """
    check_funcs_mapping = [
        # 'check_docstring_literal',
        'check_docstring_contain_question',
        'check_docstring_underdevelopment',
        'check_docstring_autogenerated',
        'check_docstring_contain_specific_pattern',
        'check_contain_little_alphabet_char',
        'check_contain_many_special_char',
        'check_contain_little_unique_chars',
        'check_contain_little_unique_words',
        # 'check_contain_many_special_case',
        'check_contain_too_many_variables',
        'check_contain_too_many_method_call',
        # 'check_contain_many_repeated_word',
        'check_contain_many_uppercase_word',
        'check_contain_many_long_word',
        'check_contain_url',
    ]
    
    check_docstring_funcs = [
        # check_docstring_literal,
        check_docstring_contain_question,
        check_docstring_underdevelopment,
        check_docstring_autogenerated,
        check_docstring_contain_specific_pattern,
        check_contain_little_alphabet_char,
        check_contain_many_special_char,
        check_contain_little_unique_chars,
        check_contain_little_unique_words,
        # check_contain_many_special_case,
        check_contain_too_many_variables,
        check_contain_too_many_method_call,
        # check_contain_many_repeated_word,
        check_contain_many_uppercase_word,
        check_contain_many_long_word,
        check_contain_url,
    ]
    
    if loosen_filter:
        check_docstring_funcs = [
        check_docstring_contain_question,
        check_docstring_underdevelopment,
        check_docstring_autogenerated,
        check_docstring_contain_specific_pattern,
        check_contain_little_alphabet_char,
        # check_contain_many_special_char,
        check_contain_little_unique_chars,
        check_contain_little_unique_words,
        # check_contain_many_special_case,
        # check_contain_too_many_variables,
        # check_contain_too_many_method_call,
        # check_contain_many_repeated_word,
        check_contain_many_uppercase_word,
        check_contain_many_long_word,
        check_contain_url,
    ]
    
    # docstring_list = docstring.split('.')
    # print(f'\nAfter split {docstring_list}')
    
    applied_res = []
    result = False
    for i, check_condition in zip(check_funcs_mapping, check_docstring_funcs):
        # for comment in docstring_list:
        if docstring == '' or not docstring:
            return True #, []
        # if True then docstring have fail
        if check_condition(docstring):
            return True
            # return True
            # applied_res.append(f"<{i}> {docstring}")
    
    return result #, applied_res


def clean_docstring(docstring: str, loosen_filter: bool = False):
    """
    Clean docstring by removing special tag/url, characters, unrelevant information
    """
    cleaned_docstring = []
    if docstring == '' or docstring == None:
        return None
    _docstring = remove_comment_delimiters(docstring)
    if check_docstring_literal(_docstring):  # True is not pass
        return None #, [f"<check_docstring_literal> {docstring}"]

    # _docstring = '\n'.join(remove_comment_delimiters(docstring))
    docstring_paragraph_list = _docstring.strip().split('\n\n')
    
    for para in docstring_paragraph_list:
        docs = remove_unrelevant(para)
        docstring_list = re.split(r'(?<=.)[.!\?](?=\s+)', docs, flags=re.M)
        clean_line = []
        for line in docstring_list:
            try:
                line = remove_special_tag(line)
            except:
                print('Oops')
                return None
            
            # not_pass, res = check_docstring(line, loosen_filter)
            not_pass = check_docstring(line, loosen_filter)
            if not not_pass:
                clean_line.append(line)
            else:
                break
        
        if len(clean_line) < len(docstring_list):
            clean_line.append('')
        cleaned_docstring.append('.'.join(clean_line))
        

    cleaned_docstring = '\n\n'.join(cleaned_docstring)

    
    if check_docstring_length(cleaned_docstring):
        # if not res:
        #     return None #, [f"<check_docstring_length> {docstring}"]
        # else:
        return None #, res
    
    return cleaned_docstring #, res

if __name__ == '__main__':
    # test remove comment delimiters
    raw = [
        '// C, C++, C#',
        '/// C, C++, C#',   
        
        '/*******'
        '* Java'
        '/*******',
        '//** Java */',
        
        '# Python', 
        
        '//! Rust',
        '//!!! Rust',
        '/*!! Rust',
        '/*! Rust',
        
        '''
        /* The code below will print the words Hello World to the screen, and it is amazing 
        
        Somethin here too*/
        '''
    ]

    # for item in raw:
    #     print(remove_comment_delimiters(item))
        
    samples = [
        '\n\t\t/* 将JSONArray转换为Bean的List, 默认为ArrayList */',
        '// TODO: Why is he using Math.round?',
        '/* for now try mappig full type URI */',
        '// public String transformTypeID(URI typeuri){',
        '// return typeuri.toString();}',
        '/* Do we need to show the upgrade wizard prompt? */',
        '/* fixme: This function is not in use */',
        '// SampleEncryptionBox (senc) and SampleAuxiliaryInformation{Sizes|Offsets}Box',
        '/* This method initializes by me. The second line \n\n Abcdef*/',
        '/* @func_name_generated',
        '/* Auto-generated by IDE',
        '/ Auto-generated by IDE',
        '''
        /// Abc
        /// Abc
        /// Abc
        ''',
        '''
        /* Abc
         * def
         */
        '''
    ]
    
    # for item in samples:
    #     print(clean_docstring(item))
        
    samples = [
        '''
        Returns the Surface's pixel buffer if the Surface doesn't require locking.
        (e.g. it's a software surface)
        ''',
        '''
        Taking in a sequence string, return the canonical form of the sequence
        (e.g. the lexigraphically lowest of either the original sequence or its
        reverse complement)
        ''',
        '''
        Internal clear timeout. The function checks that the `id` was not removed
        (e.g. by `chart.destroy()`). For the details see
        [issue #7901](https://github.com/highcharts/highcharts/issues/7901).
        ''',
    ]
    
    # print('==== Cleaning ====')
    # for item in samples:
    #     print(clean_docstring(item))
        
    sample = '''
    Returns the message Id to use as heading text, depending on what types of
    usage are present (i.e. just writable files, or also readable directories,
    etc).
    |need_lifetime_text_at_end| is set to false iff the returned message Id
    already includes an explanation for how long a website will have access to
    the listed paths. It is set to true iff a separate label is needed at the end
    of the dialog to explain lifetime.
    '''
    print(sample)
    print('==== Cleaning ====')
    print(clean_docstring(sample)[0])
    
    # print(extract_docstring(sample, [], 'cpp'))
    
    # res = clean_docstring(sample)
    # print(res[0])
    # print(res[1])
    
    # sample = '''Convert java.util.regex.Matcher groups to JavaScript groups'''
    # print(check_contain_too_many_variables(sample))