import setuptools

setuptools.setup(
    name='redditbot.base',
    version='1.0.0',
    author='Jeremy Simpson',
    description='Redditbot framework',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    packages=setuptools.find_packages(),
    namespace_packages=['redditbot'],
)
