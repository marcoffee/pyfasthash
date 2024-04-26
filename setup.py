#!/usr/bin/env python
import sys
import os
import platform
from glob import glob

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

IS_64BITS = sys.maxsize > 2**32

machine = platform.machine().lower()
IS_X86 = machine in ['i386', 'i686', 'x86_64', 'amd64']
IS_X86_64 = IS_X86 and IS_64BITS
IS_ARM = machine.startswith('arm') or machine.startswith('aarch')
IS_ARM64 = IS_ARM and IS_64BITS
IS_PPC = machine.startswith('ppc')
IS_PPC64 = IS_PPC and IS_64BITS

IS_WINNT = os.name == "nt"
IS_POSIX = os.name == "posix"
IS_MACOS = sys.platform == "darwin"

SUPPORT_INT128 = not IS_WINNT

ON = 1
OFF = 0


def cpu_features():
    from collections import namedtuple

    CpuFeatures = namedtuple(
        "CpuFeatures", ['sse41', 'sse42', 'aes', 'avx', 'avx2'])

    sse41 = sse42 = aes = avx = avx2 = False

    if IS_X86:
        try:
            from cpuid import _is_set

            sse41 = _is_set(1, 2, 19) == 'Yes'
            sse42 = _is_set(1, 2, 20) == 'Yes'
            aes = _is_set(1, 2, 25) == 'Yes'
            avx = _is_set(1, 2, 28) == 'Yes'
            avx2 = _is_set(7, 1, 5) == 'Yes'
        except ImportError:
            if IS_64BITS:
                sse41 = sse42 = aes = avx = avx2 = True

    return CpuFeatures(sse41, sse42, aes, avx, avx2)


cpu = cpu_features()


macros = []
include_dirs = [
    "src/thirdparty/pybind11/include",
    "src/thirdparty/highwayhash",
]
library_dirs = []
libraries = []
extra_macros = []
extra_compile_args = []
extra_link_args = []
default_cflags = []

if IS_WINNT:
    macros += [
        ("WIN32", None),
    ]

    python_home = os.environ.get('PYTHON_HOME')

    if python_home:
        include_dirs += [
            os.path.join(python_home, 'include'),
        ]
        library_dirs += [
            os.path.join(python_home, 'libs'),
        ]

    extra_macros += [("WIN32", 1)]
    extra_compile_args += ["/O2", "/GL", "/MT", "/EHsc", "/Gy", "/Zi"]
    extra_link_args += ["/DLL", "/OPT:REF", "/OPT:ICF",
                        "/MACHINE:X64" if IS_64BITS else "/MACHINE:X86"]
elif IS_POSIX:
    if IS_MACOS:
        include_dirs += [
            '/opt/local/include',
            '/usr/local/include'
        ]

        extra_compile_args += [
            "-Wdeprecated-register",
            "-stdlib=libc++",
        ]
    else:
        libraries += ["rt", "gcc"]

    if IS_ARM:
        default_cflags += ["-march=armv8.2-a+simd+crypto+dotprod+ssbs+rcpc"]

    elif IS_X86:
        default_cflags += ["-march=x86-64-v3"]

    else:
        default_cflags += ["-march=native"]

    extra_compile_args += default_cflags

if SUPPORT_INT128:
    macros += [
        ('SUPPORT_INT128', ON),
    ]

