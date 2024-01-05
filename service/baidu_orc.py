import requests
import base64
import urllib
from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件中的变量
API_KEY = os.environ['BAIDU_OCR_KEY']
SECRET_KEY = os.environ['BAIDU_OCR_SECRET']
END_POINT = os.environ['BAIDU_OCR_ENDPOINT']
ACCESS_TOKEN_END_POINT = os.environ['BAIDU_OCR_ACCESS_TOKEN_ENDPOINT']


def get_orc_content(image_base64):
    url = END_POINT + get_access_token()

    # image_data = base64.b64decode(image_base64)
    # 获取图片
    # image = get_file_content_as_base64(image_url, True)
    payload = 'image=' + urllib.parse.quote(image_base64) + '&detect_direction=false&probability=false'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    return response.text


def get_file_content_as_base64(path, urlencoded=False):
    """
    获取文件base64编码
    :param path: 文件路径
    :param urlencoded: 是否对结果进行urlencoded
    :return: base64编码信息
    """
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)
    return content


def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))
