from setuptools import setup, find_packages

setup(
    name='lp2',
    version='0.1.0',
    description='Lean4-Python bidirectional transpiler',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'lp2=lp2.cli:main',
        ],
    },
    python_requires='>=3.10',
)
