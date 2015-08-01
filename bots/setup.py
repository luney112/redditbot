import setuptools

setuptools.setup(
    name='redditbot.bots',
    version='1.0.0',
    author='Jeremy Simpson',
    description='Redditbot bots',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    packages=setuptools.find_packages(),
    namespace_packages=['redditbot'],
    entry_points={
        'console_scripts': [
            'runbot-emote-counter = redditbot.bots.emote_counter.runbot:run',
            'runbot-xkcdref = redditbot.bots.xkcdref.runbot:run'
        ]
    }
)
