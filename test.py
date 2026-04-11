import os
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("DEEPSEEK_API_KEY"))  # 应该输出你的密钥（前几位可见）