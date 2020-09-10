import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='master-ssh',
    version='2.0.7',
    author='Jaan Porkon',
    author_email='jaantrill@gmail.com',
    description='Tool to connect to multiple SSH servers and broadcast commands.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/JaanPorkon/master-ssh',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=['requests', 'paramiko', 'configparser', 'termcolor'],
    scripts=['bin/master-ssh']
)