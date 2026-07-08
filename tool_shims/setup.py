from setuptools import setup

setup(
    name='osintbot-tool-shims',
    version='0.2.0',
    py_modules=['osintbot_tool_shims'],
    install_requires=[
        'requests>=2.32',
        'certifi>=2024.8.30',
    ],
    entry_points={
        'console_scripts': [
            'sherlock=osintbot_tool_shims:sherlock_main',
            'user-scanner=osintbot_tool_shims:user_scanner_main',
        ],
    },
)
