from setuptools import setup, find_packages

LONG_DESCRIPTION = open("README.md").read()

INSTALL_REQUIRES = [
    "google-cloud-bigquery>=1.23",
    "six<2.0.0dev,>=1.13.0",
    "anytree==2.8.0",
    "colorama==0.4.3",
    "yaspin==0.16.0",
    "Click==7.0"
]

TESTS_REQUIRE = INSTALL_REQUIRES + ["pytest>=3.6", "pytest-cov", "coverage"]

setup(
    name="bigquery-view-analyzer",
    url="http://github.com/servian/bigquery-view-analyzer/",
    author="Chris Tippett",
    author_email="chris.tippett@servian.com",
    version="20.3.1",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages("src"),
    description="A command-line tool for visualizing dependencies and managing permissions between BigQuery views",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    setup_requires=["pytest-runner"],
    entry_points={"console_scripts": ["bqva=bigquery_view_analyzer.cli:main"]},
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