c_libraries = [(
    'fnv', {
        "sources": [
            'src/thirdparty/fnv/hash_32.c',
            'src/thirdparty/fnv/hash_32a.c',
            'src/thirdparty/fnv/hash_64.c',
            'src/thirdparty/fnv/hash_64a.c'
        ],
        "macros": extra_macros,
    }
), (
    'smhasher', {
        "sources": list(filter(None, [
            'src/thirdparty/smhasher/MurmurHash1.cpp',
            'src/thirdparty/smhasher/MurmurHash2.cpp',
            'src/thirdparty/smhasher/MurmurHash3.cpp',
            'src/thirdparty/smhasher/City.cpp',
            'src/thirdparty/smhasher/Spooky.cpp',
            'src/thirdparty/smhasher/SpookyV2.cpp',
            'src/thirdparty/smhasher/metrohash/metrohash64.cpp',
            'src/thirdparty/smhasher/metrohash/metrohash64crc.cpp' if IS_X86 or IS_ARM64 else None,
            'src/thirdparty/smhasher/metrohash/metrohash128.cpp',
            'src/thirdparty/smhasher/metrohash/metrohash128crc.cpp' if IS_X86 or IS_ARM64 else None,
        ])),
        "cflags": extra_compile_args + [
            "-std=c++11",
        ],
    }
), (
    'farm', {
        "sources": ['src/thirdparty/smhasher/farmhash-c.c'],
        "macros": extra_macros,
        "cflags": default_cflags,
    }
), (
    'lookup3', {
        "sources": ['src/thirdparty/lookup3/lookup3.c'],
        "macros": extra_macros,
        "cflags": default_cflags,
    }
), (
    'SuperFastHash', {
        "sources": ['src/thirdparty/SuperFastHash/SuperFastHash.c'],
        "macros": extra_macros,
        "cflags": default_cflags,
    }
), (
    "xxhash", {
        "sources": ["src/thirdparty/xxHash/xxhash.c"],
        "cflags": default_cflags,
    }
)]

if not IS_WINNT:
    srcs = [
        "src/thirdparty/highwayhash/highwayhash/arch_specific.cc",
        "src/thirdparty/highwayhash/highwayhash/instruction_sets.cc",
        "src/thirdparty/highwayhash/highwayhash/os_specific.cc",
        "src/thirdparty/highwayhash/highwayhash/hh_portable.cc",
    ]
    cflags = extra_compile_args + [
        "-Isrc/thirdparty/highwayhash",
        "-std=c++11",
    ]

    if IS_X86_64:
        srcs += [
            "src/thirdparty/highwayhash/highwayhash/hh_sse41.cc",
            "src/thirdparty/highwayhash/highwayhash/hh_avx2.cc",
        ]

    elif IS_ARM64:
        srcs += ["src/thirdparty/highwayhash/highwayhash/hh_neon.cc"]

    elif IS_PPC64:
        srcs += ["src/thirdparty/highwayhash/highwayhash/hh_vsx.cc"]
        cflags += ['-mvsx']

    c_libraries += [(
        "highwayhash", {
            "sources": srcs,
            "cflags": cflags,
        }
    )]

libraries += [libname for (libname, _) in c_libraries]
cmdclass = {}

try:
    from pybind11.setup_helpers import Pybind11Extension as Extension, build_ext

    cmdclass["build_ext"] = build_ext

except ImportError:
    from setuptools import Extension

pyhash = Extension(name="_pyhash",
                   sources=['src/Hash.cpp'],
                   depends=glob('src/*.h'),
                   define_macros=macros,
                   include_dirs=include_dirs,
                   library_dirs=library_dirs,
                   libraries=libraries,
                   extra_compile_args=extra_compile_args +
                   ["-std=c++11"],
                   extra_link_args=extra_link_args,
                   )

setup(name='pyhash',
      version='0.9.4',
      description='Python Non-cryptographic Hash Library',
      long_description=open(os.path.join(here, 'README.md')).read(),
      long_description_content_type='text/markdown',
      url='https://github.com/flier/pyfasthash',
      download_url='https://github.com/flier/pyfasthash/releases',
      platforms=["x86", "x64"],
      author='Flier Lu',
      author_email='flier.lu@gmail.com',
      license="Apache Software License",
      packages=['pyhash'],
      libraries=c_libraries,
      cmdclass=cmdclass,
      ext_modules=[pyhash],
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: Apache Software License',
          'Natural Language :: English',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: C++',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Internet',
          'Topic :: Software Development',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Utilities'
      ],
      keywords='hash hashing fasthash',
      setup_requires=list(filter(None, [
          'cpuid' if IS_X86 else None,
          'pybind11',
      ])),
      tests_require=['pytest', 'pytest-runner', 'pytest-benchmark'],
      )
