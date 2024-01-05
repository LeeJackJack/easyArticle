# main.py
import json
from flask import Flask, render_template, request, stream_with_context, Response, jsonify
import requests
from dotenv import load_dotenv
from generate.text_to_image import generate_and_stream, generate_and_stream_plot_image, generate_and_save_plot_image, \
    test_generate_and_stream
from generate.completions import get_lan_response
from database.models import db
import os
from flask_cors import cross_origin, CORS
from controllers.user_controller import add_user, find_user_by_open_id, edit_user
from controllers.protagonist_controller import get_preset_role, generate_role_image, get_protagonist, get_protagonist_list, add_protagonist
from controllers.story_plot_controller import get_random_story_plot
from controllers.description_controller import get_description
from controllers.album_controller import get_album, edit_album
from controllers.game_controller import get_game, reset_game_plot, add_game, save_game_data, save_game_first_time, edit_game
from controllers.image_controller import add_plot_image, get_image, edit_image
from controllers.theme_controller import get_theme_list, add_theme, get_theme
from controllers.pro_and_alb_controller import create_pro_and_alb
from generate.qinghua_completions import submit_plot_choice, get_random_plot, create_img_prompt, \
    create_plot, init_game_data, test_fake_init
from flask_jwt_extended import JWTManager, create_access_token
from app_instance import app
import zhipuai
import re
from service.baidu_orc import get_orc_content

load_dotenv()  # 加载 .env 文件中的变量
CORS(app)

# 使用 os.environ 从 .env 文件中获取配置
DATABASE_USERNAME = os.environ['DATABASE_USERNAME']
DATABASE_PASSWORD = os.environ['DATABASE_PASSWORD']
DATABASE_HOST = os.environ['DATABASE_HOST']
DATABASE_NAME = os.environ['DATABASE_NAME']
DATABASE_URI = f"mysql+pymysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# JWT 配置
app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_SECRET']  # JWT秘钥
jwt = JWTManager(app)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/generateImg', methods=['GET'])
def generate_img():
    # prompt = request.json.get('prompt')
    return Response(stream_with_context(test_generate_and_stream()), content_type='text/plain')


@app.route('/generateGpt', methods=['GET'])
def generate_gpt():
    response = get_lan_response()
    return jsonify({"response": response})


@app.route('/getPlot', methods=['GET'])
def get_story_plot():
    chapter = int(request.args.get('chapter_next'))
    # print(chapter)
    theme_id = int(request.args.get('theme_id'))
    plot = get_random_story_plot(chapter, theme_id)
    return jsonify(plot)


@app.route('/getPlotImage', methods=['POST'])
def get_story_plot_image():
    # plot_id = request.json.get('plot_id')
    plot_id = 23
    description = get_description(plot_id=plot_id)

    return Response(stream_with_context(generate_and_stream_plot_image(description['content'])), content_type='text/plain')


@app.route('/getAlbum', methods=['GET'])
def get_album_route():
    # 获取请求中的 'id' 参数
    album_id = request.args.get('album_id', type=int)
    result = get_album(album_id=album_id)
    return jsonify(result)


@app.route('/getProtagonist', methods=['GET'])
def get_protagonist_data():
    # 获取请求中的 'id' 参数
    protagonist_id = request.args.get('protagonist_id', type=int)
    result = get_protagonist(id=protagonist_id)
    return jsonify(result)


@app.route('/changeImage', methods=['GET'])
def change_plot_image():
    description = request.args.get('description')
    album_id = request.args.get('album_id', type=int)
    user_id = request.args.get('user_id', type=int)
    result = generate_and_save_plot_image(description, album_id, user_id)
    next(result)
    image_url = next(result)
    return jsonify(image_url)


@app.route('/saveAlbum', methods=['GET'])
def save_album():
    album_id = request.args.get('album_id', type=int)
    data = request.args.get('formData')
    # print(data)
    result = edit_album(album_id=album_id, content=data)
    return jsonify(result)


# 获取预设角色描述及图片
@app.route('/api/roles/preset/random', methods=['GET'])
def get_preset_role_route():
    preset_str = request.args.get('preset', default="false")
    preset = preset_str.lower() != "false"  # 如果 preset_str 不是 "false"，则 preset 为 True
    user_id = request.args.get('user_id', type=int)  # 获取 user_id 参数
    return get_preset_role(user_id=user_id, preset=preset)


