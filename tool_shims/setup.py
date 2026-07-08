from setuptools import setup

setup(
    name='osintbot-tool-shims',
    version='0.1.0',
    py_modules=['osintbot_tool_shims'],
    entry_points={
        'console_scripts': [
            'sherlock=osintbot_tool_shims:sherlock_main',
            'user-scanner=osintbot_tool_shims:user_scanner_main',
        ],
    },
)
