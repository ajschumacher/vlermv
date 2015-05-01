from distutils.core import setup

setup(name='vlermv',
      author='Thomas Levine',
      author_email='_@thomaslevine.com',
      description='Easily dump python objects to files, and then load them back.',
      url='https://github.com/tlevine/vlermv',
      packages=['vlermv', 'vlermv.serializers', 'vlermv.transformers'],
      install_requires = [],
      tests_require = ['nose'],
      version='1.0.0',
      license='AGPL',
)
