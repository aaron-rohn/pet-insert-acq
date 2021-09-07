import numpy as np
from distutils.core import setup, Extension

petmr_ext = Extension('petmr', ['petmrmodule.cpp'], language = 'c++')
setup(name = 'petmr', 
      ext_modules = [petmr_ext],
      include_dirs = [np.get_include()])
