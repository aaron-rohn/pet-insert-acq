import glob
from distutils.core import setup, Extension

acq_ext = Extension('acq', glob.glob('src/*.cpp'), language = 'c++')
setup(name = 'acq', 
      ext_modules = [acq_ext],
      include_dirs = ['./include'])
