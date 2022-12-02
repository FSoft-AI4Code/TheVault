from collections import Counter
import re
import sys
from typing import Any, Dict, List, Union
import warnings
from itertools import permutations

from langdetect import detect, detect_langs
from bs4 import BeautifulSoup
import Levenshtein as lev

from src.utils.noise_detection import split_identifier_into_parts
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

from tree_sitter import Node
from src.utils.parser.language_parser import tokenize_docstring, traverse_type


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
    
    
def remove_comment_delimiters(docstring: str) -> str:
    """
    :param comment: raw (line or block) comment
    :return: list of comment lines
    """
    clean_p1 = re.compile('([\s\/*=-]+)$|^([\s\/*!=#-]+)')
    clean_p2 = re.compile('^([\s*]+)')

    def func(t):
        t = t.strip().replace('&nbsp;', ' ')
        return re.sub(clean_p2, '', t).strip()

    comment_list = []
    return re.sub(clean_p1, '', docstring)
    # for line in re.sub(clean_p1, '', docstring).split('\n'):
    #     cur_line = func(line)
    #     if cur_line != '':
    #         comment_list.append(cur_line)

    # # print(comment_list)
    # return comment_list


def remove_special_tag(docstring: str) -> str:
    """
    Remove all special tag (html tag, e.g. <p>docstring</p>)
    """
    return BeautifulSoup(docstring, "html.parser").get_text()


def remove_special_character(docstring: str) -> str:
    return re.sub(r'[^a-zA-Z0-9\\\_\.\,]', ' ', docstring)


def remove_url(docstring: str, replace: str='') -> str:
    """
    Replace URL (e.g. https://google.com) by `replace` word
    """
    return re.sub(r'http\S+', replace, docstring, flags=re.MULTILINE)


def remove_unrelevant(docstring: str) -> str:
    """
    pattern 1 will match "(e.g something)"
    pattern 2 will match "e.g something\n" or "e.g something. "
    pattern 3 will match "{@tag content}" and change to "content"
    pattern 4 will match trailing special chars "==============" or "************"
    """
    pattern1 = re.compile(r'(\(((i\.e)|(e\.g)|(\beg)|(\bie))[\s\S]+?)(\))')
    pattern2 = re.compile(r'((i\.e)|(e\.g)|(\beg)|(\bie))\..*?(\.\s|\n)')
    pattern3 = re.compile(r'{@.*}')
    pattern4 = re.compile(r'(-|=|#|\*){5,}')
    
    docstring = re.sub(pattern1, '', docstring)
    docstring = re.sub(pattern2, '', docstring)
    docstring = re.sub(pattern4, '', docstring)
    all_matches = re.findall(pattern3, docstring)
    for match in all_matches:
        new_match = str(match)[1:-1]  # remove { }
        new_match = re.sub(r'@\w*', '', new_match)
        docstring = docstring.replace(match, new_match)
    
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
    # for child in node.children:
    #     if child.type == 'block':
    #         for item in child.children:
    #             if item.type == 'comment' or (item.type == 'expression_statement' and item.children[0].type == 'string'):
    #                 continue
    #             elif item.type != 'pass_statement' and item.type != 'raise_statement':
    #                 return False
    if get_node_length(node) <= 3:
        return False
    return True


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
    if len(doc_tokens) < 3 or len(doc_tokens) > 256:
    # if len(doc_tokens) >= 256:
        return True
    return False


def check_docstring_literal(docstring: str):
    p = re.compile('[a-zA-Z0-9]')
    if not docstring.isascii():
        return True
    if not p.search(docstring):
        return True
    # TODO: uncomment this
    # try:
    #     if detect(docstring) != 'en':
    #         return True
    # except:
        pass
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
    p2 = re.compile('(?i)^(todo|deprecate|copyright|fixme)')
    p3 = re.compile('^[A-Za-z]+(\([A-Za-z_]+\))?:')
    p4 = re.compile('[A-Z ]+')
    p5 = re.compile('\(.+\)|\[.+\]|\{.+\}')

    if p1.search(docstring) or p2.search(docstring) or p3.search(docstring):
        return True
    elif re.fullmatch(p4, docstring) or re.fullmatch(p5, docstring):
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

# =================== Check characters ======================

def check_contain_little_single_char(docstring: str):
    thresholds = [5, 0.7]
    docstring = "".join(docstring.strip().split())
    if len(docstring) < 1:
        return True
    num_alphabet_chars = len(re.findall("[a-zA-Z]", docstring))

    return len(docstring) > thresholds[0] and num_alphabet_chars / len(docstring) < thresholds[1]

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
    threshold_dict = [0.1, 0.3, 10] #, 0.3]  # percentage of single char,  percentage of all char, min token length
    docstring = convert_special_pattern(docstring)

    num_tokens = len(tokenize_docstring(docstring))
    counter = Counter(docstring)

    count = 0
    signs = [
             ";", "\\", "/", "\?", # ":",
             "+", "=", # "-"
             "\#", "*", "<", ">", "~", "%", "@", "|",
             ]
    if num_tokens == 0:
        return True
    for sign in signs:
        if counter[sign] > threshold_dict[0]*num_tokens:
            return True
        count += counter[sign]

    # return count > threshold_dict[1] and count / num_tokens > threshold_dict[2]
    return num_tokens > threshold_dict[2] and count / num_tokens > threshold_dict[1]


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

    uppercase_words = re.findall("[A-Z0-9_]+", docstring)
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
    camel_case_identifiers = re.findall("[A-Z]([A-Z0-9]*[a-z][a-z0-9]*[A-Z]|[a-z0-9]*[A-Z][A-Z0-9]*[a-z])[A-Za-z0-9]*", docstring)
    variable_names = snake_case_identifiers + camel_case_identifiers

    return len(variable_names)/len(total_words) > threshold_dict


