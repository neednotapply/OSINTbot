from setuptools import setup

setup(
    name='osintbot-tool-shims',
    version='0.4.1',
    py_modules=['osintbot_tool_shims'],
    install_requires=[
        'requests==2.32.5',
        'certifi==2026.2.25',
    ],
    entry_points={
        'console_scripts': [
            'sherlock=osintbot_tool_shims:sherlock_main',
            'user-scanner=osintbot_tool_shims:user_scanner_main',
            'holehe=osintbot_tool_shims:holehe_main',
        ],
    },
)
