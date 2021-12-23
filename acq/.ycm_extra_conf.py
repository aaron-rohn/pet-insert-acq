import os
import ycm_core

import numpy as np

flags = [
    '-Wall',
    '-Wextra',
    '-Werror',
    '-Wno-long-long',
    '-Wno-variadic-macros',
    '-Wno-unused-parameter',
    '-fexceptions',
    '-ferror-limit=10000',
    '-DNDEBUG',
    '-std=c++17',
    '-xc++',
    '-I/usr/include/python3.9',
    '-I' + os.path.dirname(__file__) + "/include",
    '-I' + np.get_include(),
    ]

SOURCE_EXTENSIONS = [ '.cpp', '.cxx', '.cc', '.c', ]

def FlagsForFile( filename, **kwargs ):
    return {'flags': flags, 'do_cache': True}
