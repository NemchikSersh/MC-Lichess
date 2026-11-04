import requests
import json
import os
import re
import time
import datetime

# --- НАСТРОЙКИ КОМАНД ---
# Главная команда и команды-друзья
TEAMS = ['43TISSDh', '0HNGIQ0f', '3pe91Ykb']
HTML_FILE = 'index.html'

def get_team_tournaments(team_id):
    url = f"https://lichess.org/api/team/{team_id}/arena?max=200"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Ошибка получения турниров для {team_id}: HTTP {response.status_code}")
        return []
    
    tournaments = [json.loads(line) for line in response.text.strip().split('\n') if line]
    # Оставляем только те, которые начались или завершились
    valid_tournaments = [t for t in tournaments if t.get('status', 0) >= 20]
    return valid_tournaments

def fetch_full_data(t_id, team_id):
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
            if p.get('team', '').lower() == team_id.lower():
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


print("Читаю существующие турниры из HTML...")
with open(HTML_FILE, 'r', encoding='utf-8') as f:
    html = f.read()

existing_teams_data = {t: [] for t in TEAMS}

# Ищем, в каком формате сейчас хранятся данные в index.html
match_new = re.search(r'let teamsData = (\{.*?\});', html, flags=re.DOTALL)
match_old = re.search(r'let data = (\[.*?\]);', html, flags=re.DOTALL)

if match_new:
    try:
        parsed = json.loads(match_new.group(1))
        for t in TEAMS:
            existing_teams_data[t] = parsed.get(t, [])
    except Exception as e:
        print("Ошибка парсинга нового формата данных:", e)
elif match_old:
    try:
        parsed = json.loads(match_old.group(1))
        existing_teams_data['43TISSDh'] = parsed
        print("Найден старый формат данных, он будет конвертирован в мульти-командный.")
    except Exception as e:
        print("Ошибка парсинга старого формата данных:", e)

print("\n=== Начинаю сбор данных ===")
for current_team in TEAMS:
    print(f"\n--- Проверка команды {current_team} ---")
    existing_ids = {t['id'] for t in existing_teams_data[current_team] if 'id' in t}
    
    for t in get_team_tournaments(current_team):
        if t['id'] in existing_ids:
            continue # Турнир уже есть, пропускаем (экономим время!)
            
        try:
            data = fetch_full_data(t['id'], current_team)
            existing_teams_data[current_team].append(data)
            print(f"Добавлен НОВЫЙ турнир {t['id']} для {current_team}. Очки: {data['pts']}")
        except Exception as e:
            print(f"Ошибка с турниром {t['id']}: {e}")
            continue
            
    # Сортируем турниры от новых к старым
    existing_teams_data[current_team].sort(key=lambda x: x.get('d', ''), reverse=True)

print("\nОбновляю HTML файл...")
new_json = json.dumps(existing_teams_data, ensure_ascii=False)

if match_new:
    html = re.sub(r'let teamsData = \{.*?\};', f'let teamsData = {new_json};', html, flags=re.DOTALL)
else:
    # Переходный вариант: меняем старую переменную data на словарь teamsData, чтобы сайт не сломался
    replacement = f'let teamsData = {new_json};\nlet currentTeamId = "43TISSDh";\nlet data = teamsData[currentTeamId] || [];'
    html = re.sub(r'let data = \[.*?\];', replacement, html, flags=re.DOTALL)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("Данные успешно сохранены.")

# Проверяем день недели (0 - Пн, 1 - Вт, 2 - Ср, 3 - Чт, 4 - Пт, 5 - Сб, 6 - Вс)
today = datetime.datetime.utcnow().weekday()

if today in [0, 3, 6]: 
    print("Отправляю уведомление в Telegram...")
    #  send_telegram_message()
else:
    print(f"Сегодня номер дня {today}. Телеграм отдыхает.")

print("Готово!")
