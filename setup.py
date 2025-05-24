from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="TeleFlow",
    version="0.2.0",
    author="Ahmed Negm",
    author_email="A7medNegm.x@gmail.com",
    description="Asynchronous Telegram Bot API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x7007x/NegmPy",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "aiohttp>=3.7.4",
        "typing_extensions>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15.1",
            "black>=21.6b0",
        ],
    },
)
