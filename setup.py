import io
import os
import subprocess

from setuptools import setup, find_packages
import versioneer


def get_long_description():
    with io.open('./README.md', encoding='utf-8') as f:
        readme = f.read()
    path = None
    pandoc_paths = ('/usr/local/bin/pandoc', '/usr/bin/pandoc')
    for p in pandoc_paths:
        if os.path.exists(p):
            path = p
            break

    if path is None:
        print('Pandoc not found, tried: {}'.format(pandoc_paths))
        return readme

    cmd = [path, '--from=markdown', '--to=rst']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    doc = readme.encode('utf8', errors='replace')
    rst = p.communicate(doc)[0]

    return str(rst)


tests_require = [
    'pytest',
    'pytest-asyncio',
    'cachetools',
    'aioredis',
    'tox',
]


setup(
    name='easy-cache-async',
    packages=find_packages(exclude=('tests', )),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Useful cache decorators for methods and properties',
    author='Oleg Churkin',
    author_email='bahusoff@gmail.com',
    url='https://github.com/Bahus/easy_cache_async',
    keywords=['cache', 'decorator', 'invalidation',
              'locmem', 'redis', 'asyncio'],
    platforms='Platform Independent',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License'
    ],
    long_description=get_long_description(),
    requires=[],
    install_requires=['cachetools', 'aioredis'],
    tests_require=tests_require,
    extras_require={
        'tests': tests_require,
        'locmem': ['cachetools'],
        'redis': ['aioredis'],
    },
)