# 创建角色（Protagonist）和绘本（Album）并返回相关数据。
# 创建角色并将描述和图片保存到数据库
@app.route('/createProAndAlb', methods=['POST'])  # 使用 POST 方法，因为我们要创建新资源。
def create_pro_and_alb_route():
    data = request.json
    user_id = int(data.get('user_id'))
    description = data.get('description')
    protagonist_id = int(data.get('protagonist'))
    name = data.get('name')
    race = data.get('race')
    feature = data.get('feature')
    preset = data.get('preset', False)
    theme_id = int(data.get('theme_id'))  # 新添加的字段，用于绘本的主题ID
    album_name = data.get('album_name')  # 新添加的字段，用于绘本名称
    content = data.get('content')  # 新添加的字段，用于绘本内容
    image_id = data.get('image_id', None)  # 新添加的字段，用于角色图片ID

    result = create_pro_and_alb(user_id, description, name, race, feature, preset, theme_id, album_name, content, image_id)
    return jsonify(result)


# 根据编辑的描述生成图片
@app.route('/api/roles/generate-image', methods=['POST'])
def generate_role_image_route():
    description = request.json.get('description')
    return generate_role_image(description)


# 20230901 新版本新增接口 ----------------------------------------------------------------------------------------
@app.route('/getGameData', methods=['GET'])
def get_game_data():
    game_id = int(request.args.get('id'))
    result = get_game(game_id)
    return jsonify(result)


@app.route('/getRandomPlot', methods=['GET'])
def refresh_plot():
    game_id = int(request.args.get('id'))
    result = get_random_plot(game_id)
    return jsonify(result)


@app.route('/submitAnswer', methods=['GET'])
def submit_answer():
    choice = request.args.get('choice')
    game_id = int(request.args.get('id'))
    result = submit_plot_choice(game_id, choice)
    # print(result)
    return jsonify(result)


# 用户输入转图片创造
@app.route('/createPlotImage', methods=['GET'])
def create_plot_image():
    content = request.args.get('content')
    game_id = int(request.args.get('game_id'))
    user_id = int(request.args.get('user_id'))
    prompt = create_img_prompt(content)

    if prompt:
        generator = generate_and_stream_plot_image(prompt)
        next(generator)
        generated_image_url = next(generator)

        # 保存图片数据
        result = add_plot_image(image_url=generated_image_url, plot_description=json.loads(content)['content'],
                                game_id=game_id, user_id=user_id, image_description=prompt)
        # print(result)
        return jsonify(result)


@app.route('/refreshPlotImage', methods=['GET'])
def refresh_plot_image():
    content = request.args.get('content')
    image_id = int(request.args.get('image_id'))
    prompt = create_img_prompt(content)

    # 获取图像内容
    image = get_image(image_id=image_id)

    if prompt:
        generator = generate_and_stream_plot_image(prompt)
        next(generator)
        generated_image_url = next(generator)

        # 保存图片数据
        result = add_plot_image(image_url=generated_image_url, plot_description=image['plot_description'],
                                game_id=image['game_id'], user_id=image['user_id'], image_description=prompt)
        # print(result)
        return jsonify(result)


@app.route('/confirmChosenImage', methods=['GET'])
def confirm_chosen_image():
    image_id = int(request.args.get('image_id'))
    # 修改图像为已选择
    image = edit_image(image_id=image_id)
    return jsonify(image)


@app.route('/createChoice', methods=['GET'])
def create_plot_content():
    choice = request.args.get('choice')
    game_id = int(request.args.get('game_id'))
    result = create_plot(choice, game_id)
    return jsonify(result)


@app.route('/resetStory', methods=['GET'])
def reset_game():
    game_id = int(request.args.get('game_id'))
    result = reset_game_plot(game_id)
    # print(result)
    return jsonify(result)


