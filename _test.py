# from src.codetext.utils.parser import PythonParser
# from src.codetext.utils import parse_code


# sample = '''
# """This is outside a function"""
# class Solutions():
#     """
#     Return a list of given sample
    
#     Args:
#         self: The docstring
#         sample: The docstring
#     """
#     pass
# '''

# tree = parse_code(sample, 'python')
# comments = PythonParser.get_comment_node(tree.root_node)
# docstring = PythonParser.get_docstring_node(tree.root_node)

# print(comments)
# print(docstring)

import multiprocessing
from itertools import repeat
from tqdm import tqdm


def f(shared_list, i):
    print('value=', i)
    shared_list.append(i)
    return 1
    # print(i)s

def abc():
    jobs = range(100)
    manager = multiprocessing.Manager()
    slist = manager.list([100, 101])
    
    pool = multiprocessing.Pool(processes=4)
    time_execute = 0
    for result in tqdm(pool.starmap(f, zip(repeat(slist), jobs)), total=len(jobs)):
        time_execute += result
    
    print(f'List: {slist}')
    print(f'List: {time_execute}')
    
    
if __name__ == '__main__':
    # abc()
    sample = '''
    def abc():
        """
        hey
        """
        
        if 1>0:
        
            pass
        \
        pass
        
    '''
    for line in sample.splitlines():
        if line.strip() == '':
            print(True, [line])
        else:
            print([line])