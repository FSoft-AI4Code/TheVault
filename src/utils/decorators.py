
import logging
import time
logger = logging.getLogger()


def timing_decorator(func):
    """
    Measure the execution time of a function. This is useful for measuring the time it takes to execute an application and print a summary of the execution time to the log

    @param func - function to be benchmarked.

    @return result of the function wrapped in a decorator that logs the execution time of the function and returns the result
    """

    def wrapper(*args, **kwargs):
        """
         Wrapper to log how long the function took. This is useful for unit testing. If you don't want to log the time taken use : func : ` log ` instead.
         
         
         @return The return value of the function wrapped by this wrapper. It's a convenience wrapper for : func : ` log `
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        print(f'{func.__name__} took:  {time.time()-start_time} (s)')
        return result
    
    return wrapper