# 获取微信用户登录信息
@app.route('/wxLogin', methods=['GET'])
def wx_login():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Missing code"}), 400

    # 与微信服务器交互，获取 openId 和 sessionKey
    payload = {
        'appid': os.environ['MINI_PROGRAM_APP_ID'],
        'secret': os.environ['MINI_PROGRAM_APP_SECRET'],
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.get(os.environ['WX_LOGIN_URL'], params=payload)
    data = response.json()

    session_key = data['session_key']
    openid = data['openid']
    token = create_access_token(identity={'session_key': session_key, 'openid': openid})

    # 先查找用户是否已存在
    user = find_user_by_open_id(openid)
    # 不存在则存储新用户
    if not user:
        user = add_user(open_id=openid, session_key=session_key, token=token)

    return jsonify(user)


# 更新微信用户登录信息
@app.route('/wxLoginUpdate', methods=['GET'])
def wx_login_update():
    avatar_url = request.args.get('avatarUrl')
    city = request.args.get('city')
    country = request.args.get('country')
    gender = request.args.get('gender')
    language = request.args.get('language')
    nick_name = request.args.get('nickName')
    province = request.args.get('province')
    user_id = request.args.get('user_id')

    # 更新用户表信息
    user = edit_user(user_id=user_id, avatar_url=avatar_url, city=city, country=country, gender=gender,
                     language=language, nick_name=nick_name, province=province)

    return jsonify(user)


# 获取故事主题信息
@app.route('/getThemeData', methods=['GET'])
def get_theme_data_list():
    result = get_theme_list()
    print(result)
    return jsonify(result)


# 获取随机n个角色信息
@app.route('/getRoleData', methods=['GET'])
def get_random_protagonist_data():
    n = 7
    result = get_protagonist_list(n)
    # print(result)
    return jsonify(result)


# 用户自定义角色信息
@app.route('/createRoleData', methods=['GET'])
def create_protagonist_data():
    name = request.args.get('name')
    description = request.args.get('description')
    user_id = request.args.get('user_id')
    result = add_protagonist(user_id=user_id, description=description, name=name, preset=False)
    return jsonify(result)


# 用户自定义故事主题
@app.route('/createThemeData', methods=['GET'])
def create_theme_data():
    theme = request.args.get('theme')
    description = request.args.get('description')
    result = add_theme(theme=theme, description=description, preset=False)
    return jsonify(result)


# 用户根据主角，故事主题创建游戏
@app.route('/initGameData', methods=['GET'])
def init_game_start_data():
    theme_id = int(request.args.get('theme_id'))
    user_id = int(request.args.get('user_id'))
    protagonist_id = int(request.args.get('protagonist_id'))
    # 获取故事主角信息
    protagonist = get_protagonist(id=protagonist_id)
    # print(protagonist)
    # 获取故事主题信息
    theme = get_theme(theme_id=theme_id)
    # 调用大模型，初始化故事的内容
    init_story_result = init_game_data(theme=json.dumps(theme), protagonist=json.dumps(protagonist))
    print(init_story_result)
    # 保存数据内容到数据库
    result = save_game_data(user_id=user_id, theme=json.dumps(theme), protagonist=json.dumps(protagonist), game_data=json.dumps(init_story_result))
    return {'new_game_id': result, 'protagonist_id': protagonist_id}


# 获取特定故事主题内容
@app.route('/getTheme', methods=['GET'])
def get_theme_data():
    theme_id = request.args.get('theme_id')
    result = get_theme(theme_id=theme_id)
    return jsonify(result)


@app.route('/testFakeInit', methods=['GET'])
def test_invoke():
    result = test_fake_init()
    return jsonify(result)


@app.route('/testStreamResponse', methods=['POST'])
def test_stream_response():
    def generate():
        prompt = [{
            "role": "user",
            "content": "你好"
        }]
        response = zhipuai.model_api.sse_invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=0.7,
            top_p=0.7,
        )
        for event in response.events():
            if event.event == "add":
                yield event.data
            elif event.event == "error" or event.event == "interrupted":
                print(event.data)
            elif event.event == "finish":
                print(event.data)
                print(event.meta)
            else:
                print(event.data)
    return Response(stream_with_context(generate()), content_type='text/event-stream')


