from setuptools import setup, find_packages

setup(
    name='sw',
    version='0.1',
    url='https://github.com/dgsb/sw',
    author='David Bariod',
    author_email='davidriod@googlemail.com',
    license='MIT',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Source Management Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.5',
    ],
    keywords='git svn wrapper',
    package=find_packages(),
    install_requires=['sh'],
    entry_points = {
        'console_scripts': [
                'sw=sw.sw:main'
        ]
    }
)
