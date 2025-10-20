import asyncio
from inspect import isfunction
import inspect
import time
import os
from types import TracebackType
class TestError(Exception): ...
class _expectationsBase:
    def __init__(self, value, failString="Value was not as expected"):
        self._value = value
        self._failString = failString
    def fail(self):
        raise TestError(self._failString)
    def _assert(self, condition):
        pass
    def toBe(self, value):
        self._assert(self._value == value)
    def toEqual(self, value):
        self.toBe(value)
    def toHaveLength(self, n):
        self._assert(len(self._value) == n)
    def toBeFalse(self):
        self._assert(not self._value)
    def toBeFalsy(self):
        self.toBeFalse()
    def toBeTrue(self):
        self._assert(self._value)
    def toBeTruthy(self):
        self.toBeTrue()
    def toStartWith(self, value):
        self.toBeInstanceOf(str)
        self._assert(self._value.startswith(value))
    def toEndWith(self, value):
        self.toBeInstanceOf(str)
        self._assert(self._value.endswith(value))
    def toBeNone(self):
        self._assert(self._value is None)
    def toBeInstanceOf(self, T):
        self._assert(isinstance(self._value, T))
class _notExpect(_expectationsBase):
    def __init__(self, value, failString="Value was not as expected"):
        super().__init__(value, failString)
    def _assert(self, condition):
        if condition:
            self.fail()
class expect(_expectationsBase):
    def __init__(self, value, failString="Value was not as expected"):
        super().__init__(value, failString)
        self.not_ = _notExpect(value, failString)
    def _assert(self, condition):
        if not condition:
            self.fail()
def test(name: str):
    def decorate(fn):
        fn.__name__ = f'{fn.__name__}{name}'
        return fn
    return decorate
if __name__ == "__main__":
    directoryQueue = ['.']
    testFileQueue = []
    while len(directoryQueue) > 0:
        directory = directoryQueue.pop()
        dirList = os.scandir(directory)
        for entry in dirList:
            if entry.name.startswith('.'):
                continue
            if entry.is_dir():
                directoryQueue.insert(0, f'{directory}/{entry.name}')
            if entry.name.endswith(".test.py"):
                testFileQueue.insert(0, f'{directory}/{entry.name}')
            if entry.name.endswith("_test.py"):
                testFileQueue.insert(0, f'{directory}/{entry.name}')
            if entry.name.endswith(".spec.py"):
                testFileQueue.insert(0, f'{directory}/{entry.name}')
            if entry.name.endswith("_spec.py"):
                testFileQueue.insert(0, f'{directory}/{entry.name}')
    if len(testFileQueue) == 0:
        print("No Test Files to run")
        exit(1)
    passes = 0
    fails = 0
    class testDescriptor:
        def __init__(self, name, fn):
            self.name = name
            self.run = fn
    def describeStackFrame(trace: TracebackType, preMessage = "caused by"):
        stackframe = trace.tb_frame
        func = stackframe.f_code
        functionName = func.co_qualname
        functionArgs = []
        for var in func.co_varnames[0:func.co_argcount]:
            functionArgs.append(var)
        functionSignature = f'{functionName}({', '.join(functionArgs)})'
        retval = f'\x1b[31m{preMessage} {stackframe.f_code.co_filename}:{stackframe.f_lineno}\x1b[0m\n  {functionSignature}\n'
        return retval
    def printError(err: Exception):
        if err.__traceback__ is None:
            print(f'There was a problem from {inspect.stack()[1].filename}')
            return
        trace = err.__traceback__.tb_next
        if trace is None:
            print(f'  Exception {err.__class__.__name__}: "{err}" was raised without a stracktrace')
            return
        print(f'  {describeStackFrame(trace, f'Exception {err.__class__.__name__}: "{err}" was raised in"').replace("\n", "\n  ")}')
        trace = trace.tb_next
        while trace is not None:
            print(f'  {describeStackFrame(trace).replace("\n", "\n  ")}')
            trace = trace.tb_next
    callsCountedOfExpect = 0
    def _wrapped_expect(v, reason="Value was not as expected"):
        global callsCountedOfExpect
        callsCountedOfExpect += 1
        return expect(v, reason)
    def runner():
        global passes
        global fails
        start_tests = time.time_ns()
        for testFile in testFileQueue:
            testQueue: list[testDescriptor] = []
            definitions = {}
            code = ""
            print(f'\n{testFile}:')
            try:
                with open(testFile, "rb") as source_file:
                    code = compile(source_file.read(), testFile, "exec")
            except Exception as err:
                fails += 1
                print("\x1b[31mFile failed to load.\x1b[0m")
                printError(err)
                continue
            try:
                exec(code, definitions)
            except Exception as err:
                timeDeltaString = ""
                fails += 1
                printError(err)
                continue
            for var in definitions:
                potentialTest = definitions[var]
                if not isfunction(potentialTest):
                    continue
                if var == potentialTest.__name__:
                    continue
                if not potentialTest.__name__.startswith(var):
                    continue
                testName = potentialTest.__name__[len(var):]
                testQueue.append(testDescriptor(
                    testName,
                    potentialTest
                ))
            definitions["expect"] = _wrapped_expect
            failedTests = 0
            passedTests = 0
            for _test in testQueue:
                start = time.time_ns()
                try:
                    _test.run()
                    end = time.time_ns()
                    passedTests += 1
                    timeDeltaString = ""
                    if end-start > 1_000_000:
                        timeDeltaString = f' [{int((end-start) / 10_000) / 100}ms]'
                    print(f'\x1b[32m✓\x1b[0;1m {_test.name}\x1b[0m{timeDeltaString}')
                except Exception as err:
                    end = time.time_ns()
                    timeDeltaString = ""
                    if (end-start) > 1_000_000:
                        timeDeltaString = f' [{int((end - start) / 10_000) / 100}ms]'
                    failedTests += 1
                    print(f'\x1b[31m✘\x1b[0;1m {_test.name}\x1b[0m{timeDeltaString}')
                    printError(err)
                    continue
            fails += failedTests
            passes += passedTests
        end_tests = time.time_ns()
    print("")
    print(f' \x1b[32m{passes} pass\x1b[0m')
    print(f' \x1b[90m{fails} fail\x1b[0m')
    print(f' {callsCountedOfExpect} expect() calls')
    print(f'Ran {passes + fails} tests across {len(testFileQueue)} files. [\x1b[90;1m{int((end_tests - start_tests) / 1_000_0) / 100}ms\x1b[0m]')
    exit(1 if fails > 0 else 0)
    asyncio.run(runner())