@app.route('/generatePlot', methods=['POST'])
def generate_game_data():
    def generate():
        # 解析请求体中的 JSON 数据
        data = request.get_json()

        # 提取前端传来的参数
        theme_id = int(data.get('theme_id'))
        user_id = int(data.get('user_id'))
        protagonist_id = int(data.get('protagonist_id'))

        # 获取主角信息
        protagonist = get_protagonist(id=protagonist_id)

        # 获取主题信息
        theme = get_theme(theme_id=theme_id)

        # 把主角信息及主题信息初始化一次到故事数据库，后续再保存故事情节
        # init_game_data(theme=json.dumps(theme), protagonist=json.dumps(protagonist))

        # 构建与大模型交互的prompt
        re_start_str = f"游戏主题：{theme['description']}，游戏主角：{protagonist['name'] + '，' + protagonist['description']}"
        prompt = [
            {"role": "user",
             "content": "我希望你扮演一个基于文本的冒险游戏，游戏主题：（稍后提供），游戏主角：（稍后提供）。如果你明白了就回复“收到”，之后我会给你介绍这个游戏的规则。"},
            {"role": "assistant",
             "content": " 收到，我已经明白了。请告诉我这个游戏的规则。"},
            {"role": "user",
             "content": "游戏总共 8 回合，每一个回合你都需要生成故事内容和a、b、c三个选项。如果你明白了就回复“收到”，之后我会给你介绍每个回合生成内容的规则。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请告诉我每个回合生成内容的规则。"},
            {"role": "user",
             "content": "每个回合都包含以下的字段，分别是：回合数，章节名，故事内容，故事选项。如果你明白了就回复“收到”，之后我会给你介绍每个字段的规则。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请告诉我每个字段的规则。"},
            {"role": "user",
             "content": "1、回合数：记录当前回合数，整数类型，从0开始增加，到8终止；2、章节名：记录当前章节名字，枚举类型，分别是：故事的开端，情节推进，矛盾产生，关键决策，情节发展，高潮冲突，结局逼近，最终结局，章节名分别与回合数一一对应，回合1对应故事的开端，回合2对应情节推进，回合3对应矛盾产生，回合4对应关键决策，回合5对应情节发展，回合6对应高潮冲突，回合7对应结局逼近，回合8对应最终结局；3、故事内容：根据当前章节名的剧情提示，生成与上一个回合内容及选项相关的故事内容；4、故事选项：根据当前故事内容，生成3个相关的会影响故事发展的选项；如果你明白了就回复“收到”，之后我会给你介绍这个游戏的玩法。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请告诉我这个游戏的玩法。"},
            {"role": "user",
             "content": "1、你需要根据我提供的游戏主题和游戏主角，先生成第一回合的所有内容给我；2、如果我回复游戏选项里的其中一个，你需要根据我回复的选项，生成下一个回合的所有内容给我；3、如果我回复“自定义”，你需要根据我回复的自定义内容，生成下一个回合的所有内容给我；4、如果我回复“换一换”，你需要重新生成当前回合的所有内容给我；如果你明白了就回复“收到”，之后我会给你介绍这个游戏的限制。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请告诉我这个游戏的限制。"},
            {"role": "user",
             "content": "1、每个回合的故事内容必须控制在 80 字以内，游戏在第8回合结束；2、你给我生成的故事内容和故事选项需要是有趣搞怪一点的，前后逻辑有联系的，不要太拘泥于常规的内容，虚幻，古代，现实的题材都可以；3、每个回合的情节结构必须和章节名对应，8个回合8个情节循序渐进，缺一不可；如果你明白了就回复“收到”，之后我会给你介绍你回复的格式要求。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请告诉我回复的格式要求。"},
            {"role": "user",
             "content": "回复的格式必须要json格式，key的对应关系如下：round对应回合数，chapter对应章节名，content对应故事内容，choice对应故事选项；参考示例：{\"round\":\"xxx\",\"chapter\":\"xxx\",\"content\":\"xxx\",\"choice\":[\"a.xxx\",\"b.xxx\",\"c.xxx\"]}；如果你明白了就回复“收到”，之后我就会给你发送游戏主题和游戏主角，然后游戏开始。"},
            {"role": "assistant",
             "content": "收到，我已经明白了。请发送游戏主题和游戏主角，我将开始游戏。"},
            {"role": "user",
             "content": re_start_str}]

        # 调用大模型接口实现内容生成
        response = zhipuai.model_api.sse_invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=0.9,
            top_p=0.7,
            incremental=True
        )

        # 定义变量记录生成过程的中间内容
        full_text = ""

        # 循环获取大模型生成的内容
        for event in response.events():
            if event.event == "add":
                full_text += event.data
                # 先把故事内容返回到前端使用
                if '"content": "' in full_text:
                    start_index = full_text.index('"content": "') + len('"content": "')
                    recorded_content = full_text[start_index:]
                    if '"' not in recorded_content:
                        yield json.dumps({'status': 'generate', 'content': recorded_content})
            elif event.event == "finish":
                try:
                    # 生成完毕后处理一下字符串转化成json格式
                    json_match = re.search(r'\{.*?\}', full_text, re.DOTALL)
                    json_content = json_match.group(0)
                    # 组装新的prompt history
                    prompt_history = {
                        'role': 'assistant',
                        'content': json_content
                    }
                    prompt.append(prompt_history)

                    # 执行数据库操作
                    result = save_game_first_time(user_id=user_id, theme=json.dumps(theme),
                                                  protagonist=json.dumps(protagonist), game_data=json.dumps(prompt))

                    # 构造要返回的字符串
                    response_str = json.dumps({'status': 'finish', 'game': result})
                    print(response_str)
                    yield response_str
                except Exception as e:
                    print("数据库操作失败:", e)
                    yield json.dumps({'status': 'error', 'message': str(e)})
            elif event.event == "error" or event.event == "interrupted":
                yield "error"
            else:
                yield "unknown"
    return Response(stream_with_context(generate()), content_type='application/json')


