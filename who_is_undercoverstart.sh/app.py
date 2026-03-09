from flask import Flask, render_template, request, redirect, url_for, session
import random
import os

app = Flask(__name__)
# 从环境变量读取密钥，如果不存在则使用默认值（仅开发用）
app.secret_key = os.environ.get("SECRET_KEY", "undercover_2025_railway")

# 全局房间数据（Render免费版重启会清空，仅临时游玩）
rooms = {}

# 扩容词库（6大类，50+组）
WORD_LIBRARY = {
    "水果类": [
        ("苹果", "梨"), ("香蕉", "芭蕉"), ("草莓", "树莓"), ("西瓜", "哈密瓜"),
        ("荔枝", "龙眼"), ("芒果", "木瓜"), ("橙子", "橘子"), ("葡萄", "提子")
    ],
    "日常用品类": [
        ("牙刷", "牙膏"), ("毛巾", "浴巾"), ("手机", "座机"), ("雨伞", "雨衣"),
        ("拖鞋", "凉鞋"), ("枕头", "抱枕"), ("梳子", "镜子"), ("保温杯", "普通水杯")
    ],
    "食物类": [
        ("米饭", "面条"), ("火锅", "麻辣烫"), ("汉堡", "三明治"), ("炸鸡", "烤鸡"),
        ("奶茶", "果茶"), ("薯片", "薯条"), ("包子", "馒头"), ("饺子", "馄饨")
    ],
    "交通工具类": [
        ("公交车", "出租车"), ("自行车", "电动车"), ("飞机", "高铁"), ("轮船", "游艇"),
        ("摩托车", "电瓶车"), ("火车", "地铁")
    ],
    "娱乐类": [
        ("王者荣耀", "和平精英"), ("电影", "电视剧"), ("唱歌", "跳舞"), ("看书", "看报"),
        ("打游戏", "刷视频"), ("篮球", "足球"), ("麻将", "扑克")
    ],
    "人物类": [
        ("老师", "医生"), ("警察", "消防员"), ("厨师", "服务员"), ("程序员", "产品经理"),
        ("爸爸", "妈妈"), ("哥哥", "弟弟"), ("闺蜜", "兄弟")
    ]
}

# 首页
@app.route('/')
def index():
    # 清空旧session
    session.pop('room', None)
    session.pop('user', None)
    return render_template('index.html')

# 创建房间
@app.route('/create', methods=['POST'])
def create():
    name = request.form['name'].strip()
    if not name:
        return "昵称不能为空！", 400
    
    # 生成4位随机房间号
    room_id = str(random.randint(1000, 9999))
    # 随机选一类词语
    word_type = random.choice(list(WORD_LIBRARY.keys()))
    word_pair = random.choice(WORD_LIBRARY[word_type])
    
    # 初始化房间
    rooms[room_id] = {
        "players": {name: {"status": "alive", "role": ""}},  # role: civilian/undercover
        "host": name,
        "word_type": word_type,
        "word_pair": word_pair,  # (平民词, 卧底词)
        "undercovers": [],  # 卧底列表
        "votes": {},
        "round": 1,
        "eliminated": [],  # 已淘汰玩家
        "status": "waiting"  # waiting/playing/ended
    }
    
    # 分配第一个玩家身份（先不分配，等开始游戏统一分配）
    session['room'] = room_id
    session['user'] = name
    return redirect(url_for('room'))

# 加入房间
@app.route('/join', methods=['POST'])
def join():
    name = request.form['name'].strip()
    room_id = request.form['room'].strip()
    
    if not name or not room_id:
        return "昵称和房间号不能为空！", 400
    if room_id not in rooms:
        return "房间不存在！", 400
    if rooms[room_id]['status'] != "waiting":
        return "游戏已开始，无法加入！", 400
    if name in rooms[room_id]['players']:
        return "昵称已存在，请换一个！", 400
    
    # 添加玩家
    rooms[room_id]["players"][name] = {"status": "alive", "role": ""}
    session['room'] = room_id
    session['user'] = name
    return redirect(url_for('room'))

