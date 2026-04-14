import requests
import json
import os
import re
import time
import datetime

TEAM_ID = '43TISSDh'
HTML_FILE = 'index.html'

def get_team_tournaments():
    url = f"https://lichess.org/api/team/{TEAM_ID}/arena"
    response = requests.get(url)
    tournaments = [json.loads(line) for line in response.text.strip().split('\n') if line]
    
    # Фильтруем турниры: оставляем только те, которые уже начались (статус 20) 
    # или завершились (статус 30). Будущие (статус 10) — пропускаем.
    valid_tournaments = [t for t in tournaments if t.get('status', 0) >= 20]
    
    return valid_tournaments[:50]

def fetch_full_data(t_id):
    time.sleep(1.5) 
    
    info_req = requests.get(f"https://lichess.org/api/tournament/{t_id}")
    if info_req.status_code != 200:
        raise Exception(f"Ошибка получения инфо: HTTP {info_req.status_code}")
    info = info_req.json()
    
    is_team_battle = 'teamBattle' in info
    
    results_req = requests.get(f"https://lichess.org/api/tournament/{t_id}/results")
    if results_req.status_code != 200:
        raise Exception(f"Ошибка получения результатов: HTTP {results_req.status_code}")
    
    results = [json.loads(l) for l in results_req.text.strip().split('\n') if l]
    
    team_results = []
    for p in results:
        if is_team_battle:
            if p.get('team', '').lower() == TEAM_ID.lower():
                team_results.append({'u': p['username'], 's': p['score'], 'r': p['rank']})
        else:
            team_results.append({'u': p['username'], 's': p['score'], 'r': p['rank']})
    
    return {
        'id': t_id,
        'n': info['fullName'],
        'd': info['startsAt'],
        'p': team_results,
        'pts': sum(p['s'] for p in team_results),
        'disabled': False
    }

def send_telegram_message():
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("Токены Telegram не найдены. Сообщение не отправлено.")
        return

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

print("Начинаю сбор данных...")
all_data = []
for t in get_team_tournaments():
    try:
        data = fetch_full_data(t['id'])
        all_data.append(data)
        print(f"Турнир {t['id']} загружен. Очки: {data['pts']}")
    except Exception as e:
        print(f"Ошибка с турниром {t['id']}: {e}")
        continue

print("Обновляю HTML файл...")
with open(HTML_FILE, 'r', encoding='utf-8') as f:
    html = f.read()

new_json = json.dumps(all_data, ensure_ascii=False)
html = re.sub(r'let data = \[.*?\];', f'let data = {new_json};', html, flags=re.DOTALL)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("Данные сохранены.")

# Проверяем день недели (0 - Пн, 1 - Вт, 2 - Ср, 3 - Чт, 4 - Пт, 5 - Сб, 6 - Вс)
today = datetime.datetime.utcnow().weekday()

# Отправляем сообщение по Пн (0), Ср (2 - временно для теста сегодня), Чт (3) и Вс (6)
if today in [0, 3, 6]: 
    print("Отправляю уведомление в Telegram...")
    #  send_telegram_message()
else:
    print(f"Сегодня номер дня {today}. Телеграм отдыхает.")

print("Готово!")