@app.route('/submitAnswerStream', methods=['POST'])
def submit_answer_stream():
    def generate():
        # 解析请求体中的 JSON 数据
        data = request.get_json()

        # 提取前端传来的参数
        choice = data.get('choice')
        game_id = data.get('id')

        # 获取故事信息
        game = get_game(id=game_id)
        content = json.loads(game['content'])
        prompt = json.loads(game['prompt_history'])
        new_entry = {
            'role': 'user',
            'content': choice
        }
        prompt.append(new_entry)

        response = zhipuai.model_api.sse_invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=0.9,
            top_p=0.7,
            incremental=True
        )
        full_text = ""

        # 循环获取大模型生成的内容
        for event in response.events():
            if event.event == "add":
                full_text += event.data
                # 先把故事内容返回到前端使用
                if '"content": "' in full_text:
                    start_index = full_text.index('"content": "') + len('"content": "')
                    recorded_content = full_text[start_index:]
                    if '"' not in recorded_content:
                        yield json.dumps({'status': 'generate', 'content': recorded_content})
            elif event.event == "finish":
                # 生成完毕后处理一下字符串转化成json格式
                json_match = re.search(r'\{.*?\}', full_text, re.DOTALL)
                json_content = json_match.group(0)
                # 组装新的prompt history
                prompt_history = {
                    'role': 'assistant',
                    'content': json_content
                }
                prompt.append(prompt_history)
                content.append(json.loads(json_content))

                # 保存新的数据内容到故事数据库
                result = edit_game(id=game_id, prompt_history=json.dumps(prompt, ensure_ascii=False),
                                   content=json.dumps(content, ensure_ascii=False))
                # 构造要返回的字符串
                response_str = json.dumps({'status': 'finish', 'game': result})
                yield response_str
            elif event.event == "error" or event.event == "interrupted":
                yield "error"
            else:
                yield "unknown"
    return Response(stream_with_context(generate()), content_type='application/json')