# 开始游戏（房主专属）
@app.route('/start', methods=['POST'])
def start():
    room_id = session.get('room')
    user = session.get('user')
    
    if not room_id or not user or room_id not in rooms:
        return redirect('/')
    if rooms[room_id]['host'] != user:
        return "只有房主能开始游戏！", 400
    
    room = rooms[room_id]
    player_list = list(room['players'].keys())
    if len(player_list) < 2:
        return "至少需要2名玩家！", 400
    
    # 分配卧底：1~玩家数-1个
    undercover_num = random.randint(1, len(player_list)-1)
    undercovers = random.sample(player_list, undercover_num)
    
    # 给玩家分配身份
    civilian_word, undercover_word = room['word_pair']
    for p in player_list:
        if p in undercovers:
            room['players'][p]['role'] = "undercover"
            room['undercovers'].append(p)
        else:
            room['players'][p]['role'] = "civilian"
    
    # 更新房间状态
    room['status'] = "playing"
    return redirect(url_for('room'))

# 房间页面
@app.route('/room')
def room():
    room_id = session.get('room')
    user = session.get('user')
    
    if not room_id or not user or room_id not in rooms:
        return redirect('/')
    
    room = rooms[room_id]
    # 基础数据
    is_host = (room['host'] == user)
    is_waiting = (room['status'] == "waiting")
    is_playing = (room['status'] == "playing")
    is_ended = (room['status'] == "ended")
    
    # 玩家数据
    all_players = room['players']
    alive_players = [p for p in all_players if all_players[p]['status'] == "alive"]
    eliminated_players = room['eliminated']
    
    # 个人身份和词语
    my_role = all_players[user]['role']
    civilian_word, undercover_word = room['word_pair']
    my_word = undercover_word if my_role == "undercover" else civilian_word
    role_cn = "卧底" if my_role == "undercover" else "平民"
    
    # 胜负判断
    win_result = None
    if is_playing:
        # 存活卧底数
        alive_under = len([p for p in alive_players if p in room['undercovers']])
        alive_civil = len(alive_players) - alive_under
        
        if alive_under == 0:
            win_result = "平民胜利！所有卧底已被淘汰！"
            room['status'] = "ended"
        elif alive_under >= alive_civil:
            win_result = "卧底胜利！卧底数量不少于平民！"
            room['status'] = "ended"
    
    return render_template('home.html',
                           room_id=room_id,
                           user=user,
                           is_host=is_host,
                           is_waiting=is_waiting,
                           is_playing=is_playing,
                           is_ended=is_ended,
                           all_players=all_players,
                           alive_players=alive_players,
                           eliminated_players=eliminated_players,
                           role_cn=role_cn,
                           my_word=my_word,
                           round_num=room['round'],
                           win_result=win_result,
                           word_type=room['word_type'])

# 投票
@app.route('/vote', methods=['POST'])
def vote():
    room_id = session.get('room')
    user = session.get('user')
    target = request.form['target']
    
    if not room_id or not user or room_id not in rooms:
        return redirect('/')
    
    room = rooms[room_id]
    # 只能投存活的非自己的玩家
    if target not in [p for p in room['players'] if room['players'][p]['status'] == "alive" and p != user]:
        return "投票无效！", 400
    
    # 记录投票
    room['votes'][user] = target
    
    # 检查是否所有人都投完票
    alive_players = [p for p in room['players'] if room['players'][p]['status'] == "alive"]
    if len(room['votes']) == len(alive_players):
        # 统计票数
        vote_count = {}
        for t in room['votes'].values():
            vote_count[t] = vote_count.get(t, 0) + 1
        
        # 淘汰最高票玩家
        max_votes = max(vote_count.values())
        eliminated = [p for p in vote_count if vote_count[p] == max_votes][0]
        
        # 更新玩家状态
        room['players'][eliminated]['status'] = "eliminated"
        room['eliminated'].append(eliminated)
        # 重置投票，轮次+1
        room['votes'] = {}
        room['round'] += 1
    
    return redirect(url_for('room'))

# 重置游戏
@app.route('/reset', methods=['POST'])
def reset():
    room_id = session.get('room')
    if room_id in rooms:
        del rooms[room_id]
    return redirect('/')

if __name__ == '__main__':
    # Railway 使用动态端口，从环境变量读取，默认为 5000（本地开发）
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)