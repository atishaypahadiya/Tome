"""Configuration and settings for the Tome scanner."""

# Directories to skip during scanning
IGNORE_DIRS = {
    'node_modules',
    '__pycache__',
    '.git',
    'venv',
    '.venv',
    'env',
    '.env',
    'dist',
    'build',
    '.tox',
    '.mypy_cache',
    '.pytest_cache',
    '.eggs',
    '.next',
    '.nuxt',
}

# File extensions to parse for imports
PYTHON_EXTENSIONS = {'.py'}
JS_TS_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx'}

# Known binary extensions to skip without reading
BINARY_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.o', '.a', '.lib', '.dll', '.dylib',
    '.exe', '.bin',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg', '.webp',
    '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
    '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.woff', '.woff2', '.ttf', '.eot',
    '.db', '.sqlite', '.sqlite3',
    '.npy', '.npz',
    '.class', '.jar',
}

# Max file size to read (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# File status categories by extension
FILE_CATEGORIES = {
    # config
    '.json': 'config', '.yml': 'config', '.yaml': 'config',
    '.toml': 'config', '.ini': 'config', '.cfg': 'config',
    '.env': 'config',
    # documentation
    '.md': 'documentation', '.txt': 'documentation', '.rst': 'documentation',
    # asset
    '.html': 'asset', '.css': 'asset', '.scss': 'asset', '.less': 'asset',
    '.svg': 'asset',
}

# Filenames that are always "build" category regardless of extension
BUILD_FILENAMES = {
    '.gitignore', '.gitattributes', '.dockerignore',
    'requirements.txt', 'requirements-dev.txt',
    'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'Makefile', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'setup.py', 'setup.cfg', 'pyproject.toml',
    'tsconfig.json', 'jest.config.js', 'babel.config.js',
    '.eslintrc', '.eslintrc.json', '.eslintrc.js',
    '.prettierrc', '.prettierrc.json',
    'Procfile', 'Gemfile', 'Rakefile',
    '.env.example', '.env.template',
}

# Well-known entry point filenames
ENTRY_POINT_FILENAMES = {
    'main.py', 'app.py', 'index.js', 'main.js', 'server.py',
    'manage.py', 'wsgi.py', 'asgi.py', 'cli.py',
}

# Git lookback period
GIT_LOOKBACK_MONTHS = 6
