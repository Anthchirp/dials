from __future__ import division
import shutil
import os.path
op = os.path
import sys
libtbx_path = os.path.join(
  os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "lib")
if (not libtbx_path in sys.path) :
  sys.path.append(libtbx_path)
from libtbx.auto_build import install_distribution
from libtbx.auto_build.installer_utils import *

class installer(install_distribution.installer):
  product_name = "DIALS"
  dest_dir_prefix = "dials"
  make_apps = []
  configure_modules = ["dials"]
  include_gui_packages = True
  base_package_options = ["--dials"]
  installer_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  modules = [
    # hot
    'annlib',
    'boost',
    'scons',
    'ccp4io',
    # base
    'cbflib',
    'cctbx_project',
    'gui_resources',
    'ccp4io_adaptbx',
    'annlib_adaptbx',
    'tntbx',
    'clipper',
    # dials
    'dials'
  ]

if (__name__ == "__main__") :
  installer(sys.argv[1:]).install()