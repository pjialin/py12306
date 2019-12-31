import warnings

# Disable aiohttp annoying warn
warnings.filterwarnings('ignore', category=DeprecationWarning, module='aiohttp')
# disable unittest warnnings
default_filterwarnings = warnings.filterwarnings
warnings.simplefilter = lambda *args, **kwargs: None if args[0] == 'default' and not \
    kwargs else default_filterwarnings(*args, **kwargs)
