import sys
import traceback
import logging


def handle_error(exception, logger=logging):
    ex_type, ex_value, ex_traceback = sys.exc_info()

    # Extract unformatter stack traces as tuples
    trace_back = traceback.extract_tb(ex_traceback)

    # Format stacktrace
    stack_trace = list()

    for trace in trace_back:
        stack_trace.append(
            "File : %s , Line : %d, Func.Name : %s, Message : %s"
            % (trace[0], trace[1], trace[2], trace[3])
        )

    logger.error("Exception type : %s " % ex_type.__name__)
    logger.error("Exception message : %s" % ex_value)
    logger.error("Stack trace : %s" % stack_trace)
