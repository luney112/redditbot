import setuptools
import pip

if pip.main(['install', '-r', 'install/requirements.txt']) != 0:
    raise Exception('Pip install requirements failed')

setuptools.setup(
    name='redditbot.base',
    version='1.0.0',
    author='Jeremy Simpson',
    description='Redditbot framework',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],
    packages=setuptools.find_packages(),
    namespace_packages=['redditbot'],
)