@app.route('/createChoiceStream', methods=['POST'])
def create_plot_content_stream():
    def generate():
        # 解析请求体中的 JSON 数据
        data = request.get_json()
        # 提取前端传来的参数
        choice = data.get('choice')
        game_id = data.get('game_id')
        game = get_game(id=game_id)
        content = json.loads(game['content'])
        prompt = json.loads(game['prompt_history'])
        new_entry = {
            'role': 'user',
            'content': f'自定义：{choice}'
        }
        prompt.append(new_entry)
        response = zhipuai.model_api.sse_invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=0.9,
            top_p=0.7,
            incremental=True
        )
        full_text = ""

        # 循环获取大模型生成的内容
        for event in response.events():
            if event.event == "add":
                full_text += event.data
                # 先把故事内容返回到前端使用
                if '"content": "' in full_text:
                    start_index = full_text.index('"content": "') + len('"content": "')
                    recorded_content = full_text[start_index:]
                    if '"' not in recorded_content:
                        yield json.dumps({'status': 'generate', 'content': recorded_content})
            elif event.event == "finish":
                # 生成完毕后处理一下字符串转化成json格式
                json_match = re.search(r'\{.*?\}', full_text, re.DOTALL)
                json_content = json_match.group(0)
                # 组装新的prompt history
                prompt_history = {
                    'role': 'assistant',
                    'content': json_content
                }
                prompt.append(prompt_history)
                content.append(json.loads(json_content))

                # 保存新的数据内容到故事数据库
                result = edit_game(id=game_id, prompt_history=json.dumps(prompt, ensure_ascii=False),
                                   content=json.dumps(content, ensure_ascii=False))
                # 构造要返回的字符串
                response_str = json.dumps({'status': 'finish', 'game': result})
                yield response_str
            elif event.event == "error" or event.event == "interrupted":
                yield "error"
            else:
                yield "unknown"

    return Response(stream_with_context(generate()), content_type='application/json')


@app.route('/testBaiduOcr', methods=['POST'])
def test_ali_ocr():
    image_base64 = request.json.get('image_base64')
    # print(image_base64)
    result = get_orc_content(image_base64)
    return jsonify(result)


@app.route('/testArticleEvaluate', methods=['POST'])
def test_article_evaluate():
    def generate():
        # 解析请求体中的 JSON 数据
        data = request.get_json()

        # 提取前端传来的参数
        article = data.get('article')

        # 构建与大模型交互的prompt
        prompt = [
            {"role": "user",
             "content": "中国小学各年级作文要求如下，请你牢记。"
                        "一年级：主要是让学生学会运用简单的词语和句子表达自己的思想和感受，培养写作的兴趣。一般要求写句子、短文，内容可以是自己身边的事物、人物，也可以是想象中的事物。"
                        "二年级：在一年级的基础上，二年级的作文要求学生能够运用更加丰富的词汇和句式进行表达，能写简单的记叙文和说明文。内容可以包括生活琐事、人物、景物等。"
                        "三年级：三年级的学生需要在掌握基本语法和句式的基础上，学会进行合理的分段和连段成篇。能够写一些简单的记叙文、说明文和应用文，如书信、日记等。"
                        "四年级：开始学习写作的篇章结构，如开头、结尾的写法，学会使用恰当的过渡语。在内容上，可以尝试写一些观察日记、读书笔记、游记等。"
                        "五年级：要求学生能够独立构思和写作，能写一些复杂的记叙文、说明文和应用文。此外，还需要学会对文章进行修改和润色。"
                        "六年级：六年级的作文要求学生能够熟练掌握各种文体的写作方法，如议论文、散文等。此外，还需要提高自己的审美和批判能力，学会对自己和他人的文章进行评价。"},
            {"role": "assistant",
             "content": "收到，我已经记住了。请告诉我接下来需要我提供什么帮助。"},
            {"role": "user",
             "content": "接下来我会向你提供一篇小学作文，你需要给这篇作为进行评分，给出ABCD四种评分，并说明为什么。然后结合小学作文要求，给这篇作文提供评价及改进方向。你的改进方向需要具体一点"},
            {"role": "assistant",
             "content": "收到，我已经明白了，请你把文章发给我。"},
            {"role": "user",
             "content": article}]

        # 调用大模型接口实现内容生成
        response = zhipuai.model_api.sse_invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=0.9,
            top_p=0.7,
            incremental=True
        )

        # 定义变量记录生成过程的中间内容
        full_text = ""

        # 循环获取大模型生成的内容
        for event in response.events():
            if event.event == "add":
                full_text += event.data
                yield json.dumps({'status': 'generate', 'content': full_text})
            elif event.event == "finish":
                yield json.dumps({'status': 'finish', 'content': full_text})
            elif event.event == "error" or event.event == "interrupted":
                yield "error"
            else:
                yield "unknown"

    return Response(stream_with_context(generate()), content_type='application/json')


if __name__ == '__main__':
    app.run()
    # socketio.run(app, debug=True)
