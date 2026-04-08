import requests
import json
import os
import re
import time
import datetime

TEAM_ID = '43TISSDh'
HTML_FILE = 'index.html'

def get_team_tournaments():
    # Получаем список турниров
    url = f"https://lichess.org/api/team/{TEAM_ID}/arena"
    response = requests.get(url)
    tournaments = [json.loads(line) for line in response.text.strip().split('\n') if line]
    return tournaments[:50] # Берем последние 50 турниров

def fetch_full_data(t_id):
    # Получаем детали турнира
    info = requests.get(f"https://lichess.org/api/tournament/{t_id}").json()
    
    # Проверяем, это межклубная битва (Team Battle) или внутренний турнир
    is_team_battle = 'teamBattle' in info
    
    # Получаем результаты
    results_text = requests.get(f"https://lichess.org/api/tournament/{t_id}/results").text
    results = [json.loads(l) for l in results_text.strip().split('\n') if l]
    
    team_results = []
    for p in results:
        if is_team_battle:
            # В командной битве берем только игроков нашего клуба
            if p.get('team', '').lower() == TEAM_ID.lower():
                team_results.append({'u': p['username'], 's': p['score'], 'r': p['rank']})
        else:
            # Во внутреннем турнире клуба берем всех участников
            team_results.append({'u': p['username'], 's': p['score'], 'r': p['rank']})
    
    return {
        'id': t_id,
        'n': info['fullName'],
        'd': info['startsAt'],
        'p': team_results,
        'pts': sum(p['s'] for p in team_results),
        'disabled': False
    }

print("Начинаю сбор данных...")
all_data = []
for t in get_team_tournaments():
    try:
        all_data.append(fetch_full_data(t['id']))
        print(f"Турнир {t['id']} загружен.")
    except Exception as e:
        print(f"Ошибка с турниром {t['id']}: {e}")
        continue

print("Обновляю HTML файл...")
with open(HTML_FILE, 'r', encoding='utf-8') as f:
    html = f.read()

# Вставляем новые данные в HTML код
new_json = json.dumps(all_data, ensure_ascii=False)
html = re.sub(r'let data = \[.*?\];', f'let data = {new_json};', html, flags=re.DOTALL)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("Готово!")
def send_telegram_message():
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("Токены Telegram не найдены. Сообщение не отправлено.")
        return

    # Ссылка на ваш сайт
    site_url = "https://NemchikSersh.github.io/MC-Lichess/"
    text = f"🏆 <b>Рейтинг клуба обновлен!</b>\n\nСвежие результаты турниров уже подсчитаны. Заходите проверить свои позиции!\n\n👉 <a href='{site_url}'>Посмотреть рейтинг</a>"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        requests.post(url, json=payload)
        print("Уведомление в Telegram успешно отправлено!")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# Проверяем день недели. 0 - Понедельник, 3 - Четверг, 6 - Воскресенье
# Время UTC (20:00), поэтому день в Берлине и UTC совпадает
today = datetime.datetime.utcnow().weekday()

if today in [0, 3, 6]:
    print("Сегодня день отправки уведомления. Пишу в Telegram...")
    send_telegram_message()
else:
    print(f"Сегодня день без уведомлений (номер дня: {today}). Телеграм отдыхает.")