def camel_case_split(identifier):
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]


def snake_case_split(identifier):
    return identifier.strip().split("_")


def check_contain_many_long_word(docstring: str):
    threshold = 30
    docstring_tokens = []
    for token in tokenize_docstring(docstring.strip()):
        sub_tokens = snake_case_split(token)
        for sub_token in sub_tokens:
            sub_sub_tokens = camel_case_split(sub_token)
            docstring_tokens.extend(sub_sub_tokens)

    if len(docstring_tokens) == 0:
        return True

    return max([len(docstring_token) for docstring_token in docstring_tokens]) > threshold


def check_contain_url(docstring: str):
    pattern = re.compile(
        r'(?:(?:https?|ftp|file):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])',
        flags=re.I|re.M
    )
    
    if re.match(pattern, docstring, flags=re.MULTILINE):
        return True
    return False


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
    
    return True


def check_docstring(docstring: str):
    """
    Check docstring is valid or not
    """
    check_funcs_mapping = [
        # 'check_docstring_literal',
        'check_docstring_contain_question',
        'check_docstring_underdevelopment',
        'check_docstring_autogenerated',
        'check_contain_little_single_char',
        'check_contain_many_special_char',
        'check_contain_little_unique_chars',
        'check_contain_little_unique_words',
        # 'check_contain_many_special_case',
        'check_contain_too_many_variables',
        # 'check_contain_many_repeated_word',
        'check_contain_many_uppercase_word',
        'check_contain_many_long_word',
    ]
    
    check_docstring_funcs = [
        # check_docstring_literal,
        check_docstring_contain_question,
        check_docstring_underdevelopment,
        check_docstring_autogenerated,
        check_contain_little_single_char,
        check_contain_many_special_char,
        check_contain_little_unique_chars,
        check_contain_little_unique_words,
        # check_contain_many_special_case,
        check_contain_too_many_variables,
        # check_contain_many_repeated_word,
        check_contain_many_uppercase_word,
        check_contain_many_long_word,
    ]
    
    # docstring_list = docstring.split('.')
    # print(f'\nAfter split {docstring_list}')
    
    applied_res = []
    result = False
    for i, check_condition in zip(check_funcs_mapping, check_docstring_funcs):
        # for comment in docstring_list:
        if docstring == '' or not docstring:
            return True, []
        # if True then docstring have fail
        if check_condition(docstring):
            result = True
            # return True
            applied_res.append(f"<{i}> {docstring}")
    
    return result, applied_res


def clean_docstring(docstring: str):
    """
    Clean docstring by removing special tag/url, characters, unrelevant information
    """
    cleaned_docstring = []
    _docstring = remove_comment_delimiters(docstring)
    if check_docstring_literal(_docstring):  # True is not pass
        return None, [f"<check_docstring_literal> {docstring}"]

    # _docstring = '\n'.join(remove_comment_delimiters(docstring))
    docstring_paragraph_list = _docstring.strip().split('\n\n')
    
    for para in docstring_paragraph_list:
        docs = remove_unrelevant(para)
        docstring_list = re.split(r'(?<=.)[.!\?](?=\s+)', docs, flags=re.M)
        # docstring_list = re.findall(r'.*?[.!\?]\s+', docs, flags=re.DOTALL)  # split . with endline
        # if not docstring_list:
        #     docstring_list = [docs]
        
        clean_line = []
        for line in docstring_list:
            # print([line])
            line = remove_special_tag(line)
            is_pass, res = check_docstring(line)
            if not is_pass:
                line = remove_url(line)
                clean_line.append(line)
            else:
                break
        
        cleaned_docstring.append('. '.join(clean_line))
        
    cleaned_docstring = '\n\n'.join(cleaned_docstring)
    
    # valid condition
    if check_docstring_length(cleaned_docstring):
        if not res:
            return None, [f"<check_docstring_length> {docstring}"]
        else:
            return None, res
    
    return cleaned_docstring, res


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
    ]
    
    # for item in samples:
    #     clean_docstring(item)
        
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
        
    sample = """
    Return a decorator that enforces API request limit guidelines.

    We are allowed to make a API request every api_request_delay seconds as
    specified in praw.ini. This value may differ from reddit to reddit. For
    reddit.com it is 2. Any function decorated with this will be forced to
    delay _rate_delay seconds from the calling of the last function
    decorated with this before executing.

    This decorator must be applied to a RateLimitHandler class method or
    instance method as it assumes `rl_lock` and `last_call` are available.
    """
    print(clean_docstring(sample))
    # print(sample)
    # res = clean_docstring(sample)
    # print('==== Cleaning ====')
    # print(res[0])
    # print(res[1])
    
    sample = '0xfff0\n 0x0001_ffff\n 0xffff_ffff_fff8_4400'
    print(check_contain_many_uppercase_word(sample))
    
    sample = 'Plays a audio file on Nao, it runs the file from the /home/nao/ directory'
    
    print(check_docstring_length(sample))