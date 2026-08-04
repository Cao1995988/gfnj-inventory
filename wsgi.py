import os
import sys

# 将项目目录加入 path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# 导入 Flask 应用
from app import app, init_db

# 初始化数据库
init_db()

# WSGI 入口
application = app
