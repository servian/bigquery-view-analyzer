from setuptools import setup, find_packages

LONG_DESCRIPTION = open("README.md").read()

INSTALL_REQUIRES = ["google-cloud-bigquery", "anytree", "colorama"]

TESTS_REQUIRE = INSTALL_REQUIRES + ["pytest>=3.6", "pytest-cov", "coverage"]

setup(
    name="bigquery-view-analyzer",
    url="http://github.com/servian/bigquery-view-analyzer/",
    author="Chris Tippett",
    author_email="chris.tippett@servian.com",
    version="19.6.0",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages("src"),
    description="Command-line tool for working with BigQuery views",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    setup_requires=["pytest-runner"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
    ],
)
