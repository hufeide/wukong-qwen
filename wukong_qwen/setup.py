from setuptools import setup, find_packages

setup(
    name="wukong_deepseek",
    version="0.1.0",
    description="将DeepSeek R1接入到悟空机器人中，接管人机交互",
    author="AI开发者",
    author_email="your-email@example.com",
    python_requires=">=3.7",
    packages=find_packages(),
    py_modules=["main", "robot_client", "deepseek_client", "voice_listener"],
    install_requires=[
        "alphamini",
        "openai==1.13.3",
        "requests==2.31.0",
        "aiohttp==3.9.1",
        "python-dotenv==1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "wukong_deepseek=main:main",
        ],
    },
) 