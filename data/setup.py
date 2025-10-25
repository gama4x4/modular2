from setuptools import setup, find_packages

setup(
    name="ml_tiny_modular",
    version="0.1.0",
    description="Sistema modular para integração Mercado Livre e Tiny ERP com scraping, fila de tarefas e automação.",
    author="Seu Nome",
    author_email="seu@email.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests",
        "beautifulsoup4",
        "lxml"
    ],
    entry_points={
        'console_scripts': [
            'ml-worker=run_workers:run_all_workers'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
