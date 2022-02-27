# Проект телеграм- и вконтакте-бота проводящего викторину  
## Цель  
Создать бота с возможностью взаимодействовать с конкурсантами викторины.  

## Технологии  
- Telegram  
- VK API  
- Python 3.9  
- Redis  

## Инсталляция  
1. Создать окружение  
> python -m venv venv  
> source venv/bin/activate  
2. Установить зависимости  
> python -m pip install --upgrade pip  
> pip install -r requirements.txt  
3. Завести (создать) переменные среды окружения (Токены телеграм-бота и бота ВКонтакте):  
- QUIZ_BOT_TOKEN=  
- QUIZ_VK_TOKEN=  
Для работы с Redis (переменные с параметрами):  
- QUIZ_REDIS_USER=  
- QUIZ_REDIS_PASS=  
- QUIZ_REDIS_URL=  
- QUIZ_REDIS_PORT=  
4. Загрузить вопросы-ответы в каталог quiz_files. Формат:    
>  Вопрос 6:
>  КРИСТИНА И СТЕПАН
>  У дяди Степы высох пруд.
>  И как теперь мне освежаться?
>  Вот будет пасмурно и тут
>  [...]!
>
>  Ответ:
>   Ты будешь в облаках купаться
5. Запустить бота  
> python telegram_bot.py или python vkontakte_bot.py  

[Пример телеграм бота](https://t.me/quiz_dvmn_student83_bot)  
[Пример бота ВКонтакте](https://vk.com/public210878612)  