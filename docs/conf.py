import datetime

import pkg_resources

master_doc = 'index'
project = 'sprockets-postgres'
release = version = pkg_resources.get_distribution(project).version
copyright = '{}, AWeber Communications'.format(datetime.date.today().year)

html_theme = 'sphinx_rtd_theme'
html_theme_path = ['_themes']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
    'sphinx.ext.viewcode'
]

set_type_checking_flag = True
typehints_fully_qualified = True
always_document_param_types = True
typehints_document_rtype = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
intersphinx_mapping = {
    'aiopg': ('https://aiopg.readthedocs.io/en/stable/', None),
    'psycopg2': ('http://initd.org/psycopg/docs/', None),
    'python': ('https://docs.python.org/3', None),
    'sprockets-http': (
        'https://sprocketshttp.readthedocs.io/en/master/', None),
    'sprockets-influxdb': (
        'https://sprockets-influxdb.readthedocs.io/en/latest/', None),
    'sprockets.mixins.metrics': (
        'https://sprocketsmixinsmetrics.readthedocs.io/en/latest/', None),
    'tornado': ('http://tornadoweb.org/en/latest/', None)
}

autodoc_default_options = {'autodoc_typehints': 'description'